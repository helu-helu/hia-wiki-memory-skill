from base_test import BaseWikiTest
from rotate_wiki import rotate_wiki
from search_wiki import extract_frontmatter_and_content
from datetime import datetime, timedelta

class TestRotate(BaseWikiTest):
    def test_rotate_wiki_capacity_and_age(self):
        young_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        old_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        for i in range(55):
            filename = f"test_doc_{i}.md"
            file_path = self.raw_dir / filename
            test_date = old_date if i < 5 else young_date
            content = f"---\ndate: {test_date}\nlast_updated: {test_date}\nstatus: active\ntier: hot\n---\n# Doc {i}\n"
            with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            with open(self.manifests_dir / "hot_index.md", 'a', encoding='utf-8') as f: f.write(f"- raw/{filename}\n")
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

    def test_rotate_wiki_capacity_exceeded_with_young_files(self):
        young_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        for i in range(55):
            filename = f"young_doc_{i}.md"
            file_path = self.raw_dir / filename
            content = f"---\ndate: {young_date}\nlast_updated: {young_date}\nstatus: active\ntier: hot\n---\n# Doc {i}\n"
            with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            with open(self.manifests_dir / "hot_index.md", 'a', encoding='utf-8') as f: f.write(f"- raw/{filename}\n")
        rotate_wiki(str(self.wiki_path), hot_days=7, warm_days=90, max_hot_files=50)
        with open(self.manifests_dir / "hot_index.md", 'r', encoding='utf-8') as f:
            hot_lines = [l for l in f.readlines() if l.strip().startswith("- raw/")]
            self.assertEqual(len(hot_lines), 50)
        with open(self.manifests_dir / "warm_index.md", 'r', encoding='utf-8') as f:
            warm_lines = [l for l in f.readlines() if l.strip().startswith("- raw/")]
            self.assertEqual(len(warm_lines), 5)

    def test_garbage_collection(self):
        test_date = (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')
        filename = "deprecated_doc.md"
        file_path = self.raw_dir / filename
        content = f"---\ndate: {test_date}\nlast_updated: {test_date}\nstatus: deprecated\ntier: cold\n---\n# Doc\n"
        with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
        with open(self.manifests_dir / "cold_index.md", 'a', encoding='utf-8') as f: f.write(f"- raw/{filename}\n")
        rotate_wiki(str(self.wiki_path), purge_days=30)
        self.assertFalse(file_path.exists())
        with open(self.manifests_dir / "cold_index.md", 'r', encoding='utf-8') as f:
            cold_content = f.read()
            self.assertNotIn("- raw/deprecated_doc.md", cold_content)

    def test_rewarm_flagging(self):
        test_date = (datetime.now() - timedelta(days=70)).strftime('%Y-%m-%d')
        filename = "old_doc.md"
        file_path = self.raw_dir / filename
        content = f"---\ndate: {test_date}\nlast_updated: {test_date}\nstatus: active\ntier: cold\n---\n# Doc\n"
        with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
        with open(self.manifests_dir / "cold_index.md", 'a', encoding='utf-8') as f: f.write(f"- raw/{filename}\n")
        rotate_wiki(str(self.wiki_path), review_days=60)
        frontmatter, _ = extract_frontmatter_and_content(file_path)
        self.assertTrue(frontmatter.get('needs_review'))
        with open(self.manifests_dir / "review_index.md", 'r', encoding='utf-8') as f:
            review_content = f.read()
            self.assertIn("- raw/old_doc.md", review_content)
