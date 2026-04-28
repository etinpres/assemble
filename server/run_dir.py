"""Run-directory artifact I/O.

`progress.py` owns `progress.json` inside each run directory. This module
owns the *content artifacts* (PRD.md, ARCHITECTURE.md, ADR.md, UI_GUIDE.md,
trace files, …) so each concern stays testable in isolation.

Atomic writes use the same temp-file-then-rename pattern that
`state_store.write_json_atomic` uses, generalized to bytes/text.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional


def _runs_dir() -> Path:
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    return base / ".claude/channels/assemble/runs"


def run_artifact_path(run_id: str, filename: str) -> Path:
    """Return the artifact's absolute path. Does not create anything."""
    return _runs_dir() / run_id / filename


def write_run_artifact(run_id: str, filename: str, content: str) -> Path:
    """Atomically write `content` to `<runs>/<run_id>/<filename>`.

    The run directory is created if missing. Writes go to a temp file in the
    same directory, then `Path.replace` swaps it into place — concurrent
    writers never see a torn file.
    """
    target = run_artifact_path(run_id, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(prefix=target.name + ".",
                                    suffix=".tmp",
                                    dir=str(target.parent))
    tmp = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(target)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    return target


def read_run_artifact(run_id: str, filename: str) -> Optional[str]:
    """Return the artifact's text or None if the file does not exist."""
    p = run_artifact_path(run_id, filename)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")
