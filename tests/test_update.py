from base_test import BaseWikiTest
from update_wiki import update_or_create_file

class TestUpdate(BaseWikiTest):
    def test_update_wiki_creates_file_and_updates_manifest(self):
        update_or_create_file(wiki_dir=str(self.wiki_path), tier="hot", filename="new_doc.md", title="New Document", status="active", content="Hello world", author="qa", tags="test", superseded_by="")
        file_path = self.raw_dir / "new_doc.md"
        self.assertTrue(file_path.exists())
        with open(self.manifests_dir / "hot_index.md", 'r') as f:
            hot_content = f.read()
            self.assertIn("- raw/new_doc.md", hot_content)

    def test_update_wiki_json_returns(self):
        result = update_or_create_file(wiki_dir=str(self.wiki_path), tier="hot", filename="invalid..name.md", title="Test", status="active", content="test", author="test", tags="test", superseded_by="")
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid filename", result["message"])
        result = update_or_create_file(wiki_dir=str(self.wiki_path), tier="hot", filename="valid_name.md", title="Test", status="active", content="test", author="test", tags="test", superseded_by="")
        self.assertEqual(result["status"], "success")
        self.assertIn("Successfully wrote", result["message"])
        self.assertIn("valid_name.md", result["file"])
