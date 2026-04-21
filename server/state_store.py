import fcntl
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional


def write_json_atomic(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp",
                                    dir=str(path.parent))
    tmp = Path(tmp_str)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def read_json(path: Path) -> Optional[Any]:
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"[state_store] corrupt JSON at {path}: {e}", file=sys.stderr)
        return None


@contextmanager
def _file_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def update_json_locked(path: Path, updater: Callable[[dict], dict]) -> dict:
    path = Path(path)
    lock = path.with_suffix(path.suffix + ".lock")
    with _file_lock(lock):
        current = read_json(path) or {}
        new = updater(current)
        write_json_atomic(path, new)
        return new
