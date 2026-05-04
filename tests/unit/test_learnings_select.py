"""Unit tests for `server.learnings.select_relevant`.

Spike X Task A1: deterministic top-K selection over an injected ledger.
Ledger I/O is deferred to Task A3 — these tests pass `ledger=[...]` directly.
"""

from server.learnings import (
    STAGE_CATEGORY_PRIORITY,
    MAX_K_DEFAULT,
    select_relevant,
)


def _entry(rule_id, category, ts, summary="x"):
    return {
        "ts": ts,
        "run_id": "run-" + rule_id,
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        "evidence_hash": "0" * 64,
        "evidence": {},
    }


def test_empty_ledger_returns_empty_list():
    assert select_relevant("plan", k=5, ledger=[]) == []


def test_none_ledger_returns_empty_list():
    """A3 will wire disk read; until then None must be a safe no-op."""
    assert select_relevant("plan", k=5, ledger=None) == []


def test_single_entry_returned_as_is():
    e = _entry("R1", "scope-deviation", "2026-05-04T10:00:00Z")
    result = select_relevant("plan", k=5, ledger=[e])
    assert result == [e]


def test_k_caps_result_size():
    ledger = [
        _entry(f"R{i}", "scope-deviation", f"2026-05-04T10:00:0{i}Z")
        for i in range(10)
    ]
    result = select_relevant("plan", k=3, ledger=ledger)
    assert len(result) == 3


def test_k_zero_returns_empty():
    ledger = [_entry("R1", "scope-deviation", "2026-05-04T10:00:00Z")]
    assert select_relevant("plan", k=0, ledger=ledger) == []


def test_default_k_is_5():
    """`MAX_K_DEFAULT = 5` — calling without `k` caps at 5."""
    ledger = [
        _entry(f"R{i}", "scope-deviation", f"2026-05-04T10:00:0{i}Z")
        for i in range(8)
    ]
    result = select_relevant("plan", ledger=ledger)
    assert MAX_K_DEFAULT == 5
    assert len(result) == 5


def test_category_priority_orders_by_stage_map():
    """For `plan`, scope-deviation outranks ac-failure outranks todo-leakage."""
    e_todo = _entry("R1", "todo-leakage", "2026-05-04T10:00:00Z")
    e_ac = _entry("R2", "ac-failure", "2026-05-04T10:00:00Z")
    e_scope = _entry("R3", "scope-deviation", "2026-05-04T10:00:00Z")
    result = select_relevant("plan", k=3, ledger=[e_todo, e_ac, e_scope])
    assert [e["category"] for e in result] == [
        "scope-deviation", "ac-failure", "todo-leakage",
    ]


def test_recency_breaks_ties_within_same_category():
    older = _entry("R1", "scope-deviation", "2026-05-01T00:00:00Z")
    newer = _entry("R2", "scope-deviation", "2026-05-04T00:00:00Z")
    middle = _entry("R3", "scope-deviation", "2026-05-02T00:00:00Z")
    result = select_relevant("plan", k=3, ledger=[older, newer, middle])
    assert [e["rule_id"] for e in result] == ["R2", "R3", "R1"]


def test_rule_id_alpha_breaks_recency_ties():
    """Same category + same ts → rule_id ascending."""
    e_b = _entry("R2", "scope-deviation", "2026-05-04T10:00:00Z")
    e_a = _entry("R1", "scope-deviation", "2026-05-04T10:00:00Z")
    e_c = _entry("R3", "scope-deviation", "2026-05-04T10:00:00Z")
    result = select_relevant("plan", k=3, ledger=[e_b, e_a, e_c])
    assert [e["rule_id"] for e in result] == ["R1", "R2", "R3"]


def test_unknown_category_ranks_below_listed():
    listed = _entry("R1", "scope-deviation", "2026-05-04T10:00:00Z")
    unlisted = _entry("R2", "made-up-cat", "2026-05-04T10:00:00Z")
    result = select_relevant("plan", k=2, ledger=[unlisted, listed])
    assert result[0] == listed
    assert result[1] == unlisted


def test_unknown_stage_falls_back_to_recency_only():
    """Stage not in priority map → category tier collapses, ts/rule_id only."""
    older_scope = _entry("R1", "scope-deviation", "2026-05-01T00:00:00Z")
    newer_misc = _entry("R2", "made-up-cat", "2026-05-04T00:00:00Z")
    result = select_relevant("nonexistent-stage", k=2,
                             ledger=[older_scope, newer_misc])
    # newer wins regardless of category
    assert result[0]["rule_id"] == "R2"
    assert result[1]["rule_id"] == "R1"


def test_stage_priority_map_covers_seven_stages():
    """Spec acceptance: plan/execute/debug/review/verify/ship/meta."""
    expected = {"plan", "execute", "debug", "review", "verify", "ship", "meta"}
    assert set(STAGE_CATEGORY_PRIORITY.keys()) == expected


def test_each_priority_list_is_non_empty():
    for stage, cats in STAGE_CATEGORY_PRIORITY.items():
        assert isinstance(cats, list)
        assert len(cats) > 0, f"{stage} has empty priority list"


def test_debug_stage_prioritizes_ac_failure_first():
    """Debug stage: AC failures are most relevant — verify map shape."""
    e_scope = _entry("R1", "scope-deviation", "2026-05-04T10:00:00Z")
    e_ac = _entry("R2", "ac-failure", "2026-05-04T10:00:00Z")
    result = select_relevant("debug", k=2, ledger=[e_scope, e_ac])
    assert result[0]["category"] == "ac-failure"
    assert result[1]["category"] == "scope-deviation"


def test_explicit_ledger_param_isolates_from_disk():
    """A1 contract: `ledger=[...]` short-circuits any disk read.

    A3 will introduce disk reads; A1 must not yet touch the filesystem.
    Passing an explicit list with a single entry must return that entry
    verbatim regardless of any environment state.
    """
    e = _entry("R1", "scope-deviation", "2026-05-04T10:00:00Z",
               summary="injected-only")
    result = select_relevant("plan", k=5, ledger=[e])
    assert result == [e]
    assert result[0]["summary"] == "injected-only"


def test_result_does_not_mutate_input_ledger():
    """`select_relevant` must be pure — input order preserved post-call."""
    e1 = _entry("R1", "todo-leakage", "2026-05-04T10:00:00Z")
    e2 = _entry("R2", "scope-deviation", "2026-05-04T10:00:00Z")
    ledger = [e1, e2]
    select_relevant("plan", k=2, ledger=ledger)
    # Original list reference unchanged
    assert ledger == [e1, e2]
