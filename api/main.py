import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

import sys
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scripts.search_wiki import search_wiki, sync_db
from scripts.update_wiki import update_or_create_file
from scripts.rotate_wiki import rotate_wiki
from scripts.check_duplication import check_duplication
from scripts.vector_stores import get_vector_store

app = FastAPI(title="Hia Wiki Memory API", description="Cloud-native memory layer for Hia Wiki.")

WIKI_DIR = os.environ.get("WIKI_DIR", "/app/wiki")

class SearchQuery(BaseModel):
    query: str
    top_k: int = 5
    tags: str = ""
    include_cold: bool = False

class UpdateQuery(BaseModel):
    title: str
    content: str
    tier: str = "hot"
    tags: str = ""
    author: str = "agent"

class DuplicateCheck(BaseModel):
    content: str
    threshold: float = 0.5
    top_k: int = 3

@app.get("/health")
def health_check():
    return {"status": "healthy", "wiki_dir": WIKI_DIR}

@app.post("/search")
def search(query: SearchQuery):
    # search_wiki normally prints to stdout, we should adapt it to return data if we want a proper API.
    # For now, we can run sync_db and then use vector_store directly here to return JSON.
    try:
        vector_store = get_vector_store(WIKI_DIR)
        sync_db(Path(WIKI_DIR), vector_store)
        
        where_clause = {}
        if query.tags:
            where_clause["tags"] = {"$contains": query.tags}
        
        if not query.include_cold:
            if where_clause:
                where_clause = {"$and": [where_clause, {"tier": {"$in": ["hot", "warm"]}}]}
            else:
                where_clause = {"tier": {"$in": ["hot", "warm"]}}
                
        docs, distances, metadatas = vector_store.search(
            query=query.query,
            n_results=query.top_k,
            where=where_clause if where_clause else None
        )
        
        results = []
        for i in range(len(docs)):
            results.append({
                "path": metadatas[i].get("path"),
                "tier": metadatas[i].get("tier"),
                "distance": distances[i],
                "content": docs[i].strip()
            })
            
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update")
def update(req: UpdateQuery):
    try:
        # Generate a safe filename from title
        import re
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', req.title).lower()
        filename = f"{safe_title}.md"
        
        result = update_or_create_file(
            wiki_dir=WIKI_DIR,
            tier=req.tier,
            filename=filename,
            title=req.title,
            status="active",
            content=req.content,
            author=req.author,
            tags=req.tags,
            superseded_by=""
        )
        
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rotate")
def rotate(background_tasks: BackgroundTasks):
    # Rotation can be slow, run in background
    background_tasks.add_task(rotate_wiki, WIKI_DIR)
    return {"status": "accepted", "message": "Rotation started in background."}

@app.post("/check_duplication")
def check_dup(req: DuplicateCheck):
    result = check_duplication(WIKI_DIR, req.content, req.threshold, req.top_k)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result
