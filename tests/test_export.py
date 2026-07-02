import json
from base_test import BaseWikiTest
from export_memory_state import export_state

class TestExport(BaseWikiTest):
    def test_memory_state_export(self):
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
