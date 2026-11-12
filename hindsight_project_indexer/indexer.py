"""Universal, stack-agnostic project structure and artifact indexer module."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

IGNORED_DIRS: Set[str] = {
    ".git", "node_modules", "dist", "build", ".next", ".turbo", "target",
    "__pycache__", ".venv", "venv", ".cache", ".hermes", ".idea", ".vscode",
    "tmp", "temp", "coverage", ".output", "vendor", ".gradle", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "site-packages", "pkg"
}

PROJECT_ROOT_MARKERS: Set[str] = {
    ".git", "Cargo.toml", "CMakeLists.txt", "Makefile", "meson.build",
    "pyproject.toml", "requirements.txt", "setup.py", "go.mod", "pom.xml",
    "build.gradle", "composer.json", "flake.nix", "default.nix", "package.json",
    "Assembly-CSharp.csproj", "WORKSPACE", "configure.ac"
}

LANG_EXTENSIONS: Dict[str, str] = {
    # Systems & Native
    ".c": "C", ".h": "C/C++ Header", ".cpp": "C++", ".hpp": "C++ Header",
    ".cc": "C++", ".cxx": "C++", ".cu": "CUDA", ".cuh": "CUDA Header",
    ".rs": "Rust", ".zig": "Zig", ".asm": "Assembly", ".s": "Assembly",
    # ML, Math & Scripting
    ".py": "Python", ".ipynb": "Jupyter Notebook", ".r": "R", ".jl": "Julia",
    ".lua": "Lua", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    # Go, C#, JVM
    ".go": "Go", ".cs": "C#", ".java": "Java", ".kt": "Kotlin", ".scala": "Scala",
    # Web, App & UI
    ".ts": "TypeScript", ".tsx": "TypeScript (UI)", ".js": "JavaScript",
    ".jsx": "JavaScript (UI)", ".vue": "Vue", ".svelte": "Svelte", ".html": "HTML",
    ".css": "CSS", ".scss": "SCSS",
    # Config & Infrastructure
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
    ".sql": "SQL", ".graphql": "GraphQL", ".proto": "Protobuf",
    ".nix": "Nix", ".dockerfile": "Dockerfile",
    # Docs & Knowledge
    ".md": "Markdown", ".org": "Org", ".txt": "Text"
}

ARTIFACT_EXTENSIONS: Dict[str, str] = {
    # ML & Model Weights
    ".gguf": "GGUF Model", ".safetensors": "SafeTensors Model",
    ".pt": "PyTorch Checkpoint", ".pth": "PyTorch Weights",
    ".onnx": "ONNX Model", ".bin": "Weight/Binary Blob",
    # Security, Exploitation & Forensics
    ".pcap": "PCAP Network Capture", ".pcapng": "PCAPng Capture",
    ".dmp": "Memory Dump", ".raw": "Disk Image",
    # Native Binaries & Shared Libraries
    ".elf": "ELF Binary", ".exe": "Windows Executable",
    ".so": "Shared Object", ".dll": "DLL", ".dylib": "macOS Library",
    # Graphics & Game Dev
    ".ase": "Aseprite Sprite", ".aseprite": "Aseprite Sprite",
    ".blend": "Blender Scene", ".unity": "Unity Scene", ".prefab": "Unity Prefab"
}

GENERIC_DIR_ROLES: Dict[str, str] = {
    "src": "Source code",
    "core": "Core logic/engine",
    "kernel": "Low-level kernels",
    "cuda": "CUDA accelerator kernels",
    "models": "Model files / weights",
    "weights": "Model weights & checkpoints",
    "data": "Data / dataset storage",
    "dataset": "Training/evaluation datasets",
    "exploits": "Exploit scripts & targets",
    "pwn": "Binary exploitation files",
    "challenges": "CTF challenge files",
    "tools": "Utility & analysis tools",
    "scripts": "Automation & maintenance scripts",
    "tests": "Test suite",
    "benches": "Benchmarks & performance tests",
    "docs": "Documentation & architecture notes",
    "writeup": "Research & CTF writeups",
    "config": "Configuration files",
    "deploy": "Deployment scripts & manifests",
    "infra": "Infrastructure as code",
    "apps": "Sub-applications (monorepo)",
    "packages": "Shared packages / libraries",
    "crates": "Rust workspace crates"
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
    """Extract active branch and recent commits from git."""
    info = {"branch": "", "recent_commits": [], "status_summary": ""}
    if not (root / ".git").exists():
        return info
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        commits = subprocess.check_output(
            ["git", "-C", str(root), "log", "-3", "--format=%h %s (%cr)"],
            text=True, stderr=subprocess.DEVNULL
        ).strip().splitlines()
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()

        info["branch"] = branch
        info["recent_commits"] = [c.strip() for c in commits if c.strip()]
        info["status_summary"] = "clean" if not status else f"{len(status.splitlines())} modified/untracked files"
    except Exception:
        pass
    return info


def get_project_fingerprint(root: Path) -> str:
    """Calculate a fast fingerprint of the project state to detect changes."""
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


def scan_universal_project(root: Path, max_depth: int = 5) -> Dict[str, Any]:
    """Perform a fast, universal scan of language counts, artifacts, and directories."""
    domains = set()
    manifests: List[str] = []
    commands: Dict[str, str] = {}
    key_dirs: Dict[str, str] = {}
    artifacts = Counter()
    lang_counter = Counter()

    manifest_map = [
        ("Cargo.toml", "Rust (Cargo)"),
        ("CMakeLists.txt", "C/C++ (CMake)"),
        ("Makefile", "Make"),
        ("meson.build", "Meson"),
        ("pyproject.toml", "Python (pyproject)"),
        ("requirements.txt", "Python (requirements)"),
        ("go.mod", "Go (Modules)"),
        ("flake.nix", "Nix Flake"),
        ("default.nix", "Nix"),
        ("package.json", "Node/Bun/TS"),
        ("Assembly-CSharp.csproj", "Unity / C#")
    ]
    for filename, label in manifest_map:
        if (root / filename).exists():
            manifests.append(label)

    # Build commands extraction
    if (root / "Cargo.toml").exists():
        commands["build"] = "cargo build"
        commands["test"] = "cargo test"
        try:
            cargo_txt = (root / "Cargo.toml").read_text(encoding="utf-8")
            bins = re.findall(r"\[\[bin\]\]\s+name\s*=\s*\"([^\"]+)\"", cargo_txt)
            if bins:
                commands["run"] = f"cargo run --bin {bins[0]}"
        except Exception:
            pass

    if (root / "Makefile").exists():
        try:
            for line in (root / "Makefile").read_text(encoding="utf-8").splitlines():
                if re.match(r"^[a-zA-Z0-9_-]+:", line):
                    t = line.split(":", 1)[0].strip()
                    if t not in ["all", ".PHONY"] and len(commands) < 8:
                        commands[f"make {t}"] = "Make target"
        except Exception:
            pass

    if (root / "CMakeLists.txt").exists():
        commands["cmake-build"] = "cmake -B build && cmake --build build"

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        if (root / "pytest.ini").exists() or (root / "tests").exists():
            commands["python-test"] = "pytest"
        for main_cand in ["main.py", "app.py", "run.py", "cli.py"]:
            if (root / main_cand).exists():
                commands["python-run"] = f"python {main_cand}"
                break

    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            for sc in ["dev", "build", "test", "lint", "start"]:
                if sc in scripts:
                    commands[sc] = scripts[sc][:40]
        except Exception:
            pass

    # File counting & special artifact detection
    total_files = 0
    try:
        for p in root.rglob("*"):
            rel_parts = p.relative_to(root).parts
            if any(part in IGNORED_DIRS or (part.startswith(".") and part != ".github") for part in rel_parts[:-1]):
                continue
            if p.is_file():
                total_files += 1
                ext = p.suffix.lower()
                if ext in LANG_EXTENSIONS:
                    lang_counter[LANG_EXTENSIONS[ext]] += 1
                elif ext in ARTIFACT_EXTENSIONS:
                    artifacts[ARTIFACT_EXTENSIONS[ext]] += 1
    except Exception:
        pass

    # Domain Classification
    if lang_counter.get("CUDA") or artifacts.get("GGUF Model") or artifacts.get("SafeTensors Model") or (root / "models").exists() or (root / "weights").exists():
        domains.add("ML / AI & GPU Systems")
    if lang_counter.get("C") or lang_counter.get("C++") or lang_counter.get("Rust") or lang_counter.get("Zig") or lang_counter.get("Assembly"):
        domains.add("Systems / Native Engineering")
    if artifacts.get("PCAP Network Capture") or artifacts.get("Memory Dump") or (root / "exploits").exists() or (root / "pwn").exists() or (root / "challenges").exists():
        domains.add("Security & Reverse Engineering")
    if artifacts.get("Aseprite Sprite") or (root / "Assets").exists() or lang_counter.get("C#"):
        domains.add("Game Dev / Graphics")
    if (root / "flake.nix").exists() or (root / "Dockerfile").exists() or any(root.glob("*.service")):
        domains.add("Infra & DevOps")
    if lang_counter.get("TypeScript") or lang_counter.get("JavaScript") or (root / "apps" / "web").exists():
        domains.add("Applications & Services")

    # Directory Purpose Mapping
    for sub, desc in GENERIC_DIR_ROLES.items():
        if (root / sub).is_dir():
            key_dirs[sub] = desc

    return {
        "domains": sorted(list(domains)) or ["General Software"],
        "manifests": manifests,
        "commands": commands,
        "languages": lang_counter.most_common(7),
        "artifacts": artifacts.most_common(5),
        "key_dirs": key_dirs,
        "total_files": total_files
    }


def generate_compact_tree(root: Path, max_depth: int = 3, max_entries: int = 60) -> str:
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


def get_readme_summary(root: Path, max_chars: int = 600) -> str:
    """Extract a brief summary from README.md if present."""
    for name in ["README.md", "README", "readme.md"]:
        f = root / name
        if f.exists() and f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                summary = " ".join(lines[:8])
                if len(summary) > max_chars:
                    summary = summary[:max_chars].rstrip() + "..."
                return summary
            except Exception:
                pass
    return ""


def build_project_summary(
    root: Path,
    max_depth: int = 3,
    max_files: int = 60
) -> Dict[str, Any]:
    """Compile complete universal project summary object and formatted context string."""
    fp = get_project_fingerprint(root)
    git_info = get_git_info(root)
    scan_info = scan_universal_project(root)
    tree = generate_compact_tree(root, max_depth=max_depth, max_entries=max_files)
    readme = get_readme_summary(root)

    domains_str = " | ".join(scan_info["domains"])
    manifests_str = ", ".join(scan_info["manifests"]) or "None"

    lines = [
        f"[Project Context: {root.name}]",
        f"- Path: {root}",
        f"- Domain: {domains_str}",
        f"- Manifests: {manifests_str}",
        f"- Fingerprint: {fp}"
    ]

    if git_info.get("branch"):
        status_line = f"- Git: branch '{git_info['branch']}' ({git_info['status_summary']})"
        lines.append(status_line)
        if git_info.get("recent_commits"):
            recent_str = " | ".join(git_info["recent_commits"][:2])
            lines.append(f"- Recent Commits: {recent_str}")

    if scan_info["commands"]:
        cmd_items = [f"{k}: `{v}`" for k, v in list(scan_info["commands"].items())[:6]]
        lines.append(f"- Commands: {', '.join(cmd_items)}")

    if scan_info["languages"]:
        lang_items = [f"{lang} ({cnt})" for lang, cnt in scan_info["languages"]]
        lines.append(f"- Code ({scan_info['total_files']} files): {', '.join(lang_items)}")

    if scan_info["artifacts"]:
        art_items = [f"{art} ({cnt})" for art, cnt in scan_info["artifacts"]]
        lines.append(f"- Special Artifacts: {', '.join(art_items)}")

    if scan_info["key_dirs"]:
        dir_items = [f"{d}/ ({desc})" for d, desc in list(scan_info["key_dirs"].items())[:6]]
        lines.append(f"- Key Directories: {', '.join(dir_items)}")

    if readme:
        lines.append(f"- Overview: {readme}")

    lines.append(f"\nDirectory Layout:\n```\n{tree}\n```")

    formatted = "\n".join(lines)

    return {
        "project_name": root.name,
        "root_path": str(root),
        "fingerprint": fp,
        "git_info": git_info,
        "scan_info": scan_info,
        "readme": readme,
        "tree": tree,
        "formatted_context": formatted
    }
