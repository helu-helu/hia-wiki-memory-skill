from base_test import BaseWikiTest
from pathlib import Path
from concurrency import DistributedLock
from update_wiki import update_or_create_file

class TestConcurrency(BaseWikiTest):
    def test_distributed_lock(self):
        """Kiểm tra cơ chế khóa phân tán fallback (FileLock)."""
        lock_path = self.manifests_dir / "test.lock"
        with DistributedLock(str(lock_path), timeout=5) as lock:
            self.assertTrue(lock_path.exists() or Path(str(lock_path) + ".lock").exists() or lock.lock.is_locked)

    def test_concurrent_writes_same_file(self):
        """Test FileLock prevents simultaneous writes (basic check)"""
        import threading
        def write_task(tier, i):
            update_or_create_file(
                wiki_dir=str(self.wiki_path), tier=tier, filename="concurrent_doc.md",
                title="Concurrent", status="active", content=f"# Concurrent {i}\nTest.",
                author="test", tags="test", superseded_by=""
            )
        threads = []
        for i in range(5):
            t = threading.Thread(target=write_task, args=("hot", i))
            threads.append(t)
            t.start()
        for t in threads: t.join()
        file_path = self.raw_dir / "concurrent_doc.md"
        self.assertTrue(file_path.exists())
