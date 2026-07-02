import shutil
from base_test import BaseWikiTest
from check_duplication import check_duplication

class TestDuplication(BaseWikiTest):
    def test_check_duplication_empty_db(self):
        db_path = self.wiki_path / ".chroma_db"
        if db_path.exists(): shutil.rmtree(db_path, ignore_errors=True)
        result = check_duplication(str(self.wiki_path), "Test content")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["duplicates"], [])
