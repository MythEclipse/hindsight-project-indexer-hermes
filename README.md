# hindsight-project-indexer-hermes

Smart project indexing, context injection, and background self-update for [Hermes Agent](https://hermes-agent.nousresearch.com/), backed by [Hindsight](https://github.com/MythEclipse) long-term memory.

---

## 💡 The Problem

By default, an AI coding agent starts each session blind:
1. It repeatedly calls `search_files`, `read_file`, and directory listing tools to understand repository layout, tech stack, and dependencies.
2. This consumes unnecessary roundtrips, latency, and context window tokens over and over again.

## 🚀 The Solution

`hindsight-project-indexer-hermes` indexes the codebase **once**, stores the structured overview into **Hindsight** and a fast local disk cache, and updates it only when files actually change.

### Key Features

- **Automatic Project Detection**: Traverses upwards to locate the true project root (via `.git` or package manifests like `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc.).
- **Smart Fingerprinting**: Uses Git commit HEAD + porcelain status (or mtime/size hash fallback) to instantly detect whether the repository has changed since the last index.
- **Rich Tech Stack & Architecture Extraction**:
  - Languages & frameworks (React, Next.js, Hono, Axum, FastAPI, etc.)
  - Active Git branch, latest commit, and dirty state
  - Monorepo detection (pnpm workspaces, Cargo workspaces, apps/ & packages/)
  - Infra detection (Docker, Docker Compose, GitHub Actions, Nix)
  - Key config files & environment templates
- **Hindsight Long-Term Memory Integration**: Synchronizes the project survey into Hindsight memory (`hermes-gemini` bank) with tags `type:project_index` and `project:<name>`.
- **Zero-Latency In-Memory & Disk Caching**: Repeated turns in the same project take `< 1ms` to resolve the cached index.
- **Dynamic Context Injection**: Injects the project context directly via Hermes's `register_system_prompt_section` and `pre_llm_call`.
- **Change Invalidation Hook**: Listens to `post_tool_call` on file-modifying tools (`write_file`, `patch`, `terminal`, `execute_code`) and flags the index as dirty so updates occur smoothly on the next turn.
- **Automatic Self-Updating**:
  - Built-in background update check (`auto_update.py`): polls git remote at bounded intervals (every 30 mins) and fast-forwards `main` automatically without restarting or stalling Hermes.
  - Manual update command `/project-indexer-update` and tool `project_indexer_update`.

---

## 📦 Architecture

```
Project Directory
      │
      ▼
┌─────────────────────────────────┐
│       indexer.py                │
│  - find_project_root()          │
│  - get_git_info()               │
│  - get_project_fingerprint()    │
│  - analyze_tech_stack()         │
│  - generate_compact_tree()      │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     hindsight_sync.py           │
│  - In-memory cache (< 1ms)      │
│  - Disk cache (~/.hermes/cache) │
│  - Async Hindsight retain       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     auto_update.py              │
│  - Background git fetch & merge │
│  - Fast-forward auto sync       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     __init__.py (Hermes Plugin) │
│  - register_system_prompt_sec() │
│  - pre_llm_call / post_tool_call│
│  - /reindex, /projectinfo,      │
│    /project-indexer-update      │
│  - Hermes Tools                 │
└─────────────────────────────────┘
```

---

## 🛠️ CLI Commands & Tools

### User Commands
- `/reindex`: Force an immediate re-index of the active project and sync to Hindsight.
- `/projectinfo`: View the detected tech stack, git branch, root path, fingerprint, and Hindsight bank configuration.
- `/project-indexer-update`: Manually trigger git fetch and fast-forward update of the plugin.

### Agent Tools
- `project_index_status`: Tool for the model to check current project status, git branch, and fingerprint.
- `project_reindex`: Tool for the model to trigger a refreshed codebase scan.
- `project_indexer_update`: Tool for the model to self-update the plugin repository.

---

## ⚙️ Configuration

In your Hermes configuration (`~/.hermes/config.yaml`):

```yaml
plugins:
  enabled:
    - hindsight-project-indexer-hermes
```

The plugin automatically reads Hindsight API settings from `~/.hermes/hindsight/config.json` (falling back to `HINDSIGHT_API_URL` and `HINDSIGHT_BANK_ID` environment variables).

---

## 🧪 Testing

Run unit tests:

```bash
python -m unittest discover -s tests
```

---

## 📄 License

MIT License. Crafted with precision for Hermes Agent and the Hindsight memory ecosystem.
