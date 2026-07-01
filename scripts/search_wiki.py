import argparse
import os
import yaml
from pathlib import Path
import subprocess
import re

try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

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

def init_chroma_client(wiki_dir: Path):
    if not HAS_CHROMA:
        print("Error: chromadb is not installed. Please run: pip install -r requirements.txt")
        exit(1)
    db_path = wiki_dir / ".chroma_db"
    client = chromadb.PersistentClient(path=str(db_path))
    return client

try:
    from filelock import FileLock, Timeout
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False
    class FileLock:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    class Timeout(Exception): pass

def get_active_paths(wiki_dir: Path):
    active_paths = set()
    manifests_dir = wiki_dir / "manifests"
    for manifest_name in ["hot_index.md", "warm_index.md"]:
        manifest_path = manifests_dir / manifest_name
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    if line.strip().startswith("- raw/"):
                        rel_path = line.strip()[2:]
                        active_paths.add(rel_path)
    return active_paths

def get_wiki_state(wiki_dir: Path, active_paths: set):
    max_mtime = 0
    file_count = 0
    
    for rel_path in active_paths:
        abs_path = wiki_dir / rel_path
        if abs_path.exists():
            file_count += 1
            mtime = os.path.getmtime(abs_path)
            if mtime > max_mtime:
                max_mtime = mtime
    return max_mtime, file_count

def sync_db(wiki_dir: Path, collection):
    sync_lock_path = wiki_dir / ".chroma_db.lock"
    sync_time_path = wiki_dir / ".last_sync_mtime"
    
    try:
        with FileLock(str(sync_lock_path), timeout=30):
            active_paths = get_active_paths(wiki_dir)
            current_max_mtime, current_file_count = get_wiki_state(wiki_dir, active_paths)
            
            last_sync_mtime = 0
            last_file_count = -1
            if sync_time_path.exists():
                with open(sync_time_path, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read().strip()
                        parts = content.split(',')
                        if len(parts) == 2:
                            last_sync_mtime = float(parts[0])
                            last_file_count = int(parts[1])
                        else:
                            last_sync_mtime = float(parts[0])
                    except ValueError:
                        pass
                        
            if current_max_mtime <= last_sync_mtime and current_file_count == last_file_count and last_sync_mtime != 0:
                print("No new changes detected. Skipping Vector DB sync.")
                return
                
            print("Changes detected. Syncing Wiki to Vector DB with Semantic Chunking...")
            
            docs_to_add = []
            metadatas = []
            ids = []
            
            for rel_path in active_paths:
                item = wiki_dir / rel_path
                if not item.exists(): continue
                    
                frontmatter, content = extract_frontmatter_and_content(item)
                if not frontmatter: continue
                    
                status = frontmatter.get('status', 'active')
                if status in ['deprecated', 'superseded']:
                    continue
                    
                tags = frontmatter.get('tags', [])
                tags_str = ",".join(tags) if isinstance(tags, list) else tags
                
                # Semantic Chunking
                chunks = chunk_markdown(content)
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
                    
            # Zombie Context Removal: delete by checking existing paths
            try:
                existing_data = collection.get()
                if existing_data and 'metadatas' in existing_data and existing_data['metadatas']:
                    existing_ids = existing_data['ids']
                    existing_metas = existing_data['metadatas']
                    
                    ids_to_delete = []
                    for doc_id, meta in zip(existing_ids, existing_metas):
                        path = meta.get("path")
                        if not path or path not in active_paths:
                            ids_to_delete.append(doc_id)
                            
                    if ids_to_delete:
                        collection.delete(ids=ids_to_delete)
                        print(f"Removed {len(ids_to_delete)} zombie chunks from Vector DB.")
            except Exception as e:
                print(f"Warning: Could not perform zombie context cleanup. {e}")
                    
            if ids:
                collection.upsert(
                    documents=docs_to_add,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"Synced {len(ids)} chunks into Vector DB.")
                
                with open(sync_time_path, 'w', encoding='utf-8') as f:
                    f.write(f"{current_max_mtime},{current_file_count}")
            else:
                print("No active files found to sync.")
                
    except Timeout:
        print("Warning: Another Agent is currently syncing the DB. Proceeding to search with current DB state...")

def search_wiki(wiki_dir: str, query: str, top_k: int = 3, tag_filter: str = None):
    wiki_path = Path(wiki_dir).resolve()
    
    sync_lock_path = wiki_path / ".chroma_db.lock"
    
    try:
        with FileLock(str(sync_lock_path), timeout=30):
            client = init_chroma_client(wiki_path)
            emb_fn = embedding_functions.DefaultEmbeddingFunction()
            
            collection = client.get_or_create_collection(
                name="hia_wiki", 
                embedding_function=emb_fn
            )
            
            # Since we are already inside the lock, we can call a modified sync or just rely on sync_db's own lock.
            # FileLock is re-entrant if it's the same thread, but just to be safe:
            pass
    except Timeout:
        print("Warning: Another Agent is currently syncing the DB. Waiting for it to finish...")
        
    # We init client again outside if it failed, but usually we just want it to be safe.
    # Actually, it's better to just do this:
    client = init_chroma_client(wiki_path)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="hia_wiki", 
        embedding_function=emb_fn
    )
    
    sync_db(wiki_path, collection)
    
    print(f"\n--- Searching for: '{query}' ---")
    
    where_clause = None
    if tag_filter:
        where_clause = {"tags": {"$contains": tag_filter}}
        
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )
        
        if not results['documents'] or not results['documents'][0]:
            print("No relevant context found.")
            return
            
        for i in range(len(results['documents'][0])):
            doc_id = results['ids'][0][i]
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i]
            print(f"\n[{i+1}] Source: {doc_id} (Distance: {dist:.4f})")
            print(f"Tags: {meta.get('tags', '')}")
            print("Content Snippet:")
            content = results['documents'][0][i]
            print(content + "\n")
    except Exception as e:
        print(f"Error during search: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metadata-Filtered RAG Search for Hia Wiki.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top", type=int, default=3, help="Number of results to return")
    parser.add_argument("--tags", type=str, help="Filter by specific tag")
    
    args = parser.parse_args()
    search_wiki(args.dir, args.query, args.top, args.tags)
