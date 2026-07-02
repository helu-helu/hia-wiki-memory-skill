import argparse
import os
import json
from pathlib import Path
import logging
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stderr)

from vector_stores import get_vector_store

def check_duplication(wiki_dir: str, content: str, threshold: float = 0.5, top_k: int = 3):
    wiki_path = Path(wiki_dir).resolve()
        
    try:
        vector_store = get_vector_store(str(wiki_path))
        
        docs, distances, metadatas = vector_store.search(
            query=content,
            n_results=top_k
        )
        
        duplicates = []
        if docs:
            for i in range(len(docs)):
                doc_id = "N/A" # Pinecone/Chroma returned ID varies, not super critical for the summary
                meta = metadatas[i]
                dist = distances[i]
                
                # Lower distance means more similar (for Chroma). 
                # Note: Pinecone uses cosine similarity (higher is better). 
                # This logic assumes distance-based threshold.
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
        logger.error(f"Error checking duplication: {e}")
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
            logger.error(f"Could not read source_file '{args.source_file}': {e}")
            print(json.dumps({"status": "error", "message": f"Could not read source_file '{args.source_file}': {e}"}))
            exit(1)
            
    if not content:
        logger.error("Either --content or --source_file must be provided.")
        print(json.dumps({"status": "error", "message": "Either --content or --source_file must be provided."}))
        exit(1)
        
    result = check_duplication(args.dir, content, args.threshold, args.top)
    print(json.dumps(result))
    if result.get("status") == "error":
        exit(1)
