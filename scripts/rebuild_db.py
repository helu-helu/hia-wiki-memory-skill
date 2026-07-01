import argparse
import shutil
from pathlib import Path

def rebuild_db(wiki_dir: str):
    wiki_path = Path(wiki_dir).resolve()
    db_path = wiki_path / ".chroma_db"
    lock_path = wiki_path / ".chroma_db.lock"
    sync_time_path = wiki_path / ".last_sync_mtime"
    
    print("Initiating Disaster Recovery for Vector DB...")
    if db_path.exists():
        shutil.rmtree(db_path)
        print(f"Deleted {db_path}")
        
    if lock_path.exists():
        lock_path.unlink()
        
    if sync_time_path.exists():
        sync_time_path.unlink()
        
    print("Database purged. Next time search_wiki.py is run, it will perform a clean, full re-embed from the physical Markdown files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild Vector DB by purging existing DB.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    args = parser.parse_args()
    rebuild_db(args.dir)
