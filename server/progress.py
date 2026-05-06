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


VALID_STATUS = {"pending","in_progress","done","skipped","manual","back"}
TERMINAL_STATUS = {"done","skipped","manual"}
VALID_ORTHOGONAL_STAGES = {"safety", "meta"}


def _ensure_orthogonal_field(p: dict) -> None:
    """Backwards-compat: schema 확장 — 'orthogonal_stages' field 없으면 생성."""
    if "orthogonal_stages" not in p:
        p["orthogonal_stages"] = {}


def mark_orthogonal_stage(run_id: str, stage: str, status: str,
                          tool_used: str | None = None,
                          notes: str = "") -> dict:
    """Mark an orthogonal stage (safety, meta) — separate from main sequence.

    orthogonal stages 는 V4 결정 #1 라인업 의 가로축 (sequence 8) + 세로축
    (orthogonal 2). main sequence 와 독립적으로 활성/완료될 수 있음.
    """
    if stage not in VALID_ORTHOGONAL_STAGES:
        raise ValueError(
            f"orthogonal stage must be one of {VALID_ORTHOGONAL_STAGES}, "
            f"got {stage!r}. main-sequence stages use mark_stage()."
        )
    if status not in VALID_STATUS:
        raise ValueError(f"bad status: {status}")
    if status == "back":
        raise ValueError("'back' is sequence-only — orthogonal stages have no cursor")

    def upd(p: dict) -> dict:
        _ensure_orthogonal_field(p)
        now = datetime.now().isoformat()
        entry = p["orthogonal_stages"].get(stage, {
            "stage": stage, "status": "pending", "tool_used": None,
            "started_at": None, "ended_at": None, "notes": "",
        })

        if status == "in_progress" and entry["started_at"] is None:
            entry["started_at"] = now
        if status in TERMINAL_STATUS:
            if entry["started_at"] is None:
                entry["started_at"] = now
            entry["ended_at"] = now
            if tool_used:
                entry["tool_used"] = tool_used
        entry["status"] = status
        if notes:
            entry["notes"] = notes
        p["orthogonal_stages"][stage] = entry
        p["updated_at"] = now
        return p

    return update_json_locked(_progress_path(run_id), upd)


def mark_stage(run_id: str, stage: str, status: str,
               tool_used: str | None = None, notes: str = "") -> dict:
    """Update a stage's status with transition guards.

    'back' is a cursor command, not a persisted status — it moves
    current_stage_index without overwriting the stage's recorded status.
    """
    if stage in VALID_ORTHOGONAL_STAGES:
        # auto-route: orthogonal stages 는 mark_orthogonal_stage 로 forwarding
        return mark_orthogonal_stage(run_id, stage, status, tool_used, notes)

    if status not in VALID_STATUS:
        raise ValueError(f"bad status: {status}")

    def upd(p: dict) -> dict:
        idx = next((i for i, s in enumerate(p["sequence"]) if s == stage), None)
        if idx is None:
            raise ValueError(f"stage {stage} not in sequence")
        st = p["stages"][idx]
        now = datetime.now().isoformat()

        if status == "back":
            # `back` is cursor-only. The stage's recorded status
            # (pending/in_progress/done/...) is preserved. Earlier versions
            # stamped status='back', which broke wrap-up counts and
            # find_resumable.
            p["current_stage_index"] = max(idx - 1, 0)
            p["updated_at"] = now
            return p

        current = st.get("status", "pending")
        if current in TERMINAL_STATUS and status == "in_progress":
            raise ValueError(
                f"illegal transition: stage '{stage}' already '{current}'. "
                "Use 'back' to revisit, not 'in_progress'."
            )

        if status == "in_progress" and st["started_at"] is None:
            st["started_at"] = now
        if status in TERMINAL_STATUS:
            if st["started_at"] is None:
                st["started_at"] = now
            st["ended_at"] = now
            if tool_used:
                st["tool_used"] = tool_used
            p["current_stage_index"] = min(idx + 1, len(p["sequence"]) - 1)
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
