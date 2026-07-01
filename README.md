# Hia Wiki Memory Skill 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Hia Wiki Memory Skill** is an enterprise-grade, token-efficient, and deterministic long-term memory management system for Autonomous AI Agents (OpenClaw, AutoGen, Claude Code, CrewAI, etc.). 

Instead of relying on unstructured chat history or purely probabilistic vector databases, this skill enforces a structured **Flat Storage + Tiered Manifests system** to give your Agents a permanent, organized, and shared "External Brain".

---

## 🎯 The Problem It Solves

As AI Agents run longer tasks, their default memory (chat history) grows exponentially. This leads to:
1. **Context Bloat:** Maxing out token limits and increasing API costs.
2. **Hallucinations:** Forgetting old instructions or mixing up versions.
3. **Siloed Knowledge:** Agent A cannot easily share complex architectural blueprints with Agent B.
4. **Link Rot (Broken Links):** Moving files between folders physically causes internal links to break.

**The Solution:** Hia Wiki Memory offloads project knowledge into a Flat physical directory (`raw/`), while logically categorizing them into Hot/Warm/Cold tiers using lightweight `Manifest files` at the Root. Agents use Python scripts to read and write to this Wiki, ensuring data is never lost, links never break, and context windows are protected.

---

## ✨ Key Features

- 📂 **Flat Storage + Tiered Manifests:** All knowledge files live permanently in `raw/` so links never break. Tier rotation happens logically by moving paths between `hot_index.md`, `warm_index.md`, and `cold_index.md`.
- 🔄 **Smart Logical Rotation:** A built-in script keeps the working memory (`hot_index.md`) lean (max 50 files). Older paths are automatically appended to `warm_index.md` and `cold_index.md`.
- 🔒 **Enterprise Concurrency (FileLock):** Safe for Multi-Agent environments. Multiple agents can write to the Wiki simultaneously without corrupting data or causing Race Conditions.
- ⚡ **Zero-Latency RAG (ChromaDB):** Real-time vector search. To achieve O(1) skipping, the Vector DB sync script bypasses OS crawling and directly reads `hot_index.md` and `warm_index.md` to instantly know which files to sync.
- 🧟 **Zombie Context Prevention:** Automatically purges deprecated or deleted knowledge from the Vector Database.
- 🔪 **Semantic Chunking:** Automatically splits massively long markdown files (e.g., 50MB logs) by `# Headers` before indexing.
- 🎯 **Hybrid Search:** Combines Vector Search with exact `tags` metadata filtering.
- 🐙 **Invisible GitOps:** Automatically runs `git commit` on every Agent change.

---

## 📂 How the Memory is Structured (The Flat-Manifest Architecture)

When an AI initializes the Wiki, it creates the following structure:

```text
wiki_directory/
│
├── index.md              # 📍 MASTER MAP (Root): Auto-created. Links to Branch maps.
├── branches/             # 🌿 BRANCH MAPS: Groups feature documentation links.
│   └── auth_index.md     # (Example branch map)
│
├── manifests/            # 📜 LOGICAL TIERS: The status of all knowledge.
│   ├── hot_index.md      # 🔴 SHORT-TERM (Active): List of paths to current focus files (max 50).
│   ├── warm_index.md     # 🟡 MID-TERM (Reference): List of paths to older files (< 90 days).
│   ├── cold_index.md     # 🔵 LONG-TERM (Archive): List of paths to > 90 days. Excluded from RAG.
│   └── review_index.md   # 🟠 NEEDS REVIEW: Files flagged for rewarm/audit.
│
├── raw/                  # 🍃 FLAT STORAGE: All Markdown knowledge files live here permanently.
│   ├── auth_v1.md        # (Tracked in cold_index.md)
│   └── auth_v2.md        # (Tracked in hot_index.md)
│
├── .chroma_db/           # 🧠 AI BRAIN (Vector Database - ChromaDB)
├── .chroma_db.lock       # 🔒 FileLock to prevent data collision.
└── .last_sync_mtime      # ⏱️ Sync optimization checkpoint.
```

---

## 🤝 The Synergy: Map vs Search Engine (Index vs VectorDB)

A common architectural question is: *"If we have a Vector Database, why do we still need `index.md`?"*

They work together in perfect synergy without bottlenecking each other:
1. **The Mindmap (`index.md` and Branch indexes):** Agents MUST read this first to get a "Bird's-eye view" of the project and discover correct terminology (Context). 
2. **The Search Engine (ChromaDB):** Once the Agent knows the domain structure and vocabulary from the Map, it uses `search_wiki.py` (Hybrid Search) to teleport directly to the specific code/knowledge chunk (Leaf) in `raw/` without reading thousands of lines.

---

## 🚀 Quick Start (Auto-Setup via AI)

You do **NOT** need to manually configure this skill. You can leverage your AI Agent's intelligence to set itself up. 

Simply copy the **Magic Prompt** below and paste it into your Agent's chat interface (OpenClaw, AutoGen, etc.):

> **The Universal Setup Prompt (Copy & Paste for your AI):**
> *"Hello AI, I want to equip you with a Long-Term Memory System using the `hia-wiki-memory-skill` folder I just downloaded. Please act as a System Architect and execute this automated setup immediately:
> 
> 1. **Install Dependencies:** Open the terminal and run `pip install -r requirements.txt` inside the skill's folder.
> 2. **Determine Wiki Location:** Ask me where I want to store the Wiki directory (If I don't answer, automatically select a default folder in my OneDrive to ensure data safety).
> 3. **Learn Core Knowledge:** Use your file reading tool to thoroughly read `SKILL.md`. You must memorize the rules regarding Manifest Indexes, and especially the 'Isolation Rule' (Agents are forbidden from reading warm/cold indexes).
> 4. **Initialize:** Once the location is confirmed, run `python scripts/init_wiki.py --wiki_dir <selected_location>` to bootstrap the storage.
> 5. **The Pledge:** From now on, you may use your default memory to converse smoothly with me, BUT for architectural details, code logic, or major decisions, you MUST use `update_wiki.py` to write and `search_wiki.py` to search.
> 
> Please confirm and begin steps 1 and 2 right now!"*

---

## 📖 How Agents Use It

Once installed, your Agents will interact with the Wiki using 4 robust Python scripts:

1. `init_wiki.py`: Bootstraps the `raw/`, `branches/` and `manifests/` indexes.
2. `update_wiki.py`: The single entry point for writing. Saves to `raw/`, enforces YAML frontmatter, updates the manifest, and uses `FileLock`. **Supports reading from `--source_file` or `stdin` for huge files.**
3. `search_wiki.py`: A Semantic RAG search tool. Directly parses `hot_index.md` and `warm_index.md` to instantly locate active files for DB syncing.
4. `rotate_wiki.py`: A maintenance script that logically moves paths from Hot to Warm to Cold manifests based on age. It also flags old files for "Rewarm" and Garbage Collects deprecated files.
5. `check_links.py`: Detects broken links in `index.md` and `branches/` and marks them with `❌ (DELETED)`.
6. `export_memory_state.py` & `build_dashboard.py`: Exports memory state to JSON and generates a stunning HTML Dashboard to visualize what the Agents know.

---

## 🤖 Best Practice: The Hierarchical Proxy Pattern (For Enterprise Multi-Agent Systems)

If you are running a single Agent, giving it direct access to this Wiki is fine. However, if you are running a massive Multi-Agent system, **do NOT give every sub-agent direct access to the Wiki tools.** 

Instead, use the **Hierarchical Proxy Pattern**:
1. Create a dedicated **Main Agent (Orchestrator)** and a **Librarian Agent**.
2. Give ONLY the Librarian the `update_wiki` and `search_wiki` tools.
3. The 100+ Worker Agents (Coders, QAs) DO NOT know about the Wiki. They simply report task completions to the Main Agent.
4. The Main Agent synthesizes the workers' reports and messages the Librarian to store the consolidated knowledge. This keeps the Wiki perfectly clean and protects all Workers from Context Bloat.

---

## 🏢 Advanced & Enterprise Integration

- **[Orchestrator Pipeline](advanced_guides/platform_integration.md#-2-enterprise-topology-the-hierarchical-proxy-model):** Set up a "Manager Agent" (e.g., Helu) to review the Wiki.
- **[Cross-Platform Integration](advanced_guides/platform_integration.md):** Specific instructions for integrating this skill into UI frameworks.

---

## ⚠️ Known Limitations

As the system evolves, please be aware of the following architectural limits:
1. **Single Librarian Bottleneck:** Currently, the system uses a single Librarian Agent to handle all `update_wiki.py` requests via FileLock. It does not yet support multiple Librarians sharded by domain (e.g., one for Backend, one for Frontend), which may cause queueing delays with 100+ concurrent worker agents.
2. **Flexible Agent Messaging:** The communication between the Main Agent and the Librarian Agent relies on natural language. There is no hard JSON schema enforced for these messages yet.
3. **Cloud & Redis Lock:** The `cloud_api_migration.md` guide outlines a roadmap for using Redis distributed locks for cloud-scale deployments. This is an opt-in draft and has not been integrated into the core `update_wiki.py` script yet.

---
*Built for the future of Multi-Agent Systems. Code smarter, remember forever.*
