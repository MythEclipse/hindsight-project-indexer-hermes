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



# ─────────────────────────────────────────────────────────────────────────────
# RICH INDEXING: ARCHITECTURE, FLOW, CONVENTIONS, AND RULES
# ─────────────────────────────────────────────────────────────────────────────

ARCH_PATTERNS: Dict[str, List[str]] = {
    "Domain-Driven Design (DDD)": ["domain", "application", "infrastructure", "presentation"],
    "Clean / Hexagonal Architecture": ["adapters", "ports", "use_cases", "entities"],
    "Layered Architecture": ["controllers", "services", "repositories", "models"],
    "Monorepo / Workspaces": ["apps", "packages", "crates", "workspace"],
    "Microservices": ["services", "gateway", "docker-compose", "k8s", "kubernetes"],
    "Event-Driven / Queue-Based": ["events", "workers", "queue", "consumers", "publishers"],
    "Plugin / Extension System": ["plugins", "extensions", "registry", "hooks"],
    "Pipeline / Stage-Based": ["pipeline", "stages", "steps", "processors"],
    "Layered Kernel / Engine": ["kernel", "engine", "backend", "frontend", "runtime"],
    "ML / Training Pipeline": ["train", "inference", "dataset", "checkpoint", "tokenizer", "model"],
}

RULE_FILE_PATTERNS: List[Tuple[str, str]] = [
    ("CLAUDE.md", "Project rules (Claude)"),
    ("AGENTS.md", "Project rules (Agents)"),
    ("CONTRIBUTING.md", "Contribution guidelines"),
    ("ARCHITECTURE.md", "Architecture documentation"),
    ("RULES.md", "Explicit project rules"),
    (".cursorrules", "Cursor AI rules"),
    (".editorconfig", "EditorConfig (formatting)"),
    ("rustfmt.toml", "Rust formatting rules"),
    ("clippy.toml", "Rust lint rules"),
    ("ruff.toml", "Ruff Python lint rules"),
    (".ruff.toml", "Ruff Python lint rules"),
    ("biome.json", "Biome format & lint"),
    ("eslint.config.mjs", "ESLint rules"),
    (".eslintrc", "ESLint rules"),
    (".pre-commit-config.yaml", "Pre-commit hooks"),
    (".lintstagedrc", "lint-staged"),
    ("commitlint.config.js", "Commit message linting"),
    (".commitlintrc", "Commit message linting"),
]

PIPELINE_INDICATORS: List[Tuple[str, str]] = [
    ("webhook", "Webhook intake"),
    ("queue", "Queue / job dispatch"),
    ("worker", "Worker processing"),
    ("scheduler", "Scheduled jobs"),
    ("cron", "Scheduled jobs"),
    ("pipeline", "Multi-stage pipeline"),
    ("middleware", "Middleware chain"),
    ("router", "Route dispatch"),
    ("handler", "Request handler"),
    ("controller", "Controller layer"),
    ("service", "Service layer"),
    ("repository", "Data access layer"),
    ("adapter", "Adapter / port"),
    ("consumer", "Event consumer"),
    ("producer", "Event producer"),
    ("publisher", "Event publisher"),
    ("subscriber", "Event subscriber"),
]


def detect_architecture_patterns(root: Path, scan_info: Dict[str, Any]) -> List[str]:
    """Infer architectural patterns from directory structure and manifest hints."""
    found: List[str] = []
    all_dirs: Set[str] = set()
    try:
        for p in root.iterdir():
            if p.is_dir() and p.name not in IGNORED_DIRS and not p.name.startswith("."):
                all_dirs.add(p.name)
    except Exception:
        pass

    # Check nested structure hints for DDD/Clean/Layered
    for pattern, hints in ARCH_PATTERNS.items():
        hit = sum(1 for h in hints if h in all_dirs or (root / h).exists())
        if hit >= 2 or (pattern in ("Monorepo / Workspaces", "Microservices") and hit >= 1):
            found.append(pattern)

    # Add monorepo check from manifests
    if scan_info.get("manifests"):
        if any("workspace" in m.lower() for m in scan_info["manifests"]) and "Monorepo / Workspaces" not in found:
            found.append("Monorepo / Workspaces")

    return found[:5]


def detect_project_rules(root: Path) -> Dict[str, Any]:
    """Extract convention/rule files and notable explicit rules from project docs."""
    rule_files: List[str] = []
    extracted_rules: List[str] = []

    for fname, label in RULE_FILE_PATTERNS:
        f = root / fname
        if f.is_file():
            rule_files.append(label)

    # Extract top actionable rules from CLAUDE.md / AGENTS.md / CONTRIBUTING.md
    for fname in ["CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md", "RULES.md"]:
        f = root / fname
        if not f.is_file():
            continue
        try:
            txt = f.read_text(encoding="utf-8")
            for line in txt.splitlines():
                s = line.strip()
                if s.startswith(("- ", "* ")):
                    clean = re.sub(r"^[-*]+\s*", "", s).strip()
                    if len(clean) > 12 and any(
                        w in clean.lower() for w in
                        ["never", "always", "must", "rule", "convention", "required", "forbidden", "do not"]
                    ):
                        if clean not in extracted_rules and len(extracted_rules) < 8:
                            extracted_rules.append(clean[:120])
        except Exception:
            pass

    return {
        "rule_files": rule_files,
        "rules": extracted_rules,
    }


def detect_execution_flow(root: Path) -> List[str]:
    """Infer execution/data flow stages from directory structure and file naming."""
    flow: List[str] = []
    seen = set()

    # Look for pipeline-like top-level and one-level dirs
    candidates: List[str] = []
    try:
        for p in root.rglob("*"):
            rel = p.relative_to(root)
            if len(rel.parts) > 2:
                continue
            if any(part in IGNORED_DIRS or part.startswith(".") for part in rel.parts):
                continue
            candidates.append(p.name.lower())
    except Exception:
        pass

    for name in candidates:
        for keyword, label in PIPELINE_INDICATORS:
            if keyword in name and label not in seen:
                flow.append(label)
                seen.add(label)

    # Deduplicate and preserve order
    return flow[:8]


def extract_env_keys(root: Path) -> List[str]:
    """Extract configuration environment keys from .env templates."""
    keys: List[str] = []
    for cand in [".env.example", ".env.sample", ".env.template", ".env.dist"]:
        f = root / cand
        if not f.is_file():
            continue
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k = s.split("=", 1)[0].strip()
                    if k and k not in keys:
                        keys.append(k)
        except Exception:
            pass
    return keys[:15]



def extract_public_api_map(root: Path, max_symbols: int = 16) -> Dict[str, List[str]]:
    """Extract key exported functions, types, and modules from core source files."""
    api_map: Dict[str, List[str]] = {}
    total = 0

    patterns = [
        "src/lib.rs", "src/main.rs", "src/index.ts", "src/index.js", "src/main.ts",
        "apps/*/src/lib.rs", "apps/*/src/main.rs", "apps/*/src/index.ts", "apps/*/src/main.ts",
        "packages/*/src/index.ts", "crates/*/src/lib.rs", "crates/*/src/main.rs",
        "main.py", "app.py", "src/app.py", "main.go"
    ]
    core_files: List[Path] = []
    for pat in patterns:
        for match in root.glob(pat):
            if match.is_file() and not any(part in IGNORED_DIRS for part in match.relative_to(root).parts):
                core_files.append(match)
                if len(core_files) >= 8:
                    break

    for f in core_files[:6]:
        rel = str(f.relative_to(root))
        symbols: List[str] = []
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
            if f.suffix == ".rs":
                matches = re.findall(r"pub\s+(?:async\s+)?(mod|fn|struct|enum|trait|type)\s+([A-Za-z0-9_]+)", txt)
                symbols.extend([f"pub {k} {n}" for k, n in matches[:6]])
            elif f.suffix in (".ts", ".js", ".tsx", ".jsx"):
                matches = re.findall(r"export\s+(?:default\s+)?(?:async\s+)?(function|class|const|type|interface)\s+([A-Za-z0-9_]+)", txt)
                symbols.extend([f"export {k} {n}" for k, n in matches[:6]])
            elif f.suffix == ".py":
                matches = re.findall(r"^(?:async\s+)?def\s+([A-Za-z0-9_]+)|class\s+([A-Za-z0-9_]+)", txt, re.MULTILINE)
                for fn, cls in matches[:6]:
                    if fn and not fn.startswith("_"):
                        symbols.append(f"def {fn}()")
                    elif cls and not cls.startswith("_"):
                        symbols.append(f"class {cls}")
            elif f.suffix == ".go":
                matches = re.findall(r"(?:type\s+([A-Z][A-Za-z0-9_]+)|func\s+([A-Z][A-Za-z0-9_]+))", txt)
                for t, fn in matches[:6]:
                    if t: symbols.append(f"type {t}")
                    if fn: symbols.append(f"func {fn}()")
        except Exception:
            pass

        if symbols:
            api_map[rel] = symbols[:5]
            total += len(symbols[:5])
            if total >= max_symbols:
                break

    return api_map


def get_latest_commit_diff(root: Path, max_chars: int = 4000) -> Optional[str]:
    """Extract latest git commit patch diff for technical decision syncing in Hindsight."""
    if not (root / ".git").exists():
        return None
    try:
        diff = subprocess.check_output(
            ["git", "-C", str(root), "log", "-1", "-p", "--stat"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        if not diff:
            return None
        if len(diff) > max_chars:
            diff = diff[:max_chars] + "\n... [diff truncated for memory budget]"
        return diff
    except Exception:
        return None


def build_project_summary(
    root: Path,
    mode: str = "standard",
    max_depth: Optional[int] = None,
    max_files: Optional[int] = None
) -> Dict[str, Any]:
    """Compile universal project summary with Level-of-Detail (LoD) token budgeting."""
    is_deep = (mode == "deep")
    eff_depth = max_depth if max_depth is not None else (4 if is_deep else 2)
    eff_files = max_files if max_files is not None else (80 if is_deep else 30)

    fp = get_project_fingerprint(root)
    git_info = get_git_info(root)
    scan_info = scan_universal_project(root)
    tree = generate_compact_tree(root, max_depth=eff_depth, max_entries=eff_files)
    readme = get_readme_summary(root, max_chars=1000 if is_deep else 400)

    arch_patterns = detect_architecture_patterns(root, scan_info)
    exec_flow = detect_execution_flow(root)
    rules_data = detect_project_rules(root)
    env_keys = extract_env_keys(root)
    api_map = extract_public_api_map(root, max_symbols=25 if is_deep else 10)

    domains_str = " | ".join(scan_info["domains"])
    manifests_str = ", ".join(scan_info["manifests"]) or "None"

    tag = f"Project Context: {root.name} (Deep Mode)" if is_deep else f"Project Context: {root.name}"
    lines = [
        f"[{tag}]",
        f"- Path: {root}",
        f"- Domain: {domains_str}",
        f"- Manifests: {manifests_str}",
        f"- Fingerprint: {fp}"
    ]

    if arch_patterns:
        lines.append(f"- Architecture: {', '.join(arch_patterns)}")

    if exec_flow:
        lines.append(f"- Inferred Flow: {' -> '.join(exec_flow)}")

    if git_info.get("branch"):
        status_line = f"- Git: branch '{git_info['branch']}' ({git_info['status_summary']})"
        lines.append(status_line)
        if git_info.get("recent_commits"):
            recent_slice = git_info["recent_commits"] if is_deep else git_info["recent_commits"][:2]
            lines.append(f"- Recent Commits: {' | '.join(recent_slice)}")

    if scan_info["commands"]:
        cmd_limit = 10 if is_deep else 5
        cmd_items = [f"{k}: `{v}`" for k, v in list(scan_info["commands"].items())[:cmd_limit]]
        lines.append(f"- Commands: {', '.join(cmd_items)}")

    if api_map:
        lines.append("- Core Public APIs / Exports:")
        api_limit = 5 if is_deep else 2
        for mod, syms in list(api_map.items())[:api_limit]:
            lines.append(f"  • {mod}: {', '.join(syms[:4])}")

    if rules_data["rules"]:
        lines.append("- Core Rules & Invariants:")
        rule_limit = 8 if is_deep else 3
        for r in rules_data["rules"][:rule_limit]:
            lines.append(f"  • {r}")

    if env_keys:
        env_limit = 15 if is_deep else 6
        lines.append(f"- Environment Keys: {', '.join(env_keys[:env_limit])}")

    if scan_info["languages"]:
        lang_limit = 10 if is_deep else 5
        lang_items = [f"{lang} ({cnt})" for lang, cnt in scan_info["languages"][:lang_limit]]
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
        "mode": mode,
        "fingerprint": fp,
        "git_info": git_info,
        "scan_info": scan_info,
        "arch_patterns": arch_patterns,
        "exec_flow": exec_flow,
        "rules_data": rules_data,
        "env_keys": env_keys,
        "api_map": api_map,
        "readme": readme,
        "tree": tree,
        "formatted_context": formatted
    }
