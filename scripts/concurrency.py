import os
import time
from dotenv import load_dotenv

load_dotenv()

# Try to import filelock
try:
    from filelock import FileLock, Timeout as FileLockTimeout
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False
    class FileLock:
        def __init__(self, *args, **kwargs): pass
        def acquire(self): return True
        def release(self): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    class FileLockTimeout(Exception): pass

# Try to import redis
try:
    import redis
    from redis.exceptions import LockError as RedisLockError
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    class RedisLockError(Exception): pass

class Timeout(Exception):
    """Unified Timeout exception for both FileLock and Redis Lock"""
    pass

class DistributedLock:
    """
    A Hybrid Lock that automatically uses Redis if REDIS_URL is provided,
    otherwise it falls back to a local FileLock.
    """
    def __init__(self, lock_path: str, timeout: int = 15):
        self.lock_path = lock_path
        self.timeout = timeout
        self.redis_url = os.environ.get("REDIS_URL")
        
        self.use_redis = bool(self.redis_url and HAS_REDIS)
        
        if self.use_redis:
            self.redis_client = redis.Redis.from_url(self.redis_url)
            # Use lock_path as the redis key. Replace slashes to make it a clean key.
            redis_key = f"wiki_lock:{lock_path.replace(os.sep, '_')}"
            # blocking_timeout corresponds to how long we wait to ACQUIRE the lock.
            # We set lock TTL to 60 seconds to prevent permanent deadlocks if process crashes.
            self.lock = self.redis_client.lock(redis_key, timeout=60, blocking_timeout=self.timeout)
        else:
            if not HAS_FILELOCK:
                # If neither is available, mock it safely (though not safe for actual concurrency)
                self.lock = FileLock(lock_path, timeout=timeout)
            else:
                self.lock = FileLock(lock_path, timeout=self.timeout)

    def __enter__(self):
        try:
            if self.use_redis:
                acquired = self.lock.acquire()
                if not acquired:
                    raise Timeout(f"Failed to acquire Redis lock for {self.lock_path}")
            else:
                self.lock.acquire()
        except FileLockTimeout:
            raise Timeout(f"Failed to acquire FileLock for {self.lock_path}")
        except RedisLockError:
            raise Timeout(f"Redis lock error for {self.lock_path}")
            
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.use_redis:
            try:
                self.lock.release()
            except RedisLockError:
                pass
        else:
            self.lock.release()
