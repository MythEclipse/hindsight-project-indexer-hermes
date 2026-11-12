# hindsight-project-indexer-hermes (v0.3.0)

Universal, stack-agnostic project indexing, context injection, and background self-update for [Hermes Agent](https://hermes-agent.nousresearch.com/), backed by [Hindsight](https://github.com/MythEclipse) long-term memory.

---

## 💡 The Problem

By default, an AI agent starts each session blind:
1. It repeatedly calls `search_files`, `read_file`, and exploratory commands to understand project domain, language composition, build commands, and file structure.
2. Most existing tools assume projects are just web applications.
3. This consumes unnecessary latency, token budget, and model roundtrips across all domains (ML, CTF, systems, gamedev, backend, etc.).

## 🚀 The Solution: Universal Indexing

`hindsight-project-indexer-hermes` provides **general, stack-agnostic codebase indexing**:
It indexes once, syncs the survey to **Hindsight memory** (`hermes-gemini` bank) and a sub-millisecond local cache, and keeps all fleet hosts updated automatically.

### 🌟 Universal Domains Supported

- **ML / AI & GPU Systems**: PyTorch, CUDA kernels (`.cu`, `.cuh`), Jupyter notebooks (`.ipynb`), model weights (`.gguf`, `.safetensors`, `.pt`, `.onnx`), model directories (`models/`, `weights/`).
- **Systems & Native Engineering**: C, C++, Rust, Zig, Assembly (`.asm`, `.s`), Makefiles, CMake, Meson, Cargo.
- **Security & Reverse Engineering (CTF)**: PCAP network captures (`.pcap`, `.pcapng`), memory dumps (`.dmp`), ELF/PE binaries, exploit/challenge folders (`exploits/`, `pwn/`, `challenges/`).
- **Game Dev & Creative Graphics**: Unity C# (`.cs`, `.unity`, `.prefab`), Shaders (`.hlsl`, `.glsl`), Blender scenes (`.blend`), Aseprite pixel art (`.ase`, `.aseprite`).
- **Infra, DevOps & Containers**: Nix flakes (`flake.nix`), Dockerfiles, Docker Compose, systemd unit files, Shell scripts (`.sh`, `.bash`).
- **Applications & Services**: CLI tools, background bots, APIs, desktop apps, and web frontends.

---

### 🔍 What Gets Indexed

1. **Domain Classification**: Automatically classifies the active workspace (e.g. `ML / AI & GPU Systems | Systems / Native Engineering`).
2. **Build & Execution Commands**: Discovers build/run/test commands from `Cargo.toml`, `Makefile`, `CMakeLists.txt`, `pyproject.toml`, `package.json`, etc.
3. **Language Composition**: Scans and counts lines/files across 45+ languages.
4. **Special Artifacts**: Detects model weights, network pcaps, memory dumps, and compiled binaries.
5. **Key Directory Mapping**: Identifies purpose of folders (`core/`, `kernel/`, `models/`, `tools/`, `exploits/`, `scripts/`, `docs/`, `apps/`, `crates/`).
6. **Live Git Status & History**: Active branch, latest commit with relative timestamp, cleanliness.
7. **Compact Layout Tree**: Filtered hierarchy omitting noisy build caches (`target/`, `build/`, `node_modules/`, `dist/`, `__pycache__`, etc.).

---

### 📋 Example Injected Context

```markdown
[Project Context: llm]
- Path: /home/asephs/Projects/llm
- Domain: ML / AI & GPU Systems | Systems / Native Engineering
- Manifests: Rust (Cargo)
- Fingerprint: a1b2c3d4e5f6
- Git: branch 'main' (clean)
- Recent Commits: 8c12f4a feat: add flash-decoding kernel (2 hours ago)
- Commands: build: `cargo build`, test: `cargo test`
- Code (106 files): Rust (65), Python (6), Markdown (6), TOML (5)
- Special Artifacts: GGUF Model (6), Weight/Binary Blob (3)
- Key Directories: models/ (Model files / weights), tests/ (Test suite), docs/ (Documentation)

Directory Layout:
...
```

---

## 🔄 Automatic Fleet Self-Updating

- **In-Plugin Background Thread**: Polls git remote every 30 minutes and fast-forwards `main` automatically.
- **CLI Commands**:
  - `/reindex`: Force immediate codebase re-scan and Hindsight sync.
  - `/projectinfo`: View active project domain, git state, and commands.
  - `/project-indexer-update`: Force pull latest plugin code from GitHub.
- **Agent Tools**: `project_index_status`, `project_reindex`, `project_indexer_update`.

---

## 🧪 Testing

```bash
python -m unittest discover -s tests
```

---

## 📄 License

MIT License. Designed for Hermes Agent and the Hindsight memory ecosystem.
