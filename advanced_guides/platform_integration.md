# Enterprise Architecture & Multi-Platform Integration Guide

The Hia Wiki Memory Skill is designed with an Agnostic nature, meaning it does not rely on any specific static Framework. This document will delve into the **Design Philosophy** and how to deploy this Skill across the most popular platforms.

---

## 🏛️ 1. Architecture Philosophy: The "Librarian Agent" Pattern

**Common Newbie Mistake:** Granting all 4 tools of this Wiki to ALL Subagents in the system.
**Consequences:** 
1. **Context Contamination:** When a coding-focused Agent searches for something itself (`search_wiki`), it retrieves thousands of document tokens and crams them into its Context Window. This dilutes focus, making it "overwhelmed" and causing it to generate illogical code.
2. **Overwrite Conflicts:** Agents not specialized in synthesizing text will arbitrarily call `update_wiki`, turning the Wiki repository into "garbage".

**Senior Architect Solution (The Librarian Pattern):**
In a large Multi-Agent system, you **MUST** create a dedicated Subagent with only one single task: Managing the Wiki (called the Memory Agent or Librarian).
- **Authorization:** ONLY the Librarian is allowed to hold the Python files of the Hia Wiki Memory Skill. Other Agents (Coder, QA, etc.) ARE NOT ALLOWED to hold these tools.
- **Workflow:** When the Coder needs information about the Database, the Coder will message the Librarian: *"Summarize the Database structure for me."* The Librarian will use the `search_wiki` tool to scan the system, read, and summarize the information into a short paragraph, then send it back to the Coder. The Coder's brain remains completely clean!
- When the Coder finishes coding, they hand it over to the Librarian: *"Save this new logic into the filing cabinet."* The Librarian will automatically call `update_wiki`, assign YAML labels, and clean up old files.

> **Note on Agent Adaptability:** Any AI Agent receiving this skill must be aware that its role is **dynamic**. Depending on the User's command, the Agent might be configured as a strict Librarian, or it might act as a dual Coder/Librarian. The Agent must always **proactively recognize** when a valuable lesson or architectural decision is made and initiate the storage process.

## 🏢 2. Enterprise Topology: The "Hierarchical Proxy" Model
If your system scales to dozens or hundreds of sub-agents (e.g., the Hia Multi-Agent System), granting permissions or injecting system prompts about the "Librarian" into every single sub-agent will cause massive prompt management overhead and context bloat.

**The Ultimate Solution:**
- **The Worker Layer:** The 100+ SubAgents (Coders, QAs, Analysts) **DO NOT** know the Librarian exists. They have no concept of a Wiki. Their sole focus is completing tasks and reporting back to their manager.
- **The Orchestrator Layer:** The Main Agent (or Manager Agent) acts as the central node. It coordinates the workers and synthesizes their output.
- **The Memory Layer:** The Librarian Agent is attached directly to the Main Agent.
- **The Flow:** 
  1. SubAgent fixes a bug and reports to the Main Agent.
  2. Main Agent synthesizes the solution into a concise summary.
  3. Main Agent messages the Librarian Agent: *"Store this architectural decision."*
  4. Librarian Agent runs `update_wiki.py` to persist the knowledge.

This ensures 100% decoupling. SubAgents remain lightweight, and the Wiki remains clean and highly curated by the Main Agent & Librarian duo.

---

## 🛠️ 3. Practical Integration Guide Across Platforms

### A. Deployment on OpenClaw (Orchestrator & Sub-Agents Model)
OpenClaw supports a very powerful hierarchical architecture.
1. **Initialize Librarian Agent:** Create a Subagent in OpenClaw named `Librarian`. Grant it access to the `hia-wiki-memory-skill/scripts/` directory.
2. **System Prompt for Librarian:**
   ```yaml
   You are the project's Librarian. Your sole task is to remember and look up documents via the ./hia-wiki-memory-skill/ directory.
   - You MUST read SKILL.md.
   - When other Agents ask, use search_wiki.py to find and summarize things for them.
   - When other Agents request storage, use update_wiki.py.
   ```
3. **System Prompt for Coder/QA Agents:**
   ```yaml
   You DO NOT NEED to memorize the project structure yourself. If you need to know rules, structure, or code history, ASK the "Librarian" subagent.
   ```

### B. Deployment on AutoGen / CrewAI (Group Chat / Agency Model)
Similar to OpenClaw, you design a separate Agent acting as a "Memory Node":
1. In CrewAI, create an `Agent(role='Knowledge Manager', tools=[SearchWikiTool, UpdateWikiTool])`.
2. Other Agents (`Software Engineer`, `QA Engineer`) will not have these tools.
3. In a CrewAI `Task`, you require the Coder to hand over design documents to the `Knowledge Manager` before ending the process.
4. AutoGen does the exact same thing with a wrapped `UserProxyAgent` dedicated to executing Python scripts, acting as the memory bridge.

### C. Deployment on Claude Code (Terminal Environment / Single Agent)
Claude Code is a lone Agent running directly in the Terminal. In this case, since there is only 1 Agent, you must grant it direct permissions.
1. Place the `hia-wiki-memory-skill` folder into the project's Root directory.
2. Create a `CLAUDE.md` file in the project Root with the following content:
   ```markdown
   # Project Memory
   We manage Project Knowledge using the "Hia Wiki Memory Skill".
   - **Ultimate Rule:** Whenever I ask you to "take note", "plan", or "read old docs", you MUST NOT guess. You MUST use Bash commands to run the python scripts in the `./hia-wiki-memory-skill/scripts/` directory.
   - The first time you see this line, run the command `cat ./hia-wiki-memory-skill/SKILL.md` to self-learn.
   ```
3. By forcing Claude Code to manage the Wiki itself, Claude will act in 2 roles: both as Coder and Librarian. (With a Single-Agent, Context Contamination is a trade-off required to have long-term memory).

---

## 📝 4. Copy-Paste Prompt Templates for Hia System (Hierarchical Proxy)

If you are using the **Hierarchical Proxy Model** (Strategy 3) for your Enterprise Hia System, copy and paste the following System Prompts into your Agent configurations:

### 1. The Worker Agents (Coders, QA, Analysts)
*Inject this globally into all worker subagents to keep their brains clean.*
```text
You are a specialized SubAgent. Focus 100% on your specific coding/testing task. 
You DO NOT need to manage project memory or documentation.
Whenever you finish a task, solve a bug, or discover something important, you MUST summarize your findings and report them back to the Main Agent. The Main Agent will handle all storage operations.
```

### 2. The Main Agent (Orchestrator/Manager)
*The Main Agent orchestrates the workers and delegates to the Librarian.*
```text
You are the Main Orchestrator Agent. You manage a team of Worker SubAgents and coordinate with a dedicated "Librarian Agent".
1. When a Worker reports a bug fix, architectural decision, or experience, it is YOUR responsibility to synthesize it.
2. After synthesizing, you MUST send a message to the "Librarian Agent" requesting them to store the knowledge into the Wiki. You must specify the Title, Tags, and Content.
3. If you need historical context before assigning tasks to Workers, message the Librarian Agent to search the Wiki for you.
```

### 3. The Librarian Agent
*This Agent MUST be the only one granted access to the `hia-wiki-memory-skill/scripts/` directory.*
```text
You are the Librarian Agent. Your sole responsibility is to manage the Project's Long-Term Wiki.
1. Before doing anything, read the `hia-wiki-memory-skill/SKILL.md` file to understand your tools.
2. When the Main Agent asks you to store something, use the `update_wiki.py` script.
3. When the Main Agent asks you to retrieve something, use the `search_wiki.py` script and summarize the results for them. (Use `--include-cold` if searching for very old features).
4. Proactively remind the Main Agent to run `rotate_wiki.py` after a milestone, and generate the HTML Dashboard if they ask to view the memory state.
Do NOT write code. Do NOT manage tasks. Only manage the Memory files.
```

---
*In summary, if there are 2 or more Agents, always use the Librarian Pattern. It will save your project from Context garbage and massive Token costs.*
