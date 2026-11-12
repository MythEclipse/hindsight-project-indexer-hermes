"""Hermes tool handlers for project index status and manual reindexing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .indexer import find_project_root
from .hindsight_sync import get_project_index, load_hindsight_config


def handle_project_index_status(args: Dict[str, Any]) -> str:
    """Return status of the current project index."""
    root = find_project_root()
    if not root:
        return json.dumps({
            "status": "not_in_project",
            "message": "Current directory is not inside a recognized project root (no git or manifest markers)."
        }, indent=2)

    cfg = load_hindsight_config()
    summary = get_project_index(root, force_refresh=False, config_override=cfg)
    return json.dumps({
        "status": "ok",
        "project_name": summary["project_name"],
        "root_path": summary["root_path"],
        "fingerprint": summary["fingerprint"],
        "stack": summary["stack"],
        "hindsight_bank": cfg.get("bank_id"),
        "hindsight_api": cfg.get("api_url")
    }, indent=2)


def handle_project_reindex(args: Dict[str, Any]) -> str:
    """Force a reindex of the current project and sync to Hindsight."""
    root = find_project_root()
    if not root:
        return json.dumps({
            "status": "error",
            "message": "Cannot reindex: not in a recognized project directory."
        }, indent=2)

    cfg = load_hindsight_config()
    summary = get_project_index(root, force_refresh=True, config_override=cfg)
    return json.dumps({
        "status": "reindexed",
        "project_name": summary["project_name"],
        "fingerprint": summary["fingerprint"],
        "message": f"Successfully reindexed {summary['project_name']} and queued Hindsight sync."
    }, indent=2)


STATUS_TOOL_SCHEMA = {
    "name": "project_index_status",
    "description": "Get the indexing status, fingerprint, and tech stack of the current active project.",
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
