# hindsight-project-indexer-hermes (v0.4.0)

Universal codebase indexing, architectural topology, execution flow inference, and project rule extraction for [Hermes Agent](https://hermes-agent.nousresearch.com/), backed by [Hindsight](https://github.com/MythEclipse) long-term memory.

---

## 💡 The Problem

By default, an AI agent starts each session blind:
1. It repeatedly calls `search_files`, `read_file`, and exploratory commands to understand project domain, architecture, data flow, and conventions.
2. It risks breaking project rules (e.g. committing secrets, using banned dependencies, ignoring commit formats) because it hasn't read `CLAUDE.md`, `AGENTS.md`, or lint rules.
3. This wastes context window tokens, roundtrip latency, and causes repetitive cold starts.

## 🚀 The Solution: Rich Architecture & Rule Indexing

`hindsight-project-indexer-hermes` provides **deep, stack-agnostic codebase understanding**:
It indexes once, syncs the survey to **Hindsight memory** (`hermes-gemini` bank) and a sub-millisecond local cache, and keeps all fleet hosts updated automatically.

### 🌟 What Gets Indexed

1. **Architecture Pattern Detection**:
   - Domain-Driven Design (DDD), Clean / Hexagonal Architecture, Layered Services, Monorepos, Microservices, Event-Driven / Queue Pipelines, Plugins / Hooks, ML Training / Inference Engines.
2. **Inferred Execution & Data Flow**:
   - Detects pipeline stages: e.g. `Webhook Intake -> Queue Dispatch -> Worker Processing -> Storage -> API Egress`.
3. **Core Project Rules & Invariants**:
   - Extracts actionable constraints from `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `RULES.md`, and linter configs (`biome.json`, `eslint`, `ruff.toml`, `clippy.toml`, `rustfmt.toml`, `pre-commit`).
4. **Environment & Secrets Requirements**:
   - Extracts required keys from `.env.example`, `.env.sample`, `.env.dist` without leaking sensitive values.
5. **Domain Classification**:
   - Automatically classifies the active workspace (ML/CUDA, Systems/Native, CTF/Security, GameDev, DevOps, Apps).
6. **Build & Execution Commands**:
   - Discovers build/run/test commands from `Cargo.toml`, `Makefile`, `CMakeLists.txt`, `pyproject.toml`, `package.json`, etc.
7. **Special Artifacts & Assets**:
   - Detects model weights (GGUF, SafeTensors, PyTorch), network pcaps, memory dumps, and compiled binaries.
8. **Live Git Status & History**:
   - Active branch, latest commits with relative timestamps, working tree cleanliness.
9. **Compact Layout Tree**:
   - Filtered hierarchy omitting noisy build caches (`target/`, `build/`, `node_modules/`, `dist/`, `__pycache__`, etc.).

---

### 📋 Example Injected Context

```markdown
[Project Context: 9router]
- Path: /home/asephs/Projects/9router
- Domain: Applications & Services | Infra & DevOps
- Manifests: Nix Flake, Node/Bun/TS
- Fingerprint: 1d948aefe92dcc3e
- Architecture: Monorepo / Workspaces
- Inferred Flow: Route dispatch
- Git: branch 'master' (clean)
- Recent Commits: 0ace6b5b chore: adjust package.json version (bump) (15 hours ago)
- Commands: dev: `bun --filter 9router-web dev`, build: `bun --filter 9router-web build`, test: `vitest run`
- Core Rules & Invariants:
  • Translators self-register via register(from, to, reqFn, resFn) as an import side effect
  • Never hardcode role/block/model strings - use schema constants
  • Security-sensitive env: JWT_SECRET, INITIAL_PASSWORD
- Environment Keys: JWT_SECRET, INITIAL_PASSWORD, DATA_DIR, PORT, NODE_ENV, API_KEY_SECRET
- Code (4743 files): TypeScript (3458), TypeScript (UI) (433), Markdown (150), JSON (96)

Directory Layout:
...
```

---

## 🔄 Automatic Fleet Self-Updating

- **In-Plugin Background Thread**: Polls git remote every 30 minutes and fast-forwards `main` automatically.
- **Systemd Timer & Cron**: Runs on Omarchy, OrangeVPS, and Imrnes to pull latest commits automatically.
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
