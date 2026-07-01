import argparse
import os
from pathlib import Path
from datetime import datetime

def create_directory(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {path}")

def init_wiki(target_dir: str, author: str):
    wiki_path = Path(target_dir).resolve()
    print(f"Initializing Wiki at: {wiki_path}")

    # Create directories
    raw_dir = wiki_path / "raw"
    manifests_dir = wiki_path / "manifests"
    branches_dir = wiki_path / "branches"
    
    create_directory(raw_dir)
    create_directory(manifests_dir)
    create_directory(branches_dir)

    # Initialize Master Map (index.md)
    index_path = wiki_path / "index.md"
    if not index_path.exists():
        template_content = f"""---
date: {datetime.now().strftime('%Y-%m-%d')}
last_updated: {datetime.now().strftime('%Y-%m-%d')}
author: {author}
tier: root
status: active
---

# Hia System — Master Map

## Reading Protocol
1. Read this file FIRST. DO NOT load the full wiki.
2. DO NOT read `manifests/warm_index.md` or `manifests/cold_index.md` directly. Use `search_wiki.py` to find specific features.
3. This file should only link to Branch Maps in `branches/` (e.g. `[Backend](branches/backend_index.md)`). DO NOT link to Leaf nodes.

## System State
- Current Sprint: [Placeholder]
- Blocking Issues: 0

## Branches (Domain Indexes)
- Add your branch links here.
"""
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(template_content)
        print(f"Created Master Map: {index_path}")
    else:
        print(f"Master Map already exists: {index_path}")

    # Initialize Manifest Indexes
    manifests = {
        "hot_index.md": "🔴 Hot Index (Active files)",
        "warm_index.md": "🟡 Warm Index (Reference files)",
        "cold_index.md": "🔵 Cold Index (Archived files, excluded from Vector Search)",
        "review_index.md": "🔍 Review Index (Files flagged for Rewarm)"
    }
    
    for filename, title in manifests.items():
        manifest_path = manifests_dir / filename
        tier_name = filename.split('_')[0]
        if not manifest_path.exists():
            content = f"""---
type: manifest
tier: {tier_name}
last_updated: {datetime.now().strftime('%Y-%m-%d')}
---
# {title}
*Note: This file is auto-managed by python scripts. Do not manually edit paths.*
"""
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Created Manifest: {manifest_path}")
        else:
            print(f"Manifest already exists: {manifest_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the Flat Storage + Manifest Wiki structure.")
    parser.add_argument("--dir", type=str, default="./wiki", help="Target directory for the wiki (default: ./wiki)")
    parser.add_argument("--author", type=str, default="system", help="Author of the initial index file")
    args = parser.parse_args()
    
    init_wiki(args.dir, args.author)
