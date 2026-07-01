# Upgrade Guide: Cloud Server Migration (API-First Microservice)

*This document is specifically for Enterprises or Users who want to move the Wiki system from a personal computer (Local) to a shared Cloud Server.*

You **DO NOT NEED** to do this immediately. Simply provide this document to your AI Agent when needed, and the Agent will read it and set everything up automatically.

---

## 1. Why Move to the Cloud?

By default, the `hia-wiki-memory-skill` system runs on your local computer, using the File System to store Markdown files and ChromaDB for Vectors. 
However, as your scale expands to:
- A team of 10 employees (Humans) running 10 AI Agents on 10 different computers.
- You want all the AI across the entire company to share a single "Wiki Brain."

The solution is to transform the current Python scripts into an **API-driven Microservice**.

---

## 2. API-First Architecture (For AI Agent Execution)

If you request the AI to upgrade, provide it with the following architectural requirements:

### A. Wrapping with FastAPI
The Agent needs to create a `server.py` file using the `FastAPI` library. Instead of running the terminal command `python update_wiki.py`, client AIs will call APIs over the Internet:
- `POST /api/wiki/update`: Send Markdown content to the server. The server will run the function inside `update_wiki.py` to write the file.
- `GET /api/wiki/search?q="..."`: Send a search query, the server calls `search_wiki.py` and returns JSON.
- `POST /api/wiki/rotate`: Trigger the garbage collection job.

### B. Resolving Concurrency with Distributed Locks (Redis)
When moving to the Cloud, the `filelock` library (which only locks files on a single machine) is not robust enough if the server runs multiple nodes (Load Balancing).
Your Agent will need to install **Redis** and use `redis-lock` to ensure that: When Employee A's AI is writing the "Database Design" document, Employee B's AI is forced to wait or receives an `HTTP 409 Conflict` error code.

### C. Centralized Interface (Headless CMS)
The `.md` file system on the server can then connect to premium systems like Notion or Confluence via their APIs. At this point, the entire Company can log into Notion to read internal documents, while in the background, AI Agents quietly call APIs to read and write documents.

---

## 3. Prompt to Request AI Auto-Upgrade

When you are ready, copy the following Prompt and send it to your Coder Agent:

> *"Hi AI, I want to upgrade the architecture of `hia-wiki-memory-skill` to an API Server. Please use FastAPI to wrap the scripts (update_wiki, search_wiki, rotate_wiki, check_links, export_memory_state) into RESTful API endpoints. 
> Ensure you add Swagger UI so I can test it. Write the code into the `api_server.py` file and update `requirements.txt` with the fastapi and uvicorn libraries."*
