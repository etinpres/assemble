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


def _validate_components(run_id: str, filename: str) -> None:
    """Reject path-traversal / absolute-path injection on either component.

    Both `run_id` and `filename` must be plain basenames (no `/`, no `..`,
    no leading dot). The caller is the bundled `plan-pack` SKILL today, but
    this is the canonical write helper for the entire bundled library —
    once a sub-agent's output ever flows into either component (e.g. a
    user-typed task slug) the surface widens to prompt-injection-to-
    arbitrary-file-write. Cheap to guard at the gate.
    """
    for label, value in (("run_id", run_id), ("filename", filename)):
        if not value:
            raise ValueError(f"unsafe {label}: empty")
        if "/" in value or "\\" in value:
            raise ValueError(f"unsafe {label}: contains separator: {value!r}")
        if value.startswith("."):
            raise ValueError(f"unsafe {label}: starts with '.': {value!r}")
        if value != Path(value).name:
            raise ValueError(f"unsafe {label}: not a plain basename: {value!r}")


def run_artifact_path(run_id: str, filename: str) -> Path:
    """Return the artifact's absolute path. Does not create anything."""
    _validate_components(run_id, filename)
    return _runs_dir() / run_id / filename


def write_run_artifact(run_id: str, filename: str, content: str) -> Path:
    """Atomically write `content` to `<runs>/<run_id>/<filename>`.

    The run directory is created if missing. Writes go to a temp file in the
    same directory, then `Path.replace` swaps it into place — concurrent
    writers never see a torn file.

    Raises ValueError if `run_id` or `filename` would escape `<runs>/`.
    """
    target = run_artifact_path(run_id, filename)  # validates components
    target.parent.mkdir(parents=True, exist_ok=True)
    # Defense in depth: even after basename validation, confirm the resolved
    # target sits under runs_dir. Catches symlink swaps that a basename check
    # alone wouldn't.
    runs_root = _runs_dir().resolve()
    resolved_target = target.resolve()
    if not str(resolved_target).startswith(str(runs_root) + os.sep):
        raise ValueError(
            f"resolved target escapes runs root: {resolved_target}"
        )
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
        tmp.unlink(missing_ok=True)
        raise
    return target


def read_run_artifact(run_id: str, filename: str) -> Optional[str]:
    """Return the artifact's text or None if the file does not exist."""
    p = run_artifact_path(run_id, filename)
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def strip_bash_fence(s: str) -> str:
    """Strip leading/trailing triple-backtick fences and `bash` language tag.

    Sub-task B (AC bash) is supposed to return a raw one-liner, but a
    `Plan` agent occasionally wraps the result in ```` ```bash ... ``` ````.
    This helper makes the strip deterministic — Step 5 references it
    instead of describing the algorithm in prose.

    Handles: bare command, ```bash-fenced, ``` bare-fenced, with/without
    trailing newline. Whitespace-tolerant.
    """
    lines = s.strip().splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].lstrip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def update_iteration_state(run_id: str, counts: dict) -> Path:
    """Append one iteration record to `runs/<run_id>/iteration_state.json`.

    Spike II §3.1 F15 + D9: orchestrator metadata write helper. Main Claude
    parses the `COUNTS: resolved=<N> unresolved=<N> new=<N>` line emitted by
    Step 9 sub-agent, computes `resolved_pct`, and calls this in one line:

        from server import update_iteration_state
        update_iteration_state("20260501-abcd", {
            "resolved_pct": 0.85, "new_count": 0,
            "stopped": False, "reason": ""
        })

    The hook whitelist (Spike II §3.1 F8) lets main do this directly under
    `runs/<rid>/iteration_state.json` — no sub-agent dispatch needed
    (B-6 dogfood showed delegation cost = 23 tool uses, 58.6k tokens).

    File schema:
        {"iterations": [{"index": 0, ...}, {"index": 1, ...}, ...]}

    Append-only. `index` is auto-assigned by current list length. Atomic
    via `write_run_artifact`.

    Returns the absolute path of iteration_state.json.
    """
    import json as _json
    target = run_artifact_path(run_id, "iteration_state.json")  # validates
    if target.exists():
        try:
            state = _json.loads(target.read_text(encoding="utf-8"))
        except (_json.JSONDecodeError, OSError):
            # Corrupt or unreadable — start fresh. Don't silently mask
            # a programmer error; raising would block the workflow.
            state = {"iterations": []}
    else:
        state = {"iterations": []}
    if "iterations" not in state or not isinstance(state["iterations"], list):
        state["iterations"] = []
    entry = {"index": len(state["iterations"]), **counts}
    state["iterations"].append(entry)
    return write_run_artifact(run_id, "iteration_state.json",
                               _json.dumps(state, indent=2, ensure_ascii=False))
