"""Hermes tool handlers for project index status, reindexing, and plugin self-update."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .indexer import find_project_root
from .hindsight_sync import get_project_index, load_hindsight_config
from .auto_update import check_and_update


def handle_project_index_status(args: Dict[str, Any]) -> str:
    """Return status of the current project index."""
    root = find_project_root()
    if not root:
        return json.dumps({
            "status": "not_in_project",
            "message": "Current directory is not inside a recognized project root (no git or manifest markers)."
        }, indent=2)

    is_deep = bool(args.get("deep", False))
    mode = "deep" if is_deep else "standard"
    cfg = load_hindsight_config()
    summary = get_project_index(root, force_refresh=False, mode=mode, config_override=cfg)

    resp = {
        "status": "ok",
        "project_name": summary["project_name"],
        "root_path": summary["root_path"],
        "mode": summary.get("mode", mode),
        "fingerprint": summary["fingerprint"],
        "git": summary.get("git_info"),
        "scan_info": summary.get("scan_info"),
        "architecture": summary.get("arch_patterns"),
        "inferred_flow": summary.get("exec_flow"),
        "core_rules": summary.get("rules_data", {}).get("rules", []),
        "public_apis": summary.get("api_map", {}),
        "hindsight_bank": cfg.get("bank_id"),
        "hindsight_api": cfg.get("api_url")
    }
    if is_deep:
        resp["formatted_context"] = summary.get("formatted_context")
    return json.dumps(resp, indent=2)


def handle_project_reindex(args: Dict[str, Any]) -> str:
    """Force a reindex of the current project and sync to Hindsight."""
    root = find_project_root()
    if not root:
        return json.dumps({
            "status": "error",
            "message": "Cannot reindex: not in a recognized project directory."
        }, indent=2)

    is_deep = bool(args.get("deep", False))
    mode = "deep" if is_deep else "standard"
    cfg = load_hindsight_config()
    summary = get_project_index(root, force_refresh=True, mode=mode, config_override=cfg)
    return json.dumps({
        "status": "reindexed",
        "project_name": summary["project_name"],
        "mode": mode,
        "fingerprint": summary["fingerprint"],
        "message": f"Successfully reindexed {summary['project_name']} (mode: {mode}) and queued Hindsight sync."
    }, indent=2)


def handle_project_indexer_update(args: Dict[str, Any]) -> str:
    """Force check for plugin updates from git remote repository."""
    result = check_and_update(force=True)
    return json.dumps(result, indent=2)


STATUS_TOOL_SCHEMA = {
    "name": "project_index_status",
    "description": "Get the indexing status, fingerprint, git info, and tech stack of the current active project.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

REINDEX_TOOL_SCHEMA = {
    "name": "project_reindex",
    "description": "Force a complete rescan and reindex of the current project, refreshing local cache and Hindsight memory.",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Optional reason for reindexing (e.g. after adding dependencies or restructuring files)."
            }
        },
        "required": []
    }
}

UPDATE_TOOL_SCHEMA = {
    "name": "project_indexer_update",
    "description": "Check for and apply updates to hindsight-project-indexer-hermes plugin directly from GitHub.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
