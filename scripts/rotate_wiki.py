import argparse
import os
import yaml
import re
from pathlib import Path
from datetime import datetime
import subprocess
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

CONFIG = {
    'HOT_DAYS': 7,
    'WARM_DAYS': 90,
    'PURGE_DAYS': 30,
    'REVIEW_DAYS': 60
}

from concurrency import DistributedLock, Timeout

def try_git_commit(wiki_dir: str, message: str):
    wiki_path = Path(wiki_dir).resolve()
    if (wiki_path / ".git").exists():
        try:
            subprocess.run(["git", "add", "."], cwd=wiki_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message], cwd=wiki_path, check=True, capture_output=True)
            logger.info(f"Git auto-commit: {message}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected git error: {e}")

def parse_frontmatter(file_path: Path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            yaml_str = match.group(1)
            frontmatter = yaml.safe_load(yaml_str) or {}
            return frontmatter
    except Exception as e:
        logger.warning(f"Error parsing frontmatter in {file_path}: {e}")
    return None

def parse_frontmatter_date(file_path: Path, frontmatter: dict = None):
    if frontmatter is None:
        frontmatter = parse_frontmatter(file_path)
    
    if frontmatter:
        date_str = frontmatter.get('last_updated') or frontmatter.get('date')
        if date_str:
            try:
                return datetime.strptime(str(date_str), '%Y-%m-%d')
            except ValueError:
                pass
    return None

def update_file_yaml(file_path: Path, updates: dict):
    try:
        lock_path = file_path.with_suffix('.md.lock')
        with DistributedLock(str(lock_path), timeout=15):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
            if match:
                frontmatter = yaml.safe_load(match.group(1)) or {}
                frontmatter.update(updates)
                yaml_block = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
                final_content = f"---\n{yaml_block}---\n{match.group(2)}"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
    except Exception as e:
        logger.error(f"Failed to update YAML in {file_path}: {e}")

def get_manifest_lines(manifest_path: Path):
    if not manifest_path.exists(): return []
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return f.readlines()

def save_manifest_lines(manifest_path: Path, lines: list):
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def process_rotation(wiki_path: Path, source_tier: str, dest_tier: str, age_limit: int, max_files: int = None):
    manifests_dir = wiki_path / "manifests"
    source_manifest = manifests_dir / f"{source_tier}_index.md"
    dest_manifest = manifests_dir / f"{dest_tier}_index.md"
    
    if not source_manifest.exists(): return
    
    lines = get_manifest_lines(source_manifest)
    
    files = []
    other_lines = []
    
    for line in lines:
        if line.strip().startswith("- raw/"):
            relative_path = line.strip()[2:]
            absolute_path = wiki_path / relative_path
            if absolute_path.exists():
                file_date = parse_frontmatter_date(absolute_path)
                if file_date:
                    age_days = (datetime.now() - file_date).days
                    files.append({
                        "line": line,
                        "rel_path": relative_path,
                        "abs_path": absolute_path,
                        "age_days": age_days
                    })
                else:
                    files.append({"line": line, "rel_path": relative_path, "abs_path": absolute_path, "age_days": 0})
            else:
                pass # skip missing files
        else:
            other_lines.append(line)
            
    files_to_move = []
    files_to_keep = []
    
    if max_files is None:
        for file_info in files:
            if file_info["age_days"] > age_limit:
                files_to_move.append(file_info)
            else:
                files_to_keep.append(file_info)
    else:
        old_files = [f for f in files if f["age_days"] > age_limit]
        new_files = [f for f in files if f["age_days"] <= age_limit]
        
        if len(new_files) >= max_files:
            files_to_move = old_files + new_files[max_files:]
            files_to_keep = new_files[:max_files]
        else:
            files_to_move = old_files
            files_to_keep = new_files
        
    if files_to_move:
        new_source_lines = other_lines + [f["line"] for f in files_to_keep]
        save_manifest_lines(source_manifest, new_source_lines)
        
        dest_lines = get_manifest_lines(dest_manifest)
        if dest_lines and not dest_lines[-1].endswith('\n'):
            dest_lines[-1] += '\n'
        dest_lines.extend([f"- {f['rel_path']}\n" for f in files_to_move])
        save_manifest_lines(dest_manifest, dest_lines)
        
        for f in files_to_move:
            print(f"Moving {f['rel_path']} from {source_tier} to {dest_tier} (Age: {f['age_days']} days)")
            update_file_yaml(f['abs_path'], {'tier': dest_tier})

def process_garbage_collection(wiki_path: Path, purge_days: int):
    print("Running Garbage Collection...")
    manifests_dir = wiki_path / "manifests"
    tiers = ['hot', 'warm', 'cold']
    for t in tiers:
        manifest = manifests_dir / f"{t}_index.md"
        if not manifest.exists(): continue
        lines = get_manifest_lines(manifest)
        new_lines = []
        modified = False
        
        for line in lines:
            if line.strip().startswith("- raw/"):
                relative_path = line.strip()[2:]
                absolute_path = wiki_path / relative_path
                if absolute_path.exists():
                    frontmatter = parse_frontmatter(absolute_path)
                    if frontmatter and frontmatter.get('status') == 'deprecated':
                        file_date = parse_frontmatter_date(absolute_path, frontmatter)
                        if file_date and (datetime.now() - file_date).days > purge_days:
                            print(f"[GC] Deleting {relative_path} (deprecated for > {purge_days} days)")
                            os.remove(absolute_path)
                            modified = True
                            continue # Do not add to new_lines
                # If file doesn't exist, we can also remove the line
                elif not absolute_path.exists():
                    modified = True
                    continue
            new_lines.append(line)
            
        if modified:
            save_manifest_lines(manifest, new_lines)

def process_rewarm(wiki_path: Path, review_days: int):
    print("Running Rewarm Flagging...")
    manifests_dir = wiki_path / "manifests"
    cold_manifest = manifests_dir / "cold_index.md"
    review_manifest = manifests_dir / "review_index.md"
    
    if not cold_manifest.exists(): return
    if not review_manifest.exists(): return
    
    lines = get_manifest_lines(cold_manifest)
    review_lines = get_manifest_lines(review_manifest)
    review_paths = set(line.strip()[2:] for line in review_lines if line.strip().startswith("- raw/"))
    
    new_reviews = []
    
    for line in lines:
        if line.strip().startswith("- raw/"):
            relative_path = line.strip()[2:]
            absolute_path = wiki_path / relative_path
            if absolute_path.exists():
                frontmatter = parse_frontmatter(absolute_path)
                if frontmatter and frontmatter.get('status') != 'deprecated':
                    file_date = parse_frontmatter_date(absolute_path, frontmatter)
                    if file_date and (datetime.now() - file_date).days > review_days:
                        # Add needs_review tag if not present
                        if not frontmatter.get('needs_review'):
                            print(f"[Rewarm] Flagging {relative_path} for review (Age > {review_days} days)")
                            update_file_yaml(absolute_path, {'needs_review': True})
                        
                        if relative_path not in review_paths:
                            new_reviews.append(f"- {relative_path}\n")
                            review_paths.add(relative_path)
                            
    # Also clean up review_index if files were warmed up and flag removed
    cleaned_review_lines = []
    modified_review = False
    for line in review_lines:
        if line.strip().startswith("- raw/"):
            relative_path = line.strip()[2:]
            absolute_path = wiki_path / relative_path
            if absolute_path.exists():
                frontmatter = parse_frontmatter(absolute_path)
                if not frontmatter or not frontmatter.get('needs_review'):
                    # File has been warmed up or flag removed manually
                    print(f"[Rewarm] {relative_path} was warmed up. Removing from review index.")
                    modified_review = True
                    continue
            else:
                modified_review = True # File missing
                continue
        cleaned_review_lines.append(line)
        
    if new_reviews:
        if cleaned_review_lines and not cleaned_review_lines[-1].endswith('\n'):
            cleaned_review_lines[-1] += '\n'
        cleaned_review_lines.extend(new_reviews)
        modified_review = True
        
    if modified_review:
        save_manifest_lines(review_manifest, cleaned_review_lines)

def rotate_wiki(wiki_dir: str, hot_days: int = CONFIG['HOT_DAYS'], warm_days: int = CONFIG['WARM_DAYS'], max_hot_files: int = 50, purge_days: int = CONFIG['PURGE_DAYS'], review_days: int = CONFIG['REVIEW_DAYS']):
    wiki_path = Path(wiki_dir).resolve()
    print(f"Running Manifest rotation script for {wiki_path}")
    
    lock_path = wiki_path / "manifests" / "rotate.lock"
    try:
        with DistributedLock(str(lock_path), timeout=10):
            # Process HOT to WARM
            process_rotation(wiki_path, "hot", "warm", hot_days, max_hot_files)
            
            # Process WARM to COLD
            process_rotation(wiki_path, "warm", "cold", warm_days, max_files=None)

            # Process Garbage Collection
            process_garbage_collection(wiki_path, purge_days)
            
            # Process Rewarm Flagging
            process_rewarm(wiki_path, review_days)

            print("Rotation complete.")
            try_git_commit(wiki_dir, "[Agent] Auto-rotate manifest files, GC and Rewarm")
    except Timeout:
        print(f"Warning: Could not acquire lock for rotation. Another rotation is likely running.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate wiki files logically using Manifest indexes.")
    parser.add_argument("--dir", required=True, help="Base wiki directory")
    parser.add_argument("--hot-days", type=int, default=7, help="Days before hot moves to warm")
    parser.add_argument("--warm-days", type=int, default=90, help="Days before warm moves to cold")
    parser.add_argument("--max-hot-files", type=int, default=50, help="Maximum files allowed in hot before rotation triggers")
    parser.add_argument("--purge-days", type=int, default=30, help="Days before deprecated files are permanently deleted")
    parser.add_argument("--review-days", type=int, default=60, help="Days before cold files are flagged for rewarm review")
    
    args = parser.parse_args()
    rotate_wiki(args.dir, args.hot_days, args.warm_days, args.max_hot_files, args.purge_days, args.review_days)
