"""Hermes Plugin: hindsight-project-indexer-hermes

Smart codebase indexing & context injection for Hermes Agent backed by Hindsight.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .indexer import find_project_root
from .hindsight_sync import get_project_index, load_hindsight_config, mark_dirty
from .auto_update import check_and_update, start_background_auto_update
from .tools import (
    STATUS_TOOL_SCHEMA,
    REINDEX_TOOL_SCHEMA,
    UPDATE_TOOL_SCHEMA,
    handle_project_index_status,
    handle_project_reindex,
    handle_project_indexer_update
)

logger = logging.getLogger(__name__)

_CTX: Any = None


def _system_prompt_section(_info: Optional[Dict[str, Any]] = None) -> str:
    """Render the project context section into the system prompt."""
    root = find_project_root()
    if not root:
        return ""
    try:
        summary = get_project_index(root, force_refresh=False)
        return summary.get("formatted_context", "")
    except Exception as e:
        logger.warning("Error generating project index prompt section: %s", e)
        return ""


def _on_pre_llm_call(**context: Any) -> Optional[Dict[str, Any]]:
    """Pre-LLM call hook to inject fresh project context if changes occurred."""
    root = find_project_root()
    if not root:
        return None
    try:
        summary = get_project_index(root, force_refresh=False)
        return None
    except Exception as e:
        logger.warning("Project indexer pre_llm_call failed: %s", e)
        return None


def _on_post_tool_call(tool_name: str = "", **kwargs: Any) -> None:
    """Invalidate cache when code modifying tools are called."""
    modifying_tools = {"write_file", "patch", "terminal", "execute_code"}
    if tool_name in modifying_tools:
        mark_dirty()


def _command_reindex(raw_args: str = "") -> str:
    """CLI command /reindex handler."""
    root = find_project_root()
    if not root:
        return "Not inside a recognized project root directory."
    try:
        summary = get_project_index(root, force_refresh=True)
        return f"Successfully reindexed '{summary['project_name']}' (fingerprint: {summary['fingerprint']})."
    except Exception as e:
        return f"Failed to reindex: {e}"


def _command_projectinfo(raw_args: str = "") -> str:
    """CLI command /projectinfo handler."""
    root = find_project_root()
    if not root:
        return "Not inside a recognized project directory."
    try:
        cfg = load_hindsight_config()
        summary = get_project_index(root, force_refresh=False)
        langs = ", ".join(summary["stack"]["languages"]) or "None"
        fws = ", ".join(summary["stack"]["frameworks"]) or "None"
        git = summary.get("git_info", {})
        git_line = f"Git: {git.get('branch')} ({git.get('commit')})" if git.get("branch") else ""
        return (
            f"Project: {summary['project_name']}\n"
            f"Path: {summary['root_path']}\n"
            f"Fingerprint: {summary['fingerprint']}\n"
            f"{git_line}\n"
            f"Languages: {langs}\n"
            f"Frameworks: {fws}\n"
            f"Hindsight Bank: {cfg.get('bank_id')} ({cfg.get('api_url')})"
        )
    except Exception as e:
        return f"Failed to retrieve project info: {e}"


def _command_plugin_update(raw_args: str = "") -> str:
    """CLI command /project-indexer-update handler."""
    res = check_and_update(force=True)
    return f"Plugin update: {res.get('message', res.get('status'))}"


def register(ctx: Any) -> None:
    """Register the plugin hooks, commands, tools, and prompt section with Hermes."""
    global _CTX
    _CTX = ctx

    # Start background auto-updater
    try:
        start_background_auto_update()
    except Exception as e:
        logger.debug("Failed to spawn background auto-updater: %s", e)

    # System prompt section
    try:
        ctx.register_system_prompt_section(
            id="hindsight-project-index",
            content=_system_prompt_section,
            position="after_memory",
            max_chars=3500
        )
    except Exception as e:
        logger.warning("Could not register system prompt section: %s", e)

    # Hooks
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)

    # Commands
    ctx.register_command("reindex", _command_reindex, description="Reindex the current project into Hindsight")
    ctx.register_command("projectinfo", _command_projectinfo, description="Show project indexing info and status")
    ctx.register_command("project-indexer-update", _command_plugin_update, description="Update hindsight-project-indexer plugin from git")

    # Tools
    for tool_name, schema, handler in [
        ("project_index_status", STATUS_TOOL_SCHEMA, handle_project_index_status),
        ("project_reindex", REINDEX_TOOL_SCHEMA, handle_project_reindex),
        ("project_indexer_update", UPDATE_TOOL_SCHEMA, handle_project_indexer_update),
    ]:
        try:
            ctx.register_tool(
                name=tool_name,
                toolset="indexing",
                schema=schema,
                handler=handler,
                description=schema["description"]
            )
        except Exception as e:
            logger.warning("Could not register tool %s: %s", tool_name, e)
