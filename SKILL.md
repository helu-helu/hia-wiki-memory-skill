---
name: Hia Wiki Memory (LLM-WIKI)
description: >
  Memory management skill using a Flat Storage + Tiered Manifests architecture combined with a Zero-Latency Vector Database.
  Agents MUST use this skill to persist long-term project knowledge. You MAY use your default memory for short-term conversational flow, but NEVER rely on it for project facts or architectural states. Always fetch and write facts to this Wiki.
---

# Hia Wiki Memory Skill

This skill enforces a robust, token-efficient, deterministic knowledge management system for agents.
Instead of relying on unstructured chat history, this skill uses a Flat physical storage (`raw/`) with Logical Tiering (`hot_index.md`, `warm_index.md`, `cold_index.md`) combined with a Zero-Latency Vector Database (ChromaDB / Pinecone) for Hybrid Search.
This system is Cloud-Native ready, supporting Distributed Locks via Redis and an optional FastAPI Microservice (`api/main.py`).

## 🤖 Agent Identity & Dynamic Role
When you receive this skill, you must understand two critical things about your role:
1. **Proactive Memory Storage:** You have the FULL AUTHORITY and RESPONSIBILITY to store experiences, workflow solutions, bug fixes, or architectural patterns into this Wiki. Do not wait for the User to tell you "save this". If you learn something valuable, use `update_wiki.py` (or request the Librarian) to save it immediately.
2. **Adaptable Role:** Your specific task in this memory ecosystem can change based on the User's command. The User might configure you as the sole "Librarian Agent" (managing memory for other agents), or as a "Coder" who must hand off notes to the Librarian. Always clarify and adapt to the workflow the User requests.
3. **Proactive Maintenance:** You must monitor the health of the Wiki. If you complete a major feature sprint or notice many files have been added, proactively remind the User to let you run `rotate_wiki.py` to freeze old data and `check_links.py` to maintain integrity.
4. **Dashboard Assistant:** If the User asks about the state of the memory or wants a visual report, you must immediately run `export_memory_state.py` followed by `build_dashboard.py`, and then provide the absolute file path of the generated HTML dashboard to the User so they can view it.

## Principles & Enterprise Scale
1. **The Root (`index.md`)**: This is the Master Map. To prevent this file from exploding with 1000+ links, it MUST ONLY contain high-level domains (e.g., Frontend, Backend, Database) and link to Branch indexes located in `branches/`.
2. **The Manifest Indexes**: All actual knowledge files live permanently in `raw/`. Their active status is tracked in `manifests/hot_index.md`, `manifests/warm_index.md`, and `manifests/cold_index.md`. 
3. **The Isolation Rule (CRITICAL)**: **AGENTS ARE STRICTLY FORBIDDEN FROM READING `warm_index.md` OR `cold_index.md` DIRECTLY.** These files contain thousands of links and will crash your Context Window. They exist ONLY for Python scripts to parse. To find older information, ALWAYS use `search_wiki.py`.
4. **Hybrid Search for Leaves**: DO NOT manually `os.walk` or guess file paths in `raw/`. ALWAYS use `search_wiki.py` to jump directly to the precise knowledge chunk.
5. **The Leaves (Markdown files)**: Every leaf MUST have YAML frontmatter. `status: deprecated` means the leaf is dead. NEVER use deprecated information.
6. **Scripts are for Execution:** NEVER use terminal commands (like `echo`, `cat`, `sed`) to manually edit wiki files or YAML frontmatter. ALWAYS use the provided Python scripts in this skill. This prevents formatting errors and updates Manifests correctly.
7. **Context Hygiene:** Rely ONLY on the fresh data you read from the Wiki. If your default memory conflicts with the Wiki, the Wiki is ALWAYS the Single Source of Truth.

## Wiki Reading Rules (MANDATORY)
When starting any new task, or if you need to recall context:
1. **Read `index.md` FIRST**: You must always read the master index first. You may optionally read `hot_index.md` to see currently active files.
2. **Search Before You Act**: Use `search_wiki.py` with specific queries and `--tags` to find relevant knowledge before writing new code.
3. **Filter Out Deprecated**: If a file has `status: deprecated` or `status: superseded` in its YAML frontmatter, treat its contents as INVALID.
4. **Cold Tier Search**: Cold files are hidden by default from `search_wiki.py` to prevent context noise. If you suspect an old solution exists but cannot find it, you MAY search the cold tier explicitly using `--include-cold`.

## Wiki Writing Rules (MANDATORY)
When you have completed a task, solved a bug, or discovered an architectural pattern, you must persist it.
- **DO NOT** use bash commands to write the file.
- **DO NOT** write raw YAML.
- **DO USE** the `update_wiki.py` script provided in this skill.

## Provided Tools

### 1. `init_wiki.py`
Initializes the Flat Storage + Manifest structure.
Usage: `python path/to/skill/scripts/init_wiki.py --dir <target_directory>`

### 2. `update_wiki.py`
Safely writes or updates a markdown file in `raw/`, updates the YAML frontmatter, and registers the file in the correct Manifest Index.
Usage:
```bash
python path/to/skill/scripts/update_wiki.py --dir <wiki_dir> --tier <hot|warm> --file <filename.md> --title "<Title>" --status <active|deprecated> --content "<Markdown Content>"
```
*Note for Agents: If the content is too large or contains complex formatting, it is highly recommended to write it to a temporary file first using your native `write_to_file` tool, and then pass it via `--source_file`:*
```bash
python path/to/skill/scripts/update_wiki.py --dir <wiki_dir> --tier hot --file large.md --title "Large" --status active --source_file "temp.md"
```
*Alternatively, you can pipe it via stdin by omitting `--content` or using `--content -`:*
```bash
echo "Huge markdown content..." | python path/to/skill/scripts/update_wiki.py --dir <wiki_dir> --tier hot --file large.md --title "Large" --status active --content -
```

### 3. `search_wiki.py`
Performs a Hybrid Semantic Search over the Wiki, using Semantic Chunking to prevent Context Bloat. Automatically skips Cold files unless `--include-cold` is provided. Also utilizes **Incremental Sync** to only embed changed files, saving API costs.
Usage: `python path/to/skill/scripts/search_wiki.py --dir <wiki_dir> --query "<search text>" --top <N> --tags "<tag_name>" [--include-cold]`

### 4. `rotate_wiki.py`
Cron-job script. Logically moves file paths from `hot_index` to `warm_index`, and `warm_index` to `cold_index`. It also Flags old cold files for "Rewarm" and Garbage Collects (deletes) deprecated files older than 30 days.
Usage: `python path/to/skill/scripts/rotate_wiki.py --dir <wiki_dir>`

### 5. `check_links.py`
Scans `index.md` and `branches/` for broken Markdown links. Marks broken links with `❌ (DELETED)`.
Usage: `python path/to/skill/scripts/check_links.py --dir <wiki_dir>`

### 6. `export_memory_state.py` & `build_dashboard.py`
Extracts stats from the manifests and raw files, and generates a beautiful HTML Dashboard.
Usage:
```bash
python path/to/skill/scripts/export_memory_state.py --dir <wiki_dir>
python path/to/skill/scripts/build_dashboard.py --dir <wiki_dir>
```

### 7. `rebuild_db.py`
Disaster Recovery script. Purges the Vector DB.
Usage: `python path/to/skill/scripts/rebuild_db.py --dir <wiki_dir>`

### 8. `check_duplication.py`
Semantic Check-before-write. Evaluates if the content you are about to write is already present in the Vector DB to avoid creating redundant Markdown files.
Usage: `python path/to/skill/scripts/check_duplication.py --dir <wiki_dir> --content "Text to check"`

## 🧠 Trigger Words & Context Handling
- **Trigger Words:** "Save to wiki", "Remember this architecture", "Document this", "Save to memory". If the user says these, immediately use this skill.
- **Context Handling:** If `search_wiki.py` returns text that is too large, DO NOT try to read all of it directly if it risks blowing up your context window. Summarize it or read it in chunks.
