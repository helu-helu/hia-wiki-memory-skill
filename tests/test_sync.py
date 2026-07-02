import json
from base_test import BaseWikiTest
from search_wiki import sync_db
from vector_stores import get_vector_store
from update_wiki import update_or_create_file

class TestSync(BaseWikiTest):
    def test_incremental_sync(self):
        """Kiểm tra cơ chế đồng bộ tăng dần (Incremental Sync)."""
        update_or_create_file(str(self.wiki_path), "hot", "test_doc.md", "Test Doc", "active", "Test Content", "tester", "test", "")
        vector_store = get_vector_store(str(self.wiki_path))
        sync_db(self.wiki_path, vector_store)
        sync_state_path = self.manifests_dir / ".sync_state.json"
        self.assertTrue(sync_state_path.exists())
        with open(sync_state_path, 'r') as f:
            state = json.load(f)
            test_path = None
            for p in state:
                if "test_doc.md" in p:
                    test_path = p
                    break
            self.assertIsNotNone(test_path)
            self.assertIn("hash", state[test_path])
            self.assertIn("chunk_count", state[test_path])
        self.assertTrue((self.manifests_dir / "warm_index.md").exists())
        self.assertTrue((self.manifests_dir / "cold_index.md").exists())
        self.assertTrue((self.manifests_dir / "review_index.md").exists())
