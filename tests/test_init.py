from base_test import BaseWikiTest

class TestInitWiki(BaseWikiTest):
    def test_init_wiki_structure(self):
        """Kiểm tra cấu trúc Flat Storage + Manifests được khởi tạo đúng."""
        self.assertTrue(self.raw_dir.exists())
        self.assertTrue(self.manifests_dir.exists())
        self.assertTrue(self.branches_dir.exists())
        self.assertTrue((self.wiki_path / "index.md").exists())
        self.assertTrue((self.manifests_dir / "hot_index.md").exists())
