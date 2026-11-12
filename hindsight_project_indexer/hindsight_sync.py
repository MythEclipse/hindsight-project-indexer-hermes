"""Hindsight memory synchronization and local caching for project indexing."""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from .indexer import build_project_summary, get_project_fingerprint, get_latest_commit_diff

logger = logging.getLogger(__name__)

_MEM_CACHE: Dict[str, Dict[str, Any]] = {}
_DIRTY_PROJECTS: set[str] = set()
_LOCK = threading.Lock()


def get_cache_dir() -> Path:
    """Return the directory for local project index cache files."""
    base = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
    cache_dir = base / "cache" / "project_index"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def load_hindsight_config() -> Dict[str, Any]:
    """Load Hindsight API config from Hermes hindsight config or env."""
    defaults = {
        "api_url": "http://100.79.111.61:8890",
        "bank_id": "hermes-gemini",
        "timeout": 30
    }
    paths = [
        Path.home() / ".hermes" / "hindsight" / "config.json",
        Path.home() / ".hindsight" / "config.json"
    ]
    for p in paths:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if "api_url" in data:
                    defaults["api_url"] = data["api_url"]
                if "bank_id" in data:
                    defaults["bank_id"] = data["bank_id"]
                if "timeout" in data:
                    defaults["timeout"] = data["timeout"]
                break
            except Exception as e:
                logger.warning("Failed to parse %s: %s", p, e)

    if os.environ.get("HINDSIGHT_API_URL"):
        defaults["api_url"] = os.environ["HINDSIGHT_API_URL"]
    if os.environ.get("HINDSIGHT_BANK_ID"):
        defaults["bank_id"] = os.environ["HINDSIGHT_BANK_ID"]

    return defaults


def mark_dirty(project_root: Optional[Path] = None) -> None:
    """Mark a project as dirty so the next lookup triggers a fingerprint check."""
    with _LOCK:
        if project_root is not None:
            _DIRTY_PROJECTS.add(str(project_root.resolve()))
        else:
            _DIRTY_PROJECTS.add("*")


def _read_disk_cache(cache_file: Path) -> Optional[Dict[str, Any]]:
    if not cache_file.is_file():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_disk_cache(cache_file: Path, data: Dict[str, Any]) -> None:
    try:
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to write project index cache: %s", e)


def sync_to_hindsight(summary: Dict[str, Any], config: Dict[str, Any]) -> None:
    """Send project index summary to Hindsight asynchronously in a background thread."""
    def _worker():
        try:
            from hindsight_client import Hindsight
            client = Hindsight(base_url=config["api_url"])
            doc_id = f"project-index-{summary['project_name']}"
            tags = [
                "type:project_index",
                f"project:{summary['project_name']}",
                f"fp:{summary['fingerprint']}"
            ]
            client.retain(
                bank_id=config["bank_id"],
                content=summary["formatted_context"],
                context=f"Project Index: {summary['project_name']}",
                document_id=doc_id,
                strategy="survey",
                tags=tags,
                retain_async=True
            )
            logger.info("Retained project index for %s to Hindsight", summary["project_name"])
        except Exception as e:
            logger.warning("Failed to retain project index to Hindsight: %s", e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def sync_git_diff_to_hindsight(root: Path, project_name: str, config: Dict[str, Any]) -> None:
    """Send latest commit diff to Hindsight using the 'git' extraction strategy."""
    if not (root / ".git").exists():
        return

    def _git_worker():
        try:
            import subprocess
            from hindsight_client import Hindsight

            head_sha = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()

            cache_dir = get_cache_dir()
            last_commit_file = cache_dir / f"last_commit_{project_name}.txt"
            last_sha = last_commit_file.read_text(encoding="utf-8").strip() if last_commit_file.is_file() else ""

            if last_sha == head_sha:
                return

            diff = get_latest_commit_diff(root)
            if not diff:
                return

            client = Hindsight(base_url=config["api_url"])
            doc_id = f"commit-{project_name}-{head_sha[:10]}"
            tags = [
                "type:git_commit",
                f"project:{project_name}",
                f"commit:{head_sha[:10]}"
            ]
            client.retain(
                bank_id=config["bank_id"],
                content=diff,
                context=f"Git Commit: {project_name}",
                document_id=doc_id,
                strategy="git",
                tags=tags,
                retain_async=True
            )
            last_commit_file.write_text(head_sha, encoding="utf-8")
            logger.info("Retained git commit %s for %s to Hindsight (strategy: git)", head_sha[:10], project_name)
        except Exception as e:
            logger.warning("Failed to sync git diff to Hindsight: %s", e)

    t = threading.Thread(target=_git_worker, daemon=True)
    t.start()


def get_project_index(
    root: Path,
    force_refresh: bool = False,
    mode: str = "standard",
    config_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Retrieve the project index, utilizing memory and disk cache with LoD budgeting."""
    root_str = str(root.resolve())
    cache_key = f"{root_str}:{mode}"
    cfg = config_override or load_hindsight_config()

    with _LOCK:
        is_dirty = ("*" in _DIRTY_PROJECTS) or (root_str in _DIRTY_PROJECTS)
        if not force_refresh and not is_dirty and cache_key in _MEM_CACHE:
            return _MEM_CACHE[cache_key]

    fp = get_project_fingerprint(root)
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"{root.name}_{mode}_{fp}.json"

    # Try disk cache
    if not force_refresh:
        cached = _read_disk_cache(cache_file)
        if cached and cached.get("fingerprint") == fp and cached.get("mode") == mode:
            with _LOCK:
                _MEM_CACHE[cache_key] = cached
                _DIRTY_PROJECTS.discard(root_str)
                _DIRTY_PROJECTS.discard("*")
            return cached

    # Generate new index with specified LoD mode
    summary = build_project_summary(root, mode=mode)
    _write_disk_cache(cache_file, summary)

    # Sync to Hindsight in background
    sync_to_hindsight(summary, cfg)
    sync_git_diff_to_hindsight(root, summary["project_name"], cfg)

    with _LOCK:
        _MEM_CACHE[cache_key] = summary
        _DIRTY_PROJECTS.discard(root_str)
        _DIRTY_PROJECTS.discard("*")

    return summary
