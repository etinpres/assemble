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


ALLOWED_PROMPT_FILES = (
    # plan-pack ★ (Spike I-III, 8 files)
    "prd_step2.md",
    "prd_step3.md",
    "prd_step4.md",
    "arch_step8.md",
    "adr_step11.md",
    "ui_step13.md",
    "cross_doc_step9.md",
    "iter_emphasis.md",
    # debugger ★ (Spike IV, 6 files — added incrementally C3-C7)
    "repro_step2.md",
    "hypothesis_step3.md",
    "root_cause_step4.md",
)


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


def _resolve_prompt_path(prompt_file: str) -> Path:
    """Return the on-disk path for a known prompt file.

    After Phase C6 (Spike III §2.6) the directory layout is:
        bundled/plan-pack/prompts/subagent/<name>.md   (7 files)
        bundled/plan-pack/prompts/orchestrator/<name>.md (1 file: iter_emphasis.md)

    Phase B implementation predates the move — the resolver checks the
    legacy flat path first, then the two subdirs. After C6 lands, the
    flat path stops resolving; this resolver continues to work without
    edits.

    Honors ASSEMBLE_HOME (mirrors `_preamble_path`) so test fixtures can
    redirect the lookup root.

    Bundle order: plan-pack first (most prompts), debugger second (Spike IV).
    """
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home()))) / (
        ".claude/skills/assemble/bundled"
    )
    for bundle in ("plan-pack", "debugger"):
        for sub in ("subagent", "orchestrator", ""):
            candidate = base / bundle / "prompts" / sub / prompt_file if sub else base / bundle / "prompts" / prompt_file
            if candidate.exists():
                return candidate
    raise FileNotFoundError(
        f"prompt_file {prompt_file!r} not found under {base} (or subdirs)"
    )


def dispatch_prompt(prompt_file: str) -> str:
    """Load a known prompt and prepend the harness preamble.

    Allowlist-checked: `prompt_file` must be in `ALLOWED_PROMPT_FILES` —
    raises ValueError with §CRITICAL pointer otherwise. The file is
    resolved via `_resolve_prompt_path` (subagent/, orchestrator/, then
    flat fallback) so this function ships independent of the Phase C6
    file move.

    Placeholder substitution is the caller's responsibility — the
    orchestrator already knows which `{{KEY}}` tokens belong to its
    Inputs section vs. the sub-agent's own `.replace("{{KEY}}", var)`
    instructions inside the canonical save block. A naive global
    `.replace` would corrupt the latter. See spec §1.2 (B2 — option B)
    for the rationale.

    Returns: the wrapped prompt (preamble + [TASK] + body) ready for
    the caller's substitution pass + Agent dispatch.
    """
    if prompt_file not in ALLOWED_PROMPT_FILES:
        raise ValueError(
            f"prompt_file {prompt_file!r} not allowed. "
            f"See SKILL.md §CRITICAL anti-bypass + ALLOWED_PROMPT_FILES "
            f"in server.harness "
            f"(current allowlist: {len(ALLOWED_PROMPT_FILES)} files)."
        )
    text = _resolve_prompt_path(prompt_file).read_text(encoding="utf-8")
    return wrap_with_preamble(text)


# `wrap_with_preamble` emits `<pre>\n[TASK]\n<prompt>` where `pre` is
# `<file_content_rstripped> + "\n"`. The full prompt thus contains
# `<rstripped>\n\n[TASK]\n<body>`. Splitting on the *single*-leading-newline
# delimiter `\n[TASK]\n` makes the preamble portion include its trailing
# newline (`<rstripped>\n`), which exactly matches the on-disk preamble file
# bytes. That alignment makes `canonical_preamble_sha256()` equal to the
# sha256 of the preamble file itself (`bundled/_shared/harness-preamble.md`,
# `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159`).
_TASK_DELIM = "\n[TASK]\n"


# Spike I §8.3: pre-cutoff (2026-04-30) dogfood data was written under the
# v1 preamble. Spike II 이전 live data is v2.
# Spike II §3.1 F12: post-cutoff (2026-05-01) live data is v3 (rule 7 추가
# + rule 5 외래어 표기 사례). ALLOW_LIST 는 v1 + v2 + canonical(=v3) 3개를
# 모두 인정해서 과거 dogfood 검증이 깨지지 않도록 한다.
# See docs/research/2026-05-01-preamble-v3-cutoff.md.
_PREAMBLE_V1_SHA256 = (
    "858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159"
)
_PREAMBLE_V2_SHA256 = (
    "df27450513c019a9dd395d8f62c99b445e7a16b4fcdbb5cba52c352397993549"
)


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
    prompt_text: str = "",
    *,
    subagent_type: str = "",
    description: str = "",
    wrote_path: Optional[str] = None,
    prompt_file: Optional[str] = None,
    status: str = "dispatched",
    note: Optional[str] = None,
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
          "body_bytes": <int>,
          "wrote_path": "<str>" | null,
          "prompt_file": "<allowed-name.md>" | null,
          "status": "dispatched" | "skipped" | "failed",
          "note": "<str>" | null
        }

    `wrote_path` (Spike I §8.1): optional absolute path the dispatched
    sub-agent is expected to write its primary artifact to (e.g.
    `/tmp/<rid>/PRD.md`). Defaults to `None` for back-compat with callers
    that don't yet pass it. Recorded as-is (no validation) — downstream
    audits can cross-check existence at verify time.

    Returns the absolute path of the dispatches.jsonl file (created on
    first call; parent run dir created if missing).

    `run_id` and `step` must be non-empty. `run_id` is restricted to a
    plain basename (no `/`, `\\`, leading dot) — same rule as
    `server.run_dir.run_artifact_path` — so a malformed `run_id` cannot
    escape the runs root.

    `status` (Spike IV §1.1 A1): one of `"dispatched"` (default — the
    orchestrator did dispatch), `"skipped"` (orchestrator chose not to
    dispatch, e.g. iter1 (no change), but recorded the intent), or
    `"failed"` (dispatch attempted, sub-agent returned ERROR or no WROTE).
    `note` (Spike IV §1.2 B1): free-form annotation (e.g. user emphasis
    string). Both default to dispatched/None for back-compat with
    pre-Spike-IV callers.
    """
    if not run_id or not step:
        raise ValueError("run_id and step are required")
    if "/" in run_id or "\\" in run_id or run_id.startswith("."):
        raise ValueError(f"unsafe run_id: {run_id!r}")
    if run_id != Path(run_id).name:
        raise ValueError(f"unsafe run_id: not a plain basename: {run_id!r}")
    if status not in ("dispatched", "skipped", "failed"):
        raise ValueError(
            f"unknown status: {status!r} (allowed: dispatched/skipped/failed)"
        )

    if prompt_file is not None and prompt_file not in ALLOWED_PROMPT_FILES:
        msg = (
            f"prompt_file {prompt_file!r} not in ALLOWED_PROMPT_FILES "
            f"(SKILL.md §CRITICAL anti-bypass)"
        )
        if os.environ.get("ASSEMBLE_DISPATCH_STRICT") == "1":
            raise ValueError(msg)
        print(f"[harness] WARN: {msg}", file=sys.stderr)

    # When status="skipped" the orchestrator never built a real prompt,
    # so prompt_text may be empty — use placeholder hashes.
    preamble, body = _split_preamble_body(prompt_text or "")
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
        "wrote_path": wrote_path,
        "prompt_file": prompt_file,
        "status": status,
        "note": note,
    }

    out = _dispatches_path(run_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out


def dispatch_and_record(
    run_id: str,
    *,
    prompt_file: str,
    step: str,
    subagent_type: str = "general-purpose",
    description: str = "",
    wrote_path: Optional[str] = None,
    status: str = "dispatched",
    note: Optional[str] = None,
) -> str:
    """Compose `dispatch_prompt` and `record_dispatch` atomically.

    Returns the wrapped prompt text (empty string when `status="skipped"`,
    in which case the caller should not invoke the Agent tool — the
    audit row alone documents the orchestrator's skip decision).

    Spike IV §1.1 A1 (carryforward A): the iter1 4-way path elided the
    audit row because `dispatch_prompt` and `record_dispatch` are two
    independent calls. This wrapper makes the pairing un-skippable from
    the orchestrator's side.

    Spike IV §1.2 B1 (carryforward B): the `(no change)` iter1 case
    flips to `status="skipped"` — main does NOT dispatch, only records.

    Status semantics:
        dispatched  — orchestrator returned the wrapped prompt, caller
                      will invoke Agent tool with it.
        skipped     — orchestrator chose not to dispatch (e.g. user
                      emphasis was (no change)). Returns "".
        failed      — orchestrator dispatched but sub-agent returned
                      ERROR / no WROTE. Caller logs failure and surfaces
                      to user via AskUserQuestion (per SKILL.md §CRITICAL
                      retry path).
    """
    if status not in ("dispatched", "skipped", "failed"):
        raise ValueError(
            f"unknown status: {status!r} (allowed: dispatched/skipped/failed)"
        )

    prompt_text = ""
    if status == "dispatched":
        prompt_text = dispatch_prompt(prompt_file)

    record_dispatch(
        run_id,
        step=step,
        prompt_text=prompt_text,
        subagent_type=subagent_type,
        description=description,
        wrote_path=wrote_path,
        prompt_file=prompt_file,
        status=status,
        note=note,
    )
    return prompt_text


def verify_dispatches(run_id: str) -> dict:
    """Audit `runs/<run_id>/dispatches.jsonl` against the canonical preamble.

    Returns:
        {
          "ok": bool,                       # True iff every record's
                                            # preamble_sha256 is in the
                                            # ALLOW_LIST (v1 + v2)
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

    Spike I §8.3: the comparison uses an ALLOW_LIST of `{v1, v2}` shas
    so dogfood data persisted under the pre-cutoff (2026-04-30) v1
    preamble still verifies green. `want` in mismatches reports the
    current canonical (v2) so the audit message points at the live
    expectation.
    """
    canonical = canonical_preamble_sha256()
    out: dict = {
        "ok": True,
        "total": 0,
        "canonical_preamble_sha256": canonical,
        "mismatches": [],
        "missing_file": False,
    }
    path = _dispatches_path(run_id)
    if not path.exists():
        out["ok"] = False
        out["missing_file"] = True
        return out
    # ALLOW_LIST: pre-cutoff v1 + Spike-I-cutoff v2 + live v3 (canonical).
    allow_list = {_PREAMBLE_V1_SHA256, _PREAMBLE_V2_SHA256}
    if canonical is not None:
        allow_list.add(canonical)
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            out["total"] += 1
            got = rec.get("preamble_sha256")
            if got not in allow_list:
                out["ok"] = False
                out["mismatches"].append({
                    "line": line_no,
                    "step": rec.get("step", "?"),
                    "got": got,
                    "want": canonical,
                })
    return out
