"""Project structure and tech-stack indexer module."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

IGNORED_DIRS: Set[str] = {
    ".git", "node_modules", "dist", "build", ".next", ".turbo", "target",
    "__pycache__", ".venv", "venv", ".cache", ".hermes", ".idea", ".vscode",
    "tmp", "temp", "coverage", ".output", "vendor", ".gradle", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "site-packages", "pkg"
}

PROJECT_ROOT_MARKERS: Set[str] = {
    ".git", "package.json", "Cargo.toml", "pyproject.toml", "go.mod", "pom.xml",
    "build.gradle", "composer.json", "requirements.txt", "Gemfile", "Makefile",
    "flake.nix", "WORKSPACE", "CMakeLists.txt"
}


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the root directory of the current project by looking upwards for markers."""
    curr = (start_path or Path.cwd()).resolve()
    home = Path.home().resolve()
    root_fs = Path("/").resolve()

    if curr in (home, root_fs):
        return None

    p = curr
    while p not in (home, root_fs, p.parent):
        if (p / ".git").exists():
            return p
        if any((p / m).exists() for m in PROJECT_ROOT_MARKERS):
            return p
        p = p.parent
    return None


def get_git_info(root: Path) -> Dict[str, str]:
    """Extract active branch and recent commit from git."""
    info = {"branch": "", "commit": "", "status_summary": ""}
    if not (root / ".git").exists():
        return info
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        commit = subprocess.check_output(
            ["git", "-C", str(root), "log", "-1", "--format=%h %s (%cr)"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()

        info["branch"] = branch
        info["commit"] = commit
        info["status_summary"] = "clean" if not status else f"{len(status.splitlines())} modified/untracked files"
    except Exception:
        pass
    return info


def get_project_fingerprint(root: Path) -> str:
    """Calculate a fast fingerprint of the project state to detect changes."""
    # Git-based fast fingerprint
    if (root / ".git").exists():
        try:
            head = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            status = subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            raw = f"git:{head}:{status}"
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        except Exception:
            pass

    # Non-git or git failure fallback: hash top-level directory stats
    entries: List[str] = []
    try:
        for p in root.glob("*"):
            if p.name in IGNORED_DIRS or p.name.startswith("."):
                continue
            try:
                st = p.stat()
                entries.append(f"{p.name}:{st.st_mtime_ns}:{st.st_size}")
            except Exception:
                pass
    except Exception:
        pass
    raw = "|".join(sorted(entries))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def analyze_tech_stack(root: Path) -> Dict[str, Any]:
    """Extract tech stack, languages, frameworks, and architecture markers."""
    stack: Dict[str, Any] = {
        "languages": [],
        "frameworks": [],
        "manifests": [],
        "entrypoints": [],
        "infra": [],
        "monorepo": False,
        "configs": []
    }

    # Node / TypeScript / JavaScript
    pkg_json = root / "package.json"
    if pkg_json.exists():
        stack["manifests"].append("package.json")
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "typescript" in deps or (root / "tsconfig.json").exists():
                stack["languages"].append("TypeScript")
            else:
                stack["languages"].append("JavaScript")

            common_fw = [
                ("react", "React"), ("next", "Next.js"), ("vue", "Vue"),
                ("nuxt", "Nuxt"), ("hono", "Hono"), ("express", "Express"),
                ("fastify", "Fastify"), ("tailwindcss", "Tailwind CSS"),
                ("vite", "Vite"), ("drizzle-orm", "Drizzle"), ("prisma", "Prisma"),
                ("svelte", "Svelte"), ("astro", "Astro"), ("electron", "Electron")
            ]
            for dep_k, fw_name in common_fw:
                if any(dep_k in k for k in deps):
                    stack["frameworks"].append(fw_name)
        except Exception:
            pass

    # Rust
    cargo_toml = root / "Cargo.toml"
    if cargo_toml.exists():
        stack["manifests"].append("Cargo.toml")
        stack["languages"].append("Rust")
        try:
            content = cargo_toml.read_text(encoding="utf-8")
            if "[workspace]" in content:
                stack["monorepo"] = True
            for fw in ["axum", "actix-web", "tokio", "sea-orm", "diesel", "leptos", "tauri"]:
                if fw in content:
                    stack["frameworks"].append(fw)
        except Exception:
            pass

    # Python
    pyproject = root / "pyproject.toml"
    reqs = root / "requirements.txt"
    if pyproject.exists() or reqs.exists():
        stack["languages"].append("Python")
        if pyproject.exists():
            stack["manifests"].append("pyproject.toml")
        if reqs.exists():
            stack["manifests"].append("requirements.txt")
        try:
            text = (pyproject.read_text(encoding="utf-8") if pyproject.exists() else "") + (
                reqs.read_text(encoding="utf-8") if reqs.exists() else ""
            )
            for fw in ["fastapi", "django", "flask", "pytorch", "torch", "pandas", "alembic"]:
                if fw in text.lower():
                    stack["frameworks"].append(fw)
        except Exception:
            pass

    # Go
    if (root / "go.mod").exists():
        stack["manifests"].append("go.mod")
        stack["languages"].append("Go")

    # Monorepo detection
    if any((root / p).exists() for p in ["pnpm-workspace.yaml", "lerna.json"]):
        stack["monorepo"] = True
    elif (root / "apps").is_dir() and (root / "packages").is_dir():
        stack["monorepo"] = True

    # Infra & Containers
    for candidate, label in [
        ("Dockerfile", "Docker"), ("docker-compose.yml", "Docker Compose"),
        ("compose.yaml", "Docker Compose"), ("compose.yml", "Docker Compose"),
        (".github/workflows", "GitHub Actions"), ("Makefile", "Make"),
        ("flake.nix", "Nix Flake"), ("default.nix", "Nix")
    ]:
        if (root / candidate).exists():
            stack["infra"].append(label)

    # Key configs
    for cfg in [
        "tsconfig.json", "drizzle.config.ts", "drizzle.config.js",
        "alembic.ini", "vite.config.ts", "vite.config.js", "next.config.mjs",
        "next.config.js", ".env.example", ".env.sample"
    ]:
        if (root / cfg).exists():
            stack["configs"].append(cfg)

    # Common Entrypoints
    for candidate in [
        "src/index.ts", "src/main.ts", "src/main.rs", "src/lib.rs",
        "main.py", "app.py", "src/app.py", "main.go", "index.js",
        "src/index.js", "apps/api/src/index.ts", "apps/web/src/main.tsx"
    ]:
        if (root / candidate).exists():
            stack["entrypoints"].append(candidate)

    stack["languages"] = sorted(list(set(stack["languages"])))
    stack["frameworks"] = sorted(list(set(stack["frameworks"])))
    stack["infra"] = sorted(list(set(stack["infra"])))
    return stack


def generate_compact_tree(root: Path, max_depth: int = 3, max_entries: int = 80) -> str:
    """Generate a clean, indented file tree omitting noisy directories."""
    lines: List[str] = []
    count = 0

    def walk(current: Path, depth: int, prefix: str):
        nonlocal count
        if depth > max_depth or count >= max_entries:
            return
        try:
            entries = sorted(
                [p for p in current.iterdir() if p.name not in IGNORED_DIRS and not p.name.startswith(".")],
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
        except Exception:
            return

        for i, entry in enumerate(entries):
            if count >= max_entries:
                lines.append(f"{prefix}... (truncated)")
                return
            count += 1
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            child_prefix = "    " if is_last else "│   "

            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                walk(entry, depth + 1, prefix + child_prefix)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

    lines.append(f"{root.name}/")
    walk(root, 1, "")
    return "\n".join(lines)


def get_readme_summary(root: Path, max_chars: int = 800) -> str:
    """Extract a brief summary from README.md if present."""
    for name in ["README.md", "README", "readme.md"]:
        f = root / name
        if f.exists() and f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                summary = " ".join(lines[:10])
                if len(summary) > max_chars:
                    summary = summary[:max_chars].rstrip() + "..."
                return summary
            except Exception:
                pass
    return ""


def build_project_summary(
    root: Path,
    max_depth: int = 3,
    max_files: int = 80
) -> Dict[str, Any]:
    """Compile complete project summary object and formatted context string."""
    fp = get_project_fingerprint(root)
    git_info = get_git_info(root)
    stack = analyze_tech_stack(root)
    tree = generate_compact_tree(root, max_depth=max_depth, max_entries=max_files)
    readme = get_readme_summary(root)

    langs = ", ".join(stack["languages"]) or "Generic"
    fws = ", ".join(stack["frameworks"]) or "None detected"
    entrypoints = ", ".join(stack["entrypoints"]) or "None detected"
    infra = ", ".join(stack["infra"]) or "None"
    configs = ", ".join(stack["configs"]) or "None"

    formatted = f"""[Project Context: {root.name}]
- Path: {root}
- Fingerprint: {fp}
- Languages: {langs}
- Frameworks: {fws}
- Entrypoints: {entrypoints}
- Infra: {infra}
- Configs: {configs}
"""
    if git_info.get("branch"):
        formatted += f"- Git: branch '{git_info['branch']}' | {git_info['commit']} | {git_info['status_summary']}\n"

    if stack.get("monorepo"):
        formatted += "- Monorepo: Yes\n"

    if readme:
        formatted += f"- About: {readme}\n"

    formatted += f"\nDirectory Layout:\n```\n{tree}\n```"

    return {
        "project_name": root.name,
        "root_path": str(root),
        "fingerprint": fp,
        "git_info": git_info,
        "stack": stack,
        "readme": readme,
        "tree": tree,
        "formatted_context": formatted
    }
