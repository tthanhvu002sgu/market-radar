import os
import time
from pathlib import Path
from config.settings import LOCK_FILE

class ProcessLock:
    """Simple file-based process lock to prevent concurrent data updates."""
    
    def __init__(self, lock_file: Path = LOCK_FILE, timeout_seconds: int = 600):
        self.lock_file = Path(lock_file)
        self.timeout_seconds = timeout_seconds
        self.acquired = False

    def acquire(self) -> bool:
        if self.lock_file.exists():
            # Check if lock file is stale (older than timeout_seconds)
            mtime = self.lock_file.stat().st_mtime
            if time.time() - mtime > self.timeout_seconds:
                try:
                    self.lock_file.unlink()
                except OSError:
                    return False
            else:
                return False

        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.lock_file, "w") as f:
                f.write(f"{os.getpid()}:{time.time()}")
            self.acquired = True
            return True
        except OSError:
            return False

    def release(self):
        if self.acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except OSError:
                pass
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Lock could not be acquired (process already running or lock file exists: {self.lock_file})")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
