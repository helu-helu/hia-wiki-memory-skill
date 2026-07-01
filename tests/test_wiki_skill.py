import unittest
import tempfile
import os
import shutil
from pathlib import Path
import sys

# Add scripts directory to sys.path so we can import them
current_dir = Path(__file__).parent.resolve()
scripts_dir = current_dir.parent / "scripts"
sys.path.append(str(scripts_dir))

from search_wiki import extract_frontmatter_and_content, get_active_paths, chunk_markdown
from rotate_wiki import rotate_wiki, parse_frontmatter_date
from update_wiki import update_or_create_file, update_manifest
from init_wiki import init_wiki
from check_links import check_and_update_links
from export_memory_state import export_state
import json

class TestWikiSkill(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.wiki_path = Path(self.test_dir)
        init_wiki(str(self.wiki_path), "test_author")
        self.raw_dir = self.wiki_path / "raw"
        self.manifests_dir = self.wiki_path / "manifests"
        self.branches_dir = self.wiki_path / "branches"
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_init_wiki_structure(self):
        """Kiểm tra cấu trúc Flat Storage + Manifests được khởi tạo đúng."""
        self.assertTrue(self.raw_dir.exists())
        self.assertTrue(self.manifests_dir.exists())
        self.assertTrue(self.branches_dir.exists())
        self.assertTrue((self.wiki_path / "index.md").exists())
        self.assertTrue((self.manifests_dir / "hot_index.md").exists())
        self.assertTrue((self.manifests_dir / "warm_index.md").exists())
        self.assertTrue((self.manifests_dir / "cold_index.md").exists())
        self.assertTrue((self.manifests_dir / "review_index.md").exists())

    def test_update_wiki_creates_file_and_updates_manifest(self):
        """Test ghi file vào raw/ và ghi đè Manifest chính xác."""
        update_or_create_file(
            wiki_dir=str(self.wiki_path),
            tier="hot",
            filename="new_doc.md",
            title="New Document",
            status="active",
            content="Hello world",
            author="qa",
            tags="test",
            superseded_by=""
        )
        
        file_path = self.raw_dir / "new_doc.md"
        self.assertTrue(file_path.exists())
        
        with open(self.manifests_dir / "hot_index.md", 'r') as f:
            hot_content = f.read()
            self.assertIn("- raw/new_doc.md", hot_content)

    def test_rotate_wiki_capacity_and_age(self):
        """Test tính năng Rotate logic: Di chuyển từ hot_index -> warm_index và sửa YAML tag."""
        from datetime import datetime, timedelta
        test_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        for i in range(55):
            filename = f"test_doc_{i}.md"
            file_path = self.raw_dir / filename
            content = f"---\ndate: {test_date}\nlast_updated: {test_date}\nstatus: active\ntier: hot\n---\n# Doc {i}\n"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            with open(self.manifests_dir / "hot_index.md", 'a', encoding='utf-8') as f:
                f.write(f"- raw/{filename}\n")
                
        rotate_wiki(str(self.wiki_path), hot_days=7, warm_days=90, max_hot_files=50)
        
        with open(self.manifests_dir / "hot_index.md", 'r', encoding='utf-8') as f:
            hot_lines = [l for l in f.readlines() if l.strip().startswith("- raw/")]
            self.assertEqual(len(hot_lines), 50)
            
        with open(self.manifests_dir / "warm_index.md", 'r', encoding='utf-8') as f:
            warm_lines = [l for l in f.readlines() if l.strip().startswith("- raw/")]
            self.assertEqual(len(warm_lines), 5)
            
        rotated_file = warm_lines[0].strip()[2:]
        frontmatter, _ = extract_frontmatter_and_content(self.wiki_path / rotated_file)
        self.assertEqual(frontmatter.get('tier'), 'warm')

    def test_garbage_collection(self):
        """Test cơ chế dọn rác đối với file status: deprecated."""
        from datetime import datetime, timedelta
        test_date = (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')
        
        # Create a deprecated file
        filename = "deprecated_doc.md"
        file_path = self.raw_dir / filename
        content = f"---\ndate: {test_date}\nlast_updated: {test_date}\nstatus: deprecated\ntier: cold\n---\n# Doc\n"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        with open(self.manifests_dir / "cold_index.md", 'a', encoding='utf-8') as f:
            f.write(f"- raw/{filename}\n")
            
        # Rotate with purge_days = 30
        rotate_wiki(str(self.wiki_path), purge_days=30)
        
        # File should be physically deleted
        self.assertFalse(file_path.exists())
        
        # And removed from manifest
        with open(self.manifests_dir / "cold_index.md", 'r', encoding='utf-8') as f:
            cold_content = f.read()
            self.assertNotIn("- raw/deprecated_doc.md", cold_content)

    def test_rewarm_flagging(self):
        """Test cơ chế Hâm Nóng (Rewarm) tự động gán needs_review."""
        from datetime import datetime, timedelta
        test_date = (datetime.now() - timedelta(days=70)).strftime('%Y-%m-%d')
        
        filename = "old_doc.md"
        file_path = self.raw_dir / filename
        content = f"---\ndate: {test_date}\nlast_updated: {test_date}\nstatus: active\ntier: cold\n---\n# Doc\n"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        with open(self.manifests_dir / "cold_index.md", 'a', encoding='utf-8') as f:
            f.write(f"- raw/{filename}\n")
            
        # Rotate with review_days = 60
        rotate_wiki(str(self.wiki_path), review_days=60)
        
        # File should now have needs_review = True
        frontmatter, _ = extract_frontmatter_and_content(file_path)
        self.assertTrue(frontmatter.get('needs_review'))
        
        # And should be in review_index
        with open(self.manifests_dir / "review_index.md", 'r', encoding='utf-8') as f:
            review_content = f.read()
            self.assertIn("- raw/old_doc.md", review_content)

    def test_broken_link_checker(self):
        """Test tính năng phát hiện link hỏng."""
        # Create a branch map with a broken link and a valid link
        branch_path = self.branches_dir / "auth_index.md"
        with open(branch_path, 'w', encoding='utf-8') as f:
            f.write("Valid link: [valid](../raw/valid.md)\n")
            f.write("Broken link: [broken](../raw/broken.md)\n")
            
        # Create the valid file
        with open(self.raw_dir / "valid.md", 'w', encoding='utf-8') as f:
            f.write("Hello")
            
        check_and_update_links(str(self.wiki_path))
        
        with open(branch_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn("[broken](../raw/broken.md) ❌ (DELETED)", content)
        self.assertIn("[valid](../raw/valid.md)", content)
        self.assertNotIn("[valid](../raw/valid.md) ❌ (DELETED)", content)
        
    def test_memory_state_export(self):
        """Test xuất ra memory_state.json cho Module Dashboard."""
        with open(self.raw_dir / "test.md", 'w', encoding='utf-8') as f:
            f.write("---\ntier: hot\ntags: [auth]\nstatus: active\n---\n# Test")
            
        with open(self.manifests_dir / "hot_index.md", 'a', encoding='utf-8') as f:
            f.write("- raw/test.md\n")
            
        export_state(str(self.wiki_path))
        state_file = self.wiki_path / "memory_state.json"
        
        self.assertTrue(state_file.exists())
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(data["stats"]["hot"], 1)

if __name__ == '__main__':
    unittest.main()
