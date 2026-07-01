import argparse
import os
import json
from pathlib import Path

try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

def check_duplication(wiki_dir: str, content: str, threshold: float = 0.5, top_k: int = 3):
    wiki_path = Path(wiki_dir).resolve()
    
    if not HAS_CHROMA:
        return {"status": "error", "message": "chromadb is not installed. Please run: pip install -r requirements.txt"}
        
    db_path = wiki_path / ".chroma_db"
    if not db_path.exists():
        return {"status": "error", "message": "Vector DB does not exist. Please ensure files are added and search_wiki.py or rotate_wiki.py is run."}
        
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # We don't want to create it if it doesn't exist to avoid empty checks, but get_collection throws if it doesn't.
        # Actually get_or_create is safer.
        collection = client.get_or_create_collection(
            name="hia_wiki", 
            embedding_function=emb_fn
        )
        
        results = collection.query(
            query_texts=[content],
            n_results=top_k
        )
        
        duplicates = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                doc_id = results['ids'][0][i]
                meta = results['metadatas'][0][i]
                dist = results['distances'][0][i]
                
                # Lower distance means more similar
                if dist < threshold:
                    duplicates.append({
                        "id": doc_id,
                        "distance": dist,
                        "path": meta.get("path", ""),
                        "tier": meta.get("tier", ""),
                        "tags": meta.get("tags", "")
                    })
                    
        return {"status": "success", "duplicates": duplicates}
    except Exception as e:
        return {"status": "error", "message": f"Error checking duplication: {e}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for semantic duplication in Hia Wiki.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    parser.add_argument("--content", required=False, help="Text content to check against existing wiki")
    parser.add_argument("--source_file", required=False, help="Path to a temporary text file to read content from")
    parser.add_argument("--threshold", type=float, default=0.5, help="Distance threshold (lower is more similar, default 0.5)")
    parser.add_argument("--top", type=int, default=3, help="Number of top matches to check")
    
    args = parser.parse_args()
    
    content = args.content
    if args.source_file:
        try:
            with open(args.source_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(json.dumps({"status": "error", "message": f"Could not read source_file '{args.source_file}': {e}"}))
            exit(1)
            
    if not content:
        print(json.dumps({"status": "error", "message": "Either --content or --source_file must be provided."}))
        exit(1)
        
    result = check_duplication(args.dir, content, args.threshold, args.top)
    print(json.dumps(result))
    if result.get("status") == "error":
        exit(1)
