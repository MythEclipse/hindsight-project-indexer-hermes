# hindsight-project-indexer-hermes (v0.5.0)

Universal codebase indexing, architectural topology, execution flow inference, project rule extraction, public API mapping, incremental git diff syncing, dynamic workspace switching, and Level-of-Detail (LoD) token budgeting for [Hermes Agent](https://hermes-agent.nousresearch.com/), backed by [Hindsight](https://github.com/MythEclipse) long-term memory.

---

## 💡 The Problem

By default, an AI agent starts each session blind:
1. It repeatedly calls `search_files`, `read_file`, and exploratory commands to understand project domain, architecture, data flow, public symbols, and conventions.
2. When code changes across commits, the agent knows the file modified but forgets the *technical reasoning* or invariants behind the change.
3. Switching workspaces mid-session leaves the agent confused with stale context.
4. Large repositories (>3,000 files) can bloat the system prompt context.

## 🚀 The Solution: Complete Project Intelligence

`hindsight-project-indexer-hermes` delivers **complete codebase understanding** with minimal context overhead:

### 🌟 Core Capabilities

1. **Incremental Git Diff Ingestion (`strategy: "git"`)**:
   - Detects fresh commits via git commit SHA tracking.
   - Extracts `git log -1 -p --stat` and syncs to Hindsight long-term memory using Hindsight's native `git` strategy.
   - Preserves technical decisions, rationale, and exact code invariants across turns and sessions.

2. **Public API & Export Map (AST/Regex Extraction)**:
   - Scans core entrypoints and workspace modules (`src/`, `apps/*/src`, `packages/*/src`, `crates/*/src`).
   - Extracts top public symbols:
     - **Rust**: `pub mod`, `pub fn`, `pub struct`, `pub enum`, `pub trait`
     - **TypeScript/JS**: `export function`, `export const`, `export class`, `export type`
     - **Python**: `class`, `def` functions
     - **Go**: `type <Name> struct`, `func <Name>()`
     - **C/C++**: `struct`, `class`, function declarations

3. **Dynamic Workspace Switch Detection**:
   - `pre_llm_call` dynamically monitors the active project directory (`find_project_root()`).
   - If you `cd` to another repository mid-conversation, the plugin detects the switch, indexes the new repo, and injects `[Workspace Switched: <project_name>]` seamlessly.

4. **Level of Detail (LoD) Token Budgeting**:
   - **Standard Mode (Automatic Injection)**: Tight, high-density summary (~400–600 tokens) with domain, commands, architecture, flow, top rules, and top exports.
   - **Deep Mode (On-demand via `/reindex --deep` or `project_index_status(deep=true)`)**: Expanded context (~1500–2500 tokens) with deep file tree (depth 4, 80 files), complete public API maps, all environment keys, and extended commit logs.

5. **Universal Architecture & Flow Detection**:
   - Detects DDD (Domain-Driven Design), Clean / Hexagonal, Layered, Monorepo / Workspaces, Pipelines, and ML Training/Inference engines.
   - Inferred pipeline flows: e.g. `Route dispatch -> Service layer` or `Webhook intake -> Queue dispatch -> Worker processing`.

6. **Core Rules, Invariants & Linters**:
   - Extracts actionable constraints from `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `RULES.md`, and linter configs (`biome.json`, `eslint`, `ruff.toml`, `clippy.toml`, `rustfmt.toml`).

---

### 📋 Example Injected Context

```markdown
[Project Context: llm]
- Path: /home/asephs/Projects/llm
- Domain: Applications & Services | ML / AI & GPU Systems | Systems / Native Engineering
- Manifests: Rust (Cargo)
- Fingerprint: 2c55e739c5759f19
- Architecture: Monorepo / Workspaces
- Git: branch 'main' (clean)
- Recent Commits: 09a403e feat(engine): raise the window to 32k by shrinking the prefill chunk (7 days ago)
- Commands: build: `cargo build`, test: `cargo test`
- Core Public APIs / Exports:
  • apps/engine/src/lib.rs: pub mod byte_level, pub mod chat, pub mod compute, pub mod deltanet
  • apps/api/src/lib.rs: pub mod application, pub mod domain, pub mod infrastructure, pub mod presentation
- Code (107 files): Rust (65), Markdown (6), Python (6), JSON (6), TOML (5)
- Special Artifacts: GGUF Model (6), Weight/Binary Blob (3)
- Key Directories: models/ (Model files / weights), tests/ (Test suite), docs/ (Documentation)

Directory Layout:
...
```

---

## 🔄 Automatic Fleet Self-Updating

- **In-Plugin Background Thread**: Polls git remote every 30 minutes and fast-forwards `main` automatically.
- **Systemd Timer & Cron**: Runs on Omarchy, OrangeVPS, and Imrnes to pull latest commits automatically.
- **CLI Commands**:
  - `/reindex [--deep]`: Force immediate codebase re-scan and Hindsight sync.
  - `/projectinfo [--deep]`: View active project domain, git state, public APIs, and commands.
  - `/project-indexer-update`: Force pull latest plugin code from GitHub.
- **Agent Tools**: `project_index_status(deep=bool)`, `project_reindex(deep=bool)`, `project_indexer_update`.

---

## 🧪 Testing

```bash
python -m unittest discover -s tests
```

---

## 📄 License

MIT License. Designed for Hermes Agent and the Hindsight memory ecosystem.
