from base_test import BaseWikiTest
from update_wiki import update_or_create_file

class TestSearch(BaseWikiTest):
    def test_search_wiki_basic(self):
        try:
            import chromadb
        except ImportError:
            self.skipTest("chromadb not installed")
        update_or_create_file(wiki_dir=str(self.wiki_path), tier="hot", filename="auth_doc.md", title="Authentication", status="active", content="# Auth\nThis document explains user authentication.", author="test", tags="auth", superseded_by="")
        update_or_create_file(wiki_dir=str(self.wiki_path), tier="hot", filename="db_doc.md", title="Database", status="active", content="# Database\nThis document explains database connections.", author="test", tags="db", superseded_by="")
        
        from search_wiki import search_wiki
        import io, sys
        captured_output = io.StringIO()
        sys.stdout = captured_output
        search_wiki(str(self.wiki_path), "authentication")
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        self.assertIn("auth_doc.md", output)
