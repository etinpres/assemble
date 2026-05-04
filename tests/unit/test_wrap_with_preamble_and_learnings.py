"""Phase D3 — `wrap_with_preamble_and_learnings` body-prefix fence injection.

The new wrapper layers learnings-fence rendering on top of `wrap_with_preamble`
without disturbing:
  - the canonical preamble bytes (sha256 unchanged → ALLOW_LIST membership),
  - the `wrap_with_preamble(prompt)` 1-arg signature (back-compat),
  - the `_TASK_DELIM = "\\n[TASK]\\n"` constant (audit boundary).

When the global ledger is empty (or `run_id`/`stage` unset) the result is
byte-identical to `wrap_with_preamble(prompt)` — zero behavior diff vs the
pre-Spike-X dispatch path.
"""

import hashlib
import json
from pathlib import Path

import pytest

import server
import server.harness as h
from server.harness import (
    ALLOWED_PROMPT_FILES,
    _PROMPT_TO_STAGE,
    _split_preamble_body,
    canonical_preamble_sha256,
    wrap_with_preamble,
    wrap_with_preamble_and_learnings,
)


@pytest.fixture
def tmp_assemble_with_bundles(tmp_path, monkeypatch):
    """Stage real bundled tree under tmp ASSEMBLE_HOME via symlink so
    `_resolve_prompt_path` and `_load_preamble` find their files, while
    learnings.jsonl + runs/ stay isolated under tmp."""
    real_home = Path.home()
    bundled_link = tmp_path / ".claude/skills/assemble"
    bundled_link.parent.mkdir(parents=True, exist_ok=True)
    bundled_link.symlink_to(real_home / ".claude/skills/assemble")
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h._CACHED_PREAMBLE.clear()
    yield tmp_path
    h._CACHED_PREAMBLE.clear()


def _seed_ledger(tmp_path, entries):
    ledger = tmp_path / ".claude/channels/assemble/learnings.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ledger


def _entry(rule_id="R1", category="scope-deviation",
           summary="default summary", ts="2026-05-04T12:00:00Z",
           evidence_hash=None):
    return {
        "ts": ts,
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        "evidence_hash": evidence_hash or hashlib.sha256(
            (rule_id + summary).encode()
        ).hexdigest(),
    }


# ---------------------------------------------------------------------------
# Degraded paths — return wrap_with_preamble(prompt) unchanged
# ---------------------------------------------------------------------------


def test_empty_ledger_byte_identical_to_wrap_with_preamble(
    tmp_assemble_with_bundles,
):
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage="plan"
    )
    assert out == wrap_with_preamble("BODY")


def test_missing_run_id_byte_identical(tmp_assemble_with_bundles):
    _seed_ledger(tmp_assemble_with_bundles, [_entry()])
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id=None, stage="plan"
    )
    assert out == wrap_with_preamble("BODY")


def test_missing_stage_byte_identical(tmp_assemble_with_bundles):
    _seed_ledger(tmp_assemble_with_bundles, [_entry()])
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage=None
    )
    assert out == wrap_with_preamble("BODY")


# ---------------------------------------------------------------------------
# Active paths — fence inserted into body
# ---------------------------------------------------------------------------


def test_non_empty_ledger_fence_inserted(tmp_assemble_with_bundles):
    _seed_ledger(tmp_assemble_with_bundles, [_entry(
        rule_id="R3", category="scope-deviation",
        summary="Edited src/auth.py despite deny pattern auth/*",
    )])
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage="plan"
    )
    assert "[PRIOR LEARNINGS — 우선 회피]" in out
    assert "[/PRIOR LEARNINGS]" in out
    assert "BODY" in out
    plain = wrap_with_preamble("BODY")
    pre, _ = _split_preamble_body(plain)
    assert out.startswith(pre)


def test_preamble_sha_unchanged_with_fence(tmp_assemble_with_bundles):
    _seed_ledger(tmp_assemble_with_bundles, [_entry()])
    canonical = canonical_preamble_sha256()
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage="plan"
    )
    pre, _ = _split_preamble_body(out)
    pre_sha = hashlib.sha256(pre.encode("utf-8")).hexdigest()
    assert pre_sha == canonical


def test_fence_inserted_between_task_and_body(tmp_assemble_with_bundles):
    _seed_ledger(tmp_assemble_with_bundles, [_entry(
        rule_id="R7", summary="fence ordering check",
    )])
    out = wrap_with_preamble_and_learnings(
        "ORIGINAL_BODY", run_id="rid", stage="plan"
    )
    fence_idx = out.index("[PRIOR LEARNINGS — 우선 회피]")
    body_idx = out.index("ORIGINAL_BODY")
    task_idx = out.index("\n[TASK]\n")
    assert task_idx < fence_idx < body_idx, (
        f"fence not between [TASK]\\n and body — "
        f"task={task_idx} fence={fence_idx} body={body_idx}"
    )


def test_only_first_task_delim_replaced(tmp_assemble_with_bundles):
    """If the body literally contains `\\n[TASK]\\n`, only the first
    occurrence (the preamble→body boundary) gets the fence injected."""
    _seed_ledger(tmp_assemble_with_bundles, [_entry()])
    body_with_marker = "first\n[TASK]\nnested-task-marker"
    out = wrap_with_preamble_and_learnings(
        body_with_marker, run_id="rid", stage="plan"
    )
    assert out.count("[PRIOR LEARNINGS") == 1
    assert "\n[TASK]\nnested-task-marker" in out


def test_top_k_limit_honored(tmp_assemble_with_bundles):
    entries = [
        _entry(
            rule_id=f"R{i}",
            ts=f"2026-05-04T12:{i:02d}:00Z",
            summary=f"learning #{i}",
        )
        for i in range(10)
    ]
    _seed_ledger(tmp_assemble_with_bundles, entries)
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage="plan", k=5
    )
    fence_start = out.index("[PRIOR LEARNINGS — 우선 회피]")
    fence_end = out.index("[/PRIOR LEARNINGS]")
    fence_block = out[fence_start:fence_end]
    numbered_lines = [
        line for line in fence_block.splitlines()
        if line and line[0].isdigit() and ". (" in line
    ]
    assert len(numbered_lines) == 5


def test_stage_category_priority_drives_ordering(tmp_assemble_with_bundles):
    """Plan stage prioritizes scope-deviation > ac-failure > todo-leakage > rule-violation.
    Even if a less-prioritized entry is newer, the higher-priority entry
    must rank first inside the fence."""
    entries = [
        _entry(
            rule_id="Rnew", category="rule-violation",
            ts="2026-05-04T23:59:00Z",
            summary="newer but lower priority",
        ),
        _entry(
            rule_id="Rold", category="scope-deviation",
            ts="2026-05-04T01:00:00Z",
            summary="older but top priority for plan",
        ),
    ]
    _seed_ledger(tmp_assemble_with_bundles, entries)
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage="plan"
    )
    pos_old = out.index("Rold")
    pos_new = out.index("Rnew")
    assert pos_old < pos_new


def test_empty_fence_when_no_relevant_entries(tmp_assemble_with_bundles):
    """Even when no category matches the stage's priority list, recency-only
    ranking still produces a fence — so a fence IS emitted."""
    _seed_ledger(tmp_assemble_with_bundles, [
        _entry(rule_id="R1", category="not-in-priority-list",
               ts="2026-05-04T01:00:00Z", summary="A"),
        _entry(rule_id="R2", category="also-not-listed",
               ts="2026-05-04T02:00:00Z", summary="B"),
    ])
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid", stage="plan"
    )
    assert "[PRIOR LEARNINGS" in out


def test_record_dispatch_preamble_sha_unchanged(tmp_assemble_with_bundles):
    """End-to-end: wrap_with_preamble_and_learnings → record_dispatch →
    `verify_dispatches.ok=True` (preamble sha hits ALLOW_LIST)."""
    _seed_ledger(tmp_assemble_with_bundles, [_entry()])
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid-x", stage="plan"
    )
    h.record_dispatch(
        "rid-x", step="step.x", prompt_text=out,
        subagent_type="general-purpose",
    )
    audit = server.verify_dispatches("rid-x")
    assert audit["ok"] is True
    assert audit["total"] == 1
    assert audit["mismatches"] == []


def test_verify_dispatches_ok_with_learnings_fence(tmp_assemble_with_bundles):
    _seed_ledger(tmp_assemble_with_bundles, [_entry(
        rule_id="R5",
        summary="verify_dispatches check with fence body",
    )])
    canonical = canonical_preamble_sha256()
    out = wrap_with_preamble_and_learnings(
        "BODY", run_id="rid-y", stage="plan"
    )
    h.record_dispatch(
        "rid-y", step="step.y", prompt_text=out,
        subagent_type="general-purpose",
    )
    log = (
        tmp_assemble_with_bundles / ".claude/channels/assemble/runs"
        / "rid-y" / "dispatches.jsonl"
    )
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert rows[0]["preamble_sha256"] == canonical
    audit = server.verify_dispatches("rid-y")
    assert audit["ok"] is True


# ---------------------------------------------------------------------------
# Back-compat + map coverage
# ---------------------------------------------------------------------------


def test_back_compat_wrap_with_preamble_signature_unchanged():
    """`wrap_with_preamble(prompt)` MUST remain a 1-arg call."""
    out = wrap_with_preamble("hello")
    assert isinstance(out, str)
    import inspect
    sig = inspect.signature(wrap_with_preamble)
    assert list(sig.parameters.keys()) == ["prompt"]


def test_prompt_to_stage_covers_all_allowed():
    """Every entry in `ALLOWED_PROMPT_FILES` MUST have a stage mapping —
    no missing entries (dispatched without stage hint), no extras (dead
    map entries that no longer correspond to a real prompt)."""
    map_keys = set(_PROMPT_TO_STAGE.keys())
    allowed = set(ALLOWED_PROMPT_FILES)
    only_map = map_keys - allowed
    only_allowed = allowed - map_keys
    assert not only_map, f"_PROMPT_TO_STAGE has dead entries: {sorted(only_map)}"
    assert not only_allowed, (
        f"ALLOWED_PROMPT_FILES entries missing from _PROMPT_TO_STAGE: "
        f"{sorted(only_allowed)}"
    )


def test_prompt_to_stage_values_are_known_stages():
    from server.learnings import STAGE_CATEGORY_PRIORITY
    valid_stages = set(STAGE_CATEGORY_PRIORITY.keys())
    for prompt, stage in _PROMPT_TO_STAGE.items():
        assert stage in valid_stages, (
            f"prompt {prompt!r} maps to unknown stage {stage!r}"
        )
