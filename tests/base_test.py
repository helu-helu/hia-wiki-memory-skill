import unittest
import tempfile
import os
import shutil
from pathlib import Path
import sys

# Add scripts directory to sys.path
current_dir = Path(__file__).parent.resolve()
scripts_dir = current_dir.parent / "scripts"
sys.path.append(str(scripts_dir))

from init_wiki import init_wiki

class BaseWikiTest(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.wiki_path = Path(self.test_dir)
        init_wiki(str(self.wiki_path), "test_author")
        self.raw_dir = self.wiki_path / "raw"
        self.manifests_dir = self.wiki_path / "manifests"
        self.branches_dir = self.wiki_path / "branches"
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
