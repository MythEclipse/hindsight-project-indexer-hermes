"""Auto-update module for hindsight-project-indexer-hermes."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 1800  # Check at most once every 30 minutes


def get_plugin_root() -> Path:
    """Return the root directory of this plugin."""
    # File is in <root>/hindsight_project_indexer/auto_update.py
    return Path(__file__).resolve().parent.parent


def get_update_state_file() -> Path:
    base = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
    state_dir = base / "cache" / "project_index"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "plugin_update_state.json"


def check_and_update(force: bool = False) -> Dict[str, Any]:
    """Check git remote and pull updates if available."""
    root = get_plugin_root()
    git_dir = root / ".git"

    if not git_dir.exists():
        return {
            "status": "not_git_repo",
            "message": f"Plugin at {root} is not a git clone, skipping auto-update."
        }

    state_file = get_update_state_file()
    now = time.time()

    if not force and state_file.is_file():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            last_check = state.get("last_check_timestamp", 0)
            if now - last_check < CHECK_INTERVAL_SECONDS:
                return {
                    "status": "rate_limited",
                    "message": "Update check skipped (checked recently).",
                    "last_check": last_check
                }
        except Exception:
            pass

    try:
        # Fetch remote
        fetch_res = subprocess.run(
            ["git", "-C", str(root), "fetch", "origin", "main"],
            capture_output=True, text=True, timeout=20
        )
        if fetch_res.returncode != 0:
            return {
                "status": "fetch_failed",
                "message": fetch_res.stderr.strip() or "git fetch failed"
            }

        # Compare HEAD and origin/main
        local_head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, timeout=5
        ).strip()
        remote_head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "origin/main"],
            text=True, timeout=5
        ).strip()

        # Update state file
        state_data = {
            "last_check_timestamp": now,
            "local_head": local_head,
            "remote_head": remote_head
        }

        if local_head == remote_head:
            state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
            return {
                "status": "up_to_date",
                "commit": local_head[:8],
                "message": f"Plugin is up to date at commit {local_head[:8]}"
            }

        # Fast-forward pull
        pull_res = subprocess.run(
            ["git", "-C", str(root), "merge", "--ff-only", "origin/main"],
            capture_output=True, text=True, timeout=20
        )
        if pull_res.returncode != 0:
            return {
                "status": "merge_failed",
                "message": pull_res.stderr.strip() or "git merge failed"
            }

        new_head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, timeout=5
        ).strip()
        state_data["local_head"] = new_head
        state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

        logger.info("Plugin auto-updated from %s to %s", local_head[:8], new_head[:8])
        return {
            "status": "updated",
            "old_commit": local_head[:8],
            "new_commit": new_head[:8],
            "message": f"Successfully updated from {local_head[:8]} to {new_head[:8]}"
        }

    except Exception as e:
        logger.warning("Plugin auto-update check error: %s", e)
        return {
            "status": "error",
            "message": str(e)
        }


def start_background_auto_update() -> None:
    """Start a daemon thread that checks for plugin updates in the background."""
    def _worker():
        try:
            # Short sleep on startup so it never contends with Hermes initial boot
            time.sleep(3)
            check_and_update(force=False)
        except Exception as e:
            logger.debug("Background auto-update caught: %s", e)

    t = threading.Thread(target=_worker, daemon=True, name="project_indexer_autoupdate")
    t.start()
