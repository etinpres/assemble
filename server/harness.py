"""Harness-preamble prepend helper.

Bundled SKILLs prepend a fixed 4-rule "harness preamble" to every dispatched
sub-agent prompt so subagents inherit the rules even when they cannot read
the SKILL.md text. The preamble lives at
`~/.claude/skills/assemble/bundled/_shared/harness-preamble.md` and is
loaded once per process (lru_cache).

`record_dispatch` + `verify_dispatches` upgrade gate B5.7 evidence from
orchestrator self-report (claiming the preamble matched) to a replayable
on-disk audit (`runs/<rid>/dispatches.jsonl` with hash-only records). The
orchestrator is expected to call `record_dispatch` once per dispatch site,
right after `wrap_with_preamble`. Records store sha256 hashes only — full
prompts are not persisted, so dispatches.jsonl is safe to commit and does
not leak user content.
"""

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Optional


_PREAMBLE_REL = ".claude/skills/assemble/bundled/_shared/harness-preamble.md"


def _preamble_path() -> Path:
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    return base / _PREAMBLE_REL


_CACHED_PREAMBLE: dict[Path, str] = {}


def _load_preamble() -> str | None:
    """Load preamble for the *current* `_preamble_path()`.

    Cached per resolved path — does NOT cache the missing-file (None) result,
    so a preamble created after first call is picked up on the next call.
    Caching by path also prevents stale reuse if `ASSEMBLE_HOME` changes
    between calls in a long-running process (e.g. pytest fixture swaps).
    """
    p = _preamble_path()
    if p in _CACHED_PREAMBLE:
        return _CACHED_PREAMBLE[p]
    if not p.exists():
        print(f"[harness] missing preamble at {p}; "
              "wrap_with_preamble will return prompts unchanged.",
              file=sys.stderr)
        return None  # not cached — re-check next call
    text = p.read_text(encoding="utf-8").rstrip() + "\n"
    _CACHED_PREAMBLE[p] = text
    return text


def wrap_with_preamble(prompt: str) -> str:
    """Return `prompt` wrapped so the harness preamble runs before it.

    Format:
        <preamble>

        [TASK]
        <prompt>

    If the preamble file is missing, the prompt is returned unchanged and a
    one-line warning is printed to stderr (no exception — bundled SKILLs
    should still function in degraded mode).
    """
    pre = _load_preamble()
    if pre is None:
        return prompt
    return f"{pre}\n[TASK]\n{prompt}"


# `wrap_with_preamble` emits `<pre>\n[TASK]\n<prompt>` where `pre` is
# `<file_content_rstripped> + "\n"`. The full prompt thus contains
# `<rstripped>\n\n[TASK]\n<body>`. Splitting on the *single*-leading-newline
# delimiter `\n[TASK]\n` makes the preamble portion include its trailing
# newline (`<rstripped>\n`), which exactly matches the on-disk preamble file
# bytes. That alignment makes `canonical_preamble_sha256()` equal to the
# sha256 of the preamble file itself (`bundled/_shared/harness-preamble.md`,
# `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159`).
_TASK_DELIM = "\n[TASK]\n"


def canonical_preamble_sha256() -> Optional[str]:
    """sha256 hex of the canonical preamble file's bytes.

    Returns None when the preamble file is missing (degraded-mode parity
    with `wrap_with_preamble`). Reads the preamble file from
    `<ASSEMBLE_HOME>/.claude/skills/assemble/bundled/_shared/harness-preamble.md`
    via `_load_preamble`, then hashes the on-disk bytes (rstripped + "\n",
    256 bytes for the canonical 4-rule preamble). The same byte range is
    what `_split_preamble_body` extracts as the preamble portion of any
    dispatched prompt, so this hash is the audit constant.
    """
    pre = _load_preamble()
    if pre is None:
        return None
    return hashlib.sha256(pre.encode("utf-8")).hexdigest()


def _split_preamble_body(prompt_text: str) -> tuple[str, str]:
    """Return (preamble, body) by splitting on the canonical [TASK] delimiter.

    Splits on `\\n[TASK]\\n` (single leading newline) so the preamble portion
    includes its trailing newline — matches the on-disk preamble file's
    byte-for-byte form. If the delimiter isn't present, returns
    ("", prompt_text) — caller passed an unwrapped prompt (degraded mode);
    we still record what we have so the dispatch is observable.
    """
    if _TASK_DELIM not in prompt_text:
        return "", prompt_text
    idx = prompt_text.index(_TASK_DELIM)
    return prompt_text[:idx], prompt_text[idx + len(_TASK_DELIM):]


def _dispatches_path(run_id: str) -> Path:
    """Return path to `runs/<run_id>/dispatches.jsonl`.

    Mirrors `server.run_dir._runs_dir()` so all run-dir consumers agree
    on location.
    """
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    return base / ".claude/channels/assemble/runs" / run_id / "dispatches.jsonl"


def record_dispatch(
    run_id: str,
    step: str,
    prompt_text: str,
    *,
    subagent_type: str = "",
    description: str = "",
) -> Path:
    """Append one hash-only record to `runs/<run_id>/dispatches.jsonl`.

    The record stores sha256 of the preamble portion + sha256 of the body
    portion + byte counts + step/subagent/description metadata. Full prompt
    text is NOT persisted — privacy-safe and compact.

    Schema (JSON object, one per line):
        {
          "ts": "<ISO8601 UTC>",
          "step": "<free-form, e.g. step6.iter2.PRD>",
          "subagent_type": "<e.g. general-purpose>",
          "description": "<short label>",
          "preamble_sha256": "<64 hex chars>",
          "preamble_bytes": <int>,
          "body_sha256": "<64 hex chars>",
          "body_bytes": <int>
        }

    Returns the absolute path of the dispatches.jsonl file (created on
    first call; parent run dir created if missing).

    `run_id` and `step` must be non-empty. `run_id` is restricted to a
    plain basename (no `/`, `\\`, leading dot) — same rule as
    `server.run_dir.run_artifact_path` — so a malformed `run_id` cannot
    escape the runs root.
    """
    if not run_id or not step:
        raise ValueError("run_id and step are required")
    if "/" in run_id or "\\" in run_id or run_id.startswith("."):
        raise ValueError(f"unsafe run_id: {run_id!r}")
    if run_id != Path(run_id).name:
        raise ValueError(f"unsafe run_id: not a plain basename: {run_id!r}")

    preamble, body = _split_preamble_body(prompt_text)
    pre_bytes = preamble.encode("utf-8")
    body_bytes = body.encode("utf-8")

    record = {
        "ts": (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        ),
        "step": step,
        "subagent_type": subagent_type,
        "description": description,
        "preamble_sha256": hashlib.sha256(pre_bytes).hexdigest(),
        "preamble_bytes": len(pre_bytes),
        "body_sha256": hashlib.sha256(body_bytes).hexdigest(),
        "body_bytes": len(body_bytes),
    }

    out = _dispatches_path(run_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out


def verify_dispatches(run_id: str) -> dict:
    """Audit `runs/<run_id>/dispatches.jsonl` against the canonical preamble.

    Returns:
        {
          "ok": bool,                       # True iff every record's
                                            # preamble_sha256 == canonical
          "total": int,                     # records read
          "canonical_preamble_sha256": str | None,
          "mismatches": [
            {"line": <1-based int>, "step": ..., "got": ..., "want": ...},
            ...
          ],
          "missing_file": bool,             # True iff dispatches.jsonl
                                            # doesn't exist for this run
        }

    A run with zero dispatches recorded is treated as `ok=False` only
    when `dispatches.jsonl` is missing entirely (`missing_file=True`).
    An empty file is `ok=True, total=0`.
    """
    out: dict = {
        "ok": True,
        "total": 0,
        "canonical_preamble_sha256": canonical_preamble_sha256(),
        "mismatches": [],
        "missing_file": False,
    }
    path = _dispatches_path(run_id)
    if not path.exists():
        out["ok"] = False
        out["missing_file"] = True
        return out
    canonical = out["canonical_preamble_sha256"]
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            out["total"] += 1
            got = rec.get("preamble_sha256")
            if canonical is None or got != canonical:
                out["ok"] = False
                out["mismatches"].append({
                    "line": line_no,
                    "step": rec.get("step", "?"),
                    "got": got,
                    "want": canonical,
                })
    return out
