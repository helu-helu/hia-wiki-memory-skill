import argparse
import json
import yaml
import re
import os
from pathlib import Path
from datetime import datetime

def parse_frontmatter(file_path: Path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            return yaml.safe_load(match.group(1)) or {}
    except:
        pass
    return {}

def export_state(wiki_dir: str):
    wiki_path = Path(wiki_dir).resolve()
    manifests_dir = wiki_path / "manifests"
    
    state = {
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "total_files": 0,
            "hot": 0,
            "warm": 0,
            "cold": 0,
            "review": 0,
            "total_size_kb": 0
        },
        "tiers": {
            "hot": [],
            "warm": [],
            "cold": []
        },
        "needs_review": {}, # Grouped by tag
        "context_inventory": {} # Grouped by tag with file breakdown
    }
    
    # Process Hot, Warm, Cold
    for tier in ["hot", "warm", "cold"]:
        manifest = manifests_dir / f"{tier}_index.md"
        if not manifest.exists(): continue
        
        with open(manifest, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("- raw/"):
                    rel_path = line.strip()[2:]
                    abs_path = wiki_path / rel_path
                    if abs_path.exists():
                        size_kb = round(os.path.getsize(abs_path) / 1024, 2)
                        frontmatter = parse_frontmatter(abs_path)
                        
                        file_data = {
                            "path": rel_path,
                            "title": rel_path.replace('raw/', '').replace('.md', ''),
                            "author": frontmatter.get("author", "unknown"),
                            "status": frontmatter.get("status", "active"),
                            "tags": frontmatter.get("tags", []),
                            "last_updated": frontmatter.get("last_updated", ""),
                            "size_kb": size_kb
                        }
                        
                        state["tiers"][tier].append(file_data)
                        state["stats"][tier] += 1
                        state["stats"]["total_files"] += 1
                        state["stats"]["total_size_kb"] += size_kb
                        
                        for tag in file_data["tags"]:
                            if tag not in state["context_inventory"]:
                                state["context_inventory"][tag] = {
                                    "total": 0,
                                    "hot": 0,
                                    "warm": 0,
                                    "cold": 0,
                                    "files": []
                                }
                            state["context_inventory"][tag]["total"] += 1
                            state["context_inventory"][tag][tier] += 1
                            state["context_inventory"][tag]["files"].append(file_data)
                        
    # Process Review Index
    review_manifest = manifests_dir / "review_index.md"
    if review_manifest.exists():
        with open(review_manifest, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("- raw/"):
                    rel_path = line.strip()[2:]
                    abs_path = wiki_path / rel_path
                    if abs_path.exists():
                        frontmatter = parse_frontmatter(abs_path)
                        if frontmatter.get("needs_review"):
                            state["stats"]["review"] += 1
                            tags = frontmatter.get("tags", [])
                            if not tags: tags = ["untagged"]
                            if isinstance(tags, str): tags = [tags]
                            
                            file_data = {
                                "path": rel_path,
                                "last_updated": frontmatter.get("last_updated", "")
                            }
                            
                            for tag in tags:
                                if tag not in state["needs_review"]:
                                    state["needs_review"][tag] = []
                                state["needs_review"][tag].append(file_data)
                                
    state["stats"]["total_size_kb"] = round(state["stats"]["total_size_kb"], 2)
    
    out_file = wiki_path / "memory_state.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        
    print(f"Memory state exported to {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export memory state to JSON for Dashboard.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    args = parser.parse_args()
    export_state(args.dir)
