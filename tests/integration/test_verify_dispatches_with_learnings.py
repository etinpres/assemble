"""Targeted regression tests covering Track B's body-prefix splice path
under `verify_dispatches` (V4 Spike X, Phase F3).

Track B (Phase D3+D4) splices a `[PRIOR LEARNINGS — 우선 회피]` fence
into the body region of a wrapped prompt — immediately after the
`\\n[TASK]\\n` delimiter, before the original prompt body. The preamble
portion stays byte-identical, so `canonical_preamble_sha256()` is
preserved across empty/non-empty ledger states.

These tests are the canary for any future regression where fence
splicing accidentally reaches into preamble bytes (a one-line bug in the
`replace(... count=1)` boundary would silently break `verify_dispatches`
green for every dispatch with a non-empty ledger). They exercise the
full record_dispatch → dispatches.jsonl → verify_dispatches loop with
both empty and non-empty ledger states.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import server
import server.harness as h
from server.harness import canonical_preamble_sha256, wrap_with_preamble


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_ledger(home: Path, entries: list[dict]) -> Path:
    """Write entries to the global learnings.jsonl under ``home``."""
    ledger = home / ".claude/channels/assemble/learnings.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ledger


def _entry(
    rule_id: str = "R2",
    category: str = "scope-deviation",
    summary: str = "Edited src/auth.py despite deny pattern.",
    ts: str = "2026-05-04T12:00:00Z",
) -> dict:
    return {
        "ts": ts,
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        "evidence_hash": hashlib.sha256(
            (rule_id + summary).encode()
        ).hexdigest(),
    }


@pytest.fixture
def tmp_assemble(tmp_path, monkeypatch):
    """Stage the real bundled tree under ``tmp_path`` via symlink so prompt
    resolution + canonical preamble work, but learnings.jsonl + runs/
    stay isolated under tmp.

    Mirrors the fixture used by `test_dispatch_and_record_learnings.py`
    so we exercise the same dispatch surface under the same conditions.
    """
    real_home = Path.home()
    bundled_link = tmp_path / ".claude/skills/assemble"
    bundled_link.parent.mkdir(parents=True, exist_ok=True)
    bundled_link.symlink_to(real_home / ".claude/skills/assemble")
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h._CACHED_PREAMBLE.clear()
    runs = tmp_path / ".claude/channels/assemble/runs/test-rid"
    runs.mkdir(parents=True, exist_ok=True)
    yield tmp_path, "test-rid"
    h._CACHED_PREAMBLE.clear()


# ---------------------------------------------------------------------------
# 1 — empty ledger → verify_dispatches.ok=True
# ---------------------------------------------------------------------------

def test_verify_dispatches_ok_with_empty_ledger(tmp_assemble):
    """Empty ledger → dispatch_and_record returns wrap_with_preamble(body)
    byte-identically (no fence injection). verify_dispatches.ok=True.
    Establishes the baseline against which the non-empty case is
    compared in test 2.
    """
    _, rid = tmp_assemble
    out = server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.empty-ledger",
        subagent_type="general-purpose",
    )
    body = h._resolve_prompt_path("iter_emphasis.md").read_text(
        encoding="utf-8"
    )
    expected = wrap_with_preamble(body)
    # Byte-identical — no fence injected.
    assert out == expected
    # No fence sentinel present.
    assert "[PRIOR LEARNINGS" not in out

    audit = server.verify_dispatches(rid)
    assert audit["ok"] is True
    assert audit["total"] == 1
    assert audit["mismatches"] == []


# ---------------------------------------------------------------------------
# 2 — non-empty ledger → verify_dispatches.ok=True (preamble unchanged)
# ---------------------------------------------------------------------------

def test_verify_dispatches_ok_with_non_empty_ledger(tmp_assemble):
    """Populate learnings.jsonl with stage-relevant entries → fence is
    injected into the body region, but preamble stays byte-identical.
    verify_dispatches MUST still return ok=True (the preamble sha is
    what's recorded — body changes are out of scope for the audit).

    This is the regression canary: a one-line bug in the splice
    `replace(_TASK_DELIM, ..., count=1)` boundary would let fence bytes
    bleed into the preamble region and break this test.
    """
    tmp, rid = tmp_assemble
    _seed_ledger(tmp, [
        _entry(
            rule_id="R2",
            category="scope-deviation",
            summary="Plan-stage learning entry — recall this.",
        ),
    ])

    out = server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.with-learnings",
        subagent_type="general-purpose",
    )
    # Fence MUST appear in the wrapped output (proves the splice ran).
    assert "[PRIOR LEARNINGS — 우선 회피]" in out
    assert "(R2) Plan-stage learning entry — recall this." in out

    audit = server.verify_dispatches(rid)
    assert audit["ok"] is True, (
        f"verify_dispatches regression: {audit}"
    )
    assert audit["total"] == 1
    assert audit["mismatches"] == []


# ---------------------------------------------------------------------------
# 3 — preamble sha invariant across ledger states
# ---------------------------------------------------------------------------

def test_preamble_sha_canonical_regardless_of_ledger_state(tmp_assemble):
    """Compute canonical_preamble_sha256() with empty + non-empty ledger
    states. It MUST be identical — the sha covers the preamble file
    only, not the per-dispatch body content.

    Then dispatch under both states and confirm the recorded
    `preamble_sha256` field on each `dispatches.jsonl` row matches the
    canonical value (the audit invariant).
    """
    tmp, rid = tmp_assemble

    # Empty-ledger sha snapshot.
    canonical_empty = canonical_preamble_sha256()
    assert canonical_empty is not None

    # Dispatch with empty ledger.
    server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.empty",
        subagent_type="general-purpose",
    )

    # Seed ledger; canonical sha MUST stay the same (preamble file
    # didn't change).
    _seed_ledger(tmp, [_entry()])
    h._CACHED_PREAMBLE.clear()  # force re-read in case of caching weirdness
    canonical_seeded = canonical_preamble_sha256()
    assert canonical_seeded == canonical_empty, (
        "canonical preamble sha must NOT depend on ledger state — got "
        f"empty={canonical_empty!r} vs seeded={canonical_seeded!r}"
    )

    # Dispatch under non-empty ledger.
    server.dispatch_and_record(
        rid,
        prompt_file="iter_emphasis.md",
        step="step.fenced",
        subagent_type="general-purpose",
    )

    # Both rows MUST record the canonical sha — the splice happens in
    # the body region only.
    log = tmp / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    rows = [
        json.loads(l)
        for l in log.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert len(rows) == 2
    for row in rows:
        assert row["preamble_sha256"] == canonical_empty, (
            "row preamble_sha256 mismatch: "
            f"got {row['preamble_sha256']!r} vs "
            f"canonical {canonical_empty!r}"
        )

    # And verify_dispatches still green.
    audit = server.verify_dispatches(rid)
    assert audit["ok"] is True
    assert audit["total"] == 2
    assert audit["mismatches"] == []
