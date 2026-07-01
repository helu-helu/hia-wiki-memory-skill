import argparse
import os
import yaml
import re
from pathlib import Path
from datetime import datetime
import subprocess
import sys

def try_git_commit(wiki_dir: str, message: str):
    wiki_path = Path(wiki_dir).resolve()
    if (wiki_path / ".git").exists():
        try:
            subprocess.run(["git", "add", "."], cwd=wiki_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message], cwd=wiki_path, check=True, capture_output=True)
            print(f"Git auto-commit: {message}")
        except Exception:
            pass

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

def update_manifest(wiki_path: Path, target_tier: str, relative_path: str):
    tiers = ['hot', 'warm', 'cold', 'review']
    manifests_dir = wiki_path / "manifests"
    
    for t in tiers:
        manifest_path = manifests_dir / f"{t}_index.md"
        if not manifest_path.exists():
            continue
            
        with open(manifest_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        new_lines = []
        found = False
        for line in lines:
            # Check if this exact path is in the line (e.g. "- raw/login.md")
            if line.strip().endswith(relative_path):
                if t == target_tier:
                    found = True
                    new_lines.append(line)
                # Else we skip appending it (removes from wrong tier)
            else:
                new_lines.append(line)
                
        if t == target_tier and not found:
            # Ensure it ends with newline
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            new_lines.append(f"- {relative_path}\n")
            
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)


def update_or_create_file(wiki_dir: str, tier: str, filename: str, title: str, status: str, content: str, author: str, tags: str, superseded_by: str):
    wiki_path = Path(wiki_dir).resolve()
    raw_dir = wiki_path / "raw"
    
    if not raw_dir.exists():
        print(f"Error: {raw_dir} does not exist. Please run init_wiki.py first.")
        return
        
    # SECURITY PATCH: Prevent Path Traversal and Injection
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        print(f"Error: Invalid filename '{filename}'. Only alphanumeric characters, hyphens, underscores, and dots are allowed.")
        return
    if '..' in filename:
        print("Error: Invalid filename. Path traversal detected.")
        return
        
    file_path = raw_dir / filename
    
    # Ensure it doesn't escape raw_dir just in case
    try:
        if not file_path.resolve().is_relative_to(raw_dir.resolve()):
            print("Error: Invalid filename. Path traversal detected.")
            return
    except Exception:
        pass

    lock_path = file_path.with_suffix('.md.lock')
    relative_path = f"raw/{filename}"
    
    try:
        with FileLock(str(lock_path), timeout=15):
            existing_frontmatter = {}
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                match = re.match(r'^---\s*\n(.*?)\n---\s*\n', file_content, re.DOTALL)
                if match:
                    try:
                        existing_frontmatter = yaml.safe_load(match.group(1)) or {}
                    except yaml.YAMLError:
                        pass

            now_str = datetime.now().strftime('%Y-%m-%d')
            
            frontmatter = {
                'date': existing_frontmatter.get('date', now_str),
                'last_updated': now_str,
                'author': author,
                'tier': tier,
                'status': status
            }
            
            if tags:
                tag_list = [t.strip() for t in tags.split(',') if t.strip()]
                # SECURITY PATCH: Strict tag validation
                for t in tag_list:
                    if not re.match(r'^[a-zA-Z0-9_\-]+$', t):
                        print(f"Error: Invalid tag '{t}'. Tags can only contain alphanumeric characters, hyphens, and underscores.")
                        return
                frontmatter['tags'] = tag_list
            elif 'tags' in existing_frontmatter:
                frontmatter['tags'] = existing_frontmatter['tags']
            else:
                print("Error: --tags is required for new files. You must categorize this file into a branch/tag.")
                return
                
            if not frontmatter.get('tags') or 'untagged' in [t.lower() for t in frontmatter['tags']]:
                print("Error: Files must have at least one valid tag. 'untagged' is not allowed. Please assign a proper branch/tag.")
                return

            if status == 'deprecated' and superseded_by:
                frontmatter['superseded_by'] = superseded_by
            elif 'superseded_by' in existing_frontmatter and status == 'deprecated':
                frontmatter['superseded_by'] = existing_frontmatter['superseded_by']

            # Note: We intentionally do not preserve 'needs_review' flag, effectively "rewarming" the file.
            
            yaml_block = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
            final_content = f"---\n{yaml_block}---\n\n# {title}\n\n{content}\n"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
                
            # Update manifest files safely under the same lock
            update_manifest(wiki_path, tier, relative_path)
                
            print(f"Successfully wrote to {file_path} and registered in {tier}_index.md")
            try_git_commit(wiki_dir, f"[Agent] Update {filename}")
            
    except Timeout:
        print(f"Error: Could not acquire lock for {file_path}. Another Agent is currently modifying it.")
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update or create a wiki file safely.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    parser.add_argument("--tier", required=True, choices=["hot", "warm", "cold"], help="Wiki tier")
    parser.add_argument("--file", required=True, help="Filename (e.g. decision_01.md)")
    parser.add_argument("--title", required=True, help="Document title")
    parser.add_argument("--status", required=True, choices=["active", "deprecated", "superseded"], help="Document status")
    parser.add_argument("--content", required=False, help="Markdown content (omit or use '-' to read from stdin)")
    parser.add_argument("--source_file", required=False, help="Path to a temporary markdown file to read content from (Recommended for Agents writing huge files)")
    parser.add_argument("--author", default="agent", help="Author of the change")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--superseded-by", dest="superseded_by", default="", help="Path to new file if deprecated")
    
    args = parser.parse_args()
    
    content = args.content
    if args.source_file:
        try:
            with open(args.source_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error: Could not read source_file '{args.source_file}': {e}")
            sys.exit(1)
    elif not content or content == '-':
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("Error: Either --content, --source_file, or stdin must be provided.")
            sys.exit(1)
            
    update_or_create_file(args.dir, args.tier, args.file, args.title, args.status, content, args.author, args.tags, args.superseded_by)
