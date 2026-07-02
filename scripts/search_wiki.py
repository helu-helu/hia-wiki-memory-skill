import argparse
import os
import yaml
from pathlib import Path
import subprocess
import re
import hashlib

import json
from vector_stores import get_vector_store
from concurrency import DistributedLock, Timeout

def extract_frontmatter_and_content(file_path: Path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
        if match:
            yaml_str = match.group(1)
            body = match.group(2).strip()
            frontmatter = yaml.safe_load(yaml_str) or {}
            return frontmatter, body
        else:
            return None, content.strip()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None, ""

def chunk_markdown(content: str):
    chunks = []
    current_chunk = []
    for line in content.split('\n'):
        if line.startswith('# ') or line.startswith('## '):
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    final_chunks = []
    prev_tail = []
    for c in chunks:
        lines = c.split('\n')
        final_c = '\n'.join(prev_tail + lines) if prev_tail else c
        final_chunks.append(final_c)
        # Chunk overlap: keep last 3 lines for context continuity
        prev_tail = lines[-3:] if len(lines) >= 3 else lines
        
    return [c for c in final_chunks if c.strip()]

def get_all_indexed_paths(wiki_dir: Path):
    active_paths = set()
    manifests_dir = wiki_dir / "manifests"
    for manifest_name in ["hot_index.md", "warm_index.md", "cold_index.md"]:
        manifest_path = manifests_dir / manifest_name
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    if line.strip().startswith("- raw/"):
                        rel_path = line.strip()[2:]
                        active_paths.add(rel_path)
    return active_paths

def compute_file_hash(content: str):
    hash_obj = hashlib.sha256()
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()

def sync_db(wiki_dir: Path, vector_store):
    sync_lock_path = wiki_dir / "manifests" / ".sync_db.lock"
    sync_state_path = wiki_dir / "manifests" / ".sync_state.json"
    
    try:
        with DistributedLock(str(sync_lock_path), timeout=30):
            active_paths = get_all_indexed_paths(wiki_dir)
            
            sync_state = {}
            if sync_state_path.exists():
                with open(sync_state_path, 'r', encoding='utf-8') as f:
                    try:
                        sync_state = json.load(f)
                    except json.JSONDecodeError:
                        pass
                        
            print("Running Incremental Sync to Vector DB...")
            
            docs_to_add = []
            metadatas = []
            ids = []
            
            new_sync_state = {}
            ids_to_delete = []
            
            for rel_path in active_paths:
                item = wiki_dir / rel_path
                if not item.exists(): continue
                    
                frontmatter, content = extract_frontmatter_and_content(item)
                if not frontmatter: continue
                    
                status = frontmatter.get('status', 'active')
                if status in ['deprecated', 'superseded']:
                    continue
                    
                file_hash = compute_file_hash(content)
                
                # Incremental check
                if rel_path in sync_state and sync_state[rel_path].get("hash") == file_hash:
                    new_sync_state[rel_path] = sync_state[rel_path]
                    continue
                    
                tags = frontmatter.get('tags', [])
                tags_str = ",".join(tags) if isinstance(tags, list) else tags
                
                chunks = chunk_markdown(content)
                
                # Track how many chunks were in the previous version so we can delete excess chunks
                old_chunk_count = sync_state.get(rel_path, {}).get("chunk_count", 0)
                if old_chunk_count > len(chunks):
                    for i in range(len(chunks), old_chunk_count):
                        ids_to_delete.append(f"{rel_path}#chunk{i}")
                
                new_sync_state[rel_path] = {"hash": file_hash, "chunk_count": len(chunks)}
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"{rel_path}#chunk{i}"
                    meta = {
                        "tier": frontmatter.get('tier', 'warm'),
                        "author": frontmatter.get('author', 'unknown'),
                        "path": rel_path,
                        "chunk_index": i
                    }
                    if tags_str:
                        meta["tags"] = tags_str
                        
                    docs_to_add.append(chunk)
                    metadatas.append(meta)
                    ids.append(doc_id)
            
            # Find deleted/deprecated files that are in sync_state but not in active_paths
            for rel_path, state in sync_state.items():
                if rel_path not in new_sync_state:
                    for i in range(state.get("chunk_count", 0)):
                        ids_to_delete.append(f"{rel_path}#chunk{i}")
                        
            # Clean up zombie context
            if ids_to_delete:
                batch_size = 1000
                for i in range(0, len(ids_to_delete), batch_size):
                    vector_store.delete_batch(ids_to_delete[i:i+batch_size])
                print(f"Removed {len(ids_to_delete)} zombie chunks from Vector DB.")
                    
            if ids:
                batch_size = 1000
                for i in range(0, len(ids), batch_size):
                    vector_store.upsert_batch(
                        ids=ids[i:i+batch_size],
                        documents=docs_to_add[i:i+batch_size],
                        metadatas=metadatas[i:i+batch_size]
                    )
                print(f"Synced {len(ids)} new/updated chunks into Vector DB.")
            else:
                print("No files needed syncing (up to date).")
                
            with open(sync_state_path, 'w', encoding='utf-8') as f:
                json.dump(new_sync_state, f, indent=2)
                
    except Timeout:
        print("Warning: Could not acquire sync lock. DB sync is likely already running.")

def search_wiki(wiki_dir: str, query: str, top: int = 5, tags: str = "", include_cold: bool = False):
    wiki_path = Path(wiki_dir).resolve()
    
    vector_store = get_vector_store(str(wiki_path))
    
    sync_db(wiki_path, vector_store)
    
    if query:
        where_clause = {}
        if tags:
            where_clause["tags"] = {"$contains": tags}
        
        if not include_cold:
            if where_clause:
                where_clause = {"$and": [where_clause, {"tier": {"$in": ["hot", "warm"]}}]}
            else:
                where_clause = {"tier": {"$in": ["hot", "warm"]}}
                
        docs, distances, metadatas = vector_store.search(
            query=query,
            n_results=top,
            where=where_clause if where_clause else None
        )
        
        if docs:
            print("\n--- SEARCH RESULTS ---")
            for idx, doc in enumerate(docs):
                meta = metadatas[idx]
                distance = distances[idx]
                print(f"\n[Result {idx+1}] File: {meta.get('path')} (Tier: {meta.get('tier')}, Distance: {distance:.4f})")
                print("-" * 40)
                print(doc.strip())
                print("-" * 40)
        else:
            print("\nNo matching knowledge found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metadata-Filtered RAG Search for Hia Wiki.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top", type=int, default=3, help="Number of results to return")
    parser.add_argument("--tags", type=str, help="Filter by specific tag")
    parser.add_argument("--include-cold", action="store_true", help="Include cold tier files in search")
    
    args = parser.parse_args()
    search_wiki(args.dir, args.query, args.top, args.tags, args.include_cold)
