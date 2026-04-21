import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from server.state_store import write_json_atomic, read_json, update_json_locked


def _runs_dir() -> Path:
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    p = base / ".claude/channels/assemble/runs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _progress_path(run_id: str) -> Path:
    return _runs_dir() / run_id / "progress.json"


def create_run(task: str, sequence: list[str]) -> str:
    now = datetime.now()
    run_id = now.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    body = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "task": task,
        "sequence": list(sequence),
        "current_stage_index": 0,
        "stages": [
            {"stage": s, "status": "pending", "tool_used": None,
             "started_at": None, "ended_at": None, "notes": ""}
            for s in sequence
        ],
    }
    write_json_atomic(_progress_path(run_id), body)
    return run_id


def load_progress(run_id: str) -> dict | None:
    return read_json(_progress_path(run_id))


def mark_stage(run_id: str, stage: str, status: str,
               tool_used: str | None = None, notes: str = "") -> dict:
    if status not in {"pending","in_progress","done","skipped","manual","back"}:
        raise ValueError(f"bad status: {status}")

    def upd(p: dict) -> dict:
        idx = next((i for i, s in enumerate(p["sequence"]) if s == stage), None)
        if idx is None:
            raise ValueError(f"stage {stage} not in sequence")
        st = p["stages"][idx]
        now = datetime.now().isoformat()
        if status == "in_progress" and st["started_at"] is None:
            st["started_at"] = now
        if status in {"done","skipped","manual"}:
            st["ended_at"] = now
            if tool_used:
                st["tool_used"] = tool_used
            p["current_stage_index"] = min(idx + 1, len(p["sequence"]) - 1)
        elif status == "back":
            p["current_stage_index"] = max(idx - 1, 0)
        st["status"] = status
        if notes:
            st["notes"] = notes
        p["updated_at"] = now
        return p

    return update_json_locked(_progress_path(run_id), upd)


def list_runs() -> list[str]:
    base = _runs_dir()
    return sorted(d.name for d in base.iterdir() if (d / "progress.json").exists())


def find_resumable(max_age_days: int = 7) -> list[str]:
    cutoff = time.time() - max_age_days * 24 * 3600
    out = []
    for rid in list_runs():
        p = _progress_path(rid)
        if p.stat().st_mtime < cutoff:
            continue
        body = read_json(p)
        if not body:
            continue
        statuses = [s["status"] for s in body["stages"]]
        if all(s in {"done","skipped","manual"} for s in statuses):
            continue
        out.append(rid)
    return sorted(out, key=lambda r: _progress_path(r).stat().st_mtime, reverse=True)
