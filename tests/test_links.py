from base_test import BaseWikiTest
from check_links import check_and_update_links

class TestLinks(BaseWikiTest):
    def test_broken_link_checker(self):
        branch_path = self.branches_dir / "auth_index.md"
        with open(branch_path, 'w', encoding='utf-8') as f:
            f.write("Valid link: [valid](../raw/valid.md)\n")
            f.write("Broken link: [broken](../raw/broken.md)\n")
        with open(self.raw_dir / "valid.md", 'w', encoding='utf-8') as f:
            f.write("Hello")
        check_and_update_links(str(self.wiki_path))
        with open(branch_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("[broken](../raw/broken.md) ❌ (DELETED)", content)
        self.assertIn("[valid](../raw/valid.md)", content)
        self.assertNotIn("[valid](../raw/valid.md) ❌ (DELETED)", content)
