import argparse
import re
import os
from pathlib import Path

def check_and_update_links(wiki_dir: str):
    wiki_path = Path(wiki_dir).resolve()
    print(f"Running Broken Link Checker on {wiki_path}...")
    
    # Files to check: index.md and everything in branches/
    files_to_check = []
    
    index_path = wiki_path / "index.md"
    if index_path.exists():
        files_to_check.append(index_path)
        
    branches_dir = wiki_path / "branches"
    if branches_dir.exists():
        for file in branches_dir.rglob("*.md"):
            files_to_check.append(file)
            
    broken_mark = " ❌ (DELETED)"
    
    # Regex to find markdown links: [Text](link)
    # We want to match the whole line or segment to append the mark outside the link
    # Actually, it's easier to find the link, and check if it's followed by broken_mark
    link_pattern = re.compile(r'(\[.*?\]\((.*?)\))(\s*❌ \(DELETED\))?')
    
    total_broken = 0
    total_fixed = 0
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            def replace_link(match):
                nonlocal total_broken, total_fixed
                full_link = match.group(1) # [text](link)
                link_target = match.group(2) # link
                has_mark = match.group(3) # ❌ (DELETED)
                
                # We only check relative local links that end in .md
                if link_target.startswith('http') or not link_target.endswith('.md'):
                    return match.group(0) # unchanged
                    
                target_abs_path = (file_path.parent / link_target).resolve()
                
                if not target_abs_path.exists():
                    if not has_mark:
                        total_broken += 1
                        return full_link + broken_mark
                else:
                    if has_mark:
                        total_fixed += 1
                        return full_link # Removed the mark
                        
                return match.group(0) # unchanged
                
            new_content = link_pattern.sub(replace_link, content)
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated links in {file_path.relative_to(wiki_path)}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    print(f"Link check complete. Found {total_broken} new broken links. Recovered {total_fixed} restored links.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check and mark broken links in branch maps.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    args = parser.parse_args()
    check_and_update_links(args.dir)
