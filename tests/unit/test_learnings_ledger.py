"""Unit tests for `server.learnings` ledger I/O + `prune_ledger`.

Spike X Task A3: disk-backed read/write helpers + the deterministic prune
pipeline (TTL → skiplist → dedup → FIFO cap). Filesystem isolation via the
`tmp_path` fixture and `ASSEMBLE_HOME` monkeypatching — these tests must
never touch the real `~/.claude/channels/assemble/` directory.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from server.learnings import (
    learnings_path,
    learnings_skip_path,
    prune_ledger,
    read_ledger,
    read_skiplist,
    write_ledger,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _entry(rule_id, ts, evidence_hash=None, category="scope-deviation",
           summary="x", run_id=None):
    return {
        "ts": ts,
        "run_id": run_id or ("run-" + rule_id),
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        "evidence_hash": evidence_hash if evidence_hash is not None else rule_id * 8,
        "evidence": {},
    }


def _set_assemble_home(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))


# ---------------------------------------------------------------------------
# 1-2: path helpers honor ASSEMBLE_HOME
# ---------------------------------------------------------------------------

def test_learnings_path_honors_assemble_home(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    expected = tmp_path / ".claude/channels/assemble/learnings.jsonl"
    assert learnings_path() == expected


def test_learnings_skip_path_honors_assemble_home(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    expected = tmp_path / ".claude/channels/assemble/learnings.skip"
    assert learnings_skip_path() == expected


# ---------------------------------------------------------------------------
# 3-6: read_ledger
# ---------------------------------------------------------------------------

def test_read_ledger_missing_file_returns_empty(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    assert read_ledger() == []


def test_read_ledger_round_trip_single_entry(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    e = _entry("R1", "2026-05-04T10:00:00+00:00")
    write_ledger([e])
    assert read_ledger() == [e]


def test_read_ledger_skips_malformed_line(monkeypatch, tmp_path, capsys):
    _set_assemble_home(monkeypatch, tmp_path)
    target = learnings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    valid = _entry("R1", "2026-05-04T10:00:00+00:00")
    target.write_text(
        json.dumps(valid) + "\n"
        + "{not valid json\n"
        + json.dumps(_entry("R2", "2026-05-04T11:00:00+00:00")) + "\n",
        encoding="utf-8",
    )
    result = read_ledger()
    assert len(result) == 2
    assert result[0]["rule_id"] == "R1"
    assert result[1]["rule_id"] == "R2"
    captured = capsys.readouterr()
    assert "skipped malformed line 2" in captured.err


def test_read_ledger_skips_empty_lines(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    target = learnings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    e1 = _entry("R1", "2026-05-04T10:00:00+00:00")
    e2 = _entry("R2", "2026-05-04T11:00:00+00:00")
    target.write_text(
        "\n" + json.dumps(e1) + "\n\n   \n" + json.dumps(e2) + "\n",
        encoding="utf-8",
    )
    result = read_ledger()
    assert result == [e1, e2]


# ---------------------------------------------------------------------------
# 7-10: read_skiplist
# ---------------------------------------------------------------------------

def test_read_skiplist_missing_file_returns_empty_set(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    assert read_skiplist() == set()


def test_read_skiplist_parses_one_hash_per_line(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    target = learnings_skip_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("aaa\nbbb\nccc\n", encoding="utf-8")
    assert read_skiplist() == {"aaa", "bbb", "ccc"}


def test_read_skiplist_skips_comment_lines(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    target = learnings_skip_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# top comment\naaa\n# inline comment\nbbb\n",
        encoding="utf-8",
    )
    assert read_skiplist() == {"aaa", "bbb"}


def test_read_skiplist_skips_blank_lines(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    target = learnings_skip_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n   \naaa\n\nbbb\n   \n", encoding="utf-8")
    assert read_skiplist() == {"aaa", "bbb"}


# ---------------------------------------------------------------------------
# 11-13: write_ledger
# ---------------------------------------------------------------------------

def test_write_ledger_creates_parent_dir(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    parent = tmp_path / ".claude/channels/assemble"
    assert not parent.exists()
    write_ledger([_entry("R1", "2026-05-04T10:00:00+00:00")])
    assert parent.is_dir()
    assert learnings_path().is_file()


def test_write_ledger_atomic_no_stray_tmp_files(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    write_ledger([_entry("R1", "2026-05-04T10:00:00+00:00")])
    parent = learnings_path().parent
    leftovers = [p.name for p in parent.iterdir()
                 if p.name != "learnings.jsonl"]
    assert leftovers == [], f"unexpected leftover: {leftovers}"


def test_write_ledger_preserves_korean_characters(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    e = _entry("R1", "2026-05-04T10:00:00+00:00",
               summary="가위바위보 — Korean summary 한글")
    write_ledger([e])
    raw = learnings_path().read_text(encoding="utf-8")
    assert "가위바위보" in raw
    assert "한글" in raw
    # ensure_ascii=False ⇒ raw bytes carry the literal codepoints, not \uXXXX.
    assert "\\uac00" not in raw
    # round-trip integrity
    assert read_ledger()[0]["summary"] == e["summary"]


def test_write_ledger_materializes_generator_input(monkeypatch, tmp_path):
    """Regression anchor: write_ledger must accept a generator and write
    every yielded entry to disk. This pins the `entries = list(entries)`
    materialization line at function entry — without it, future refactors
    that iterate `entries` more than once would silently lose data on
    generator inputs.
    """
    _set_assemble_home(monkeypatch, tmp_path)
    e1 = _entry("R1", "2026-05-04T10:00:00+00:00", evidence_hash="g1")
    e2 = _entry("R2", "2026-05-04T11:00:00+00:00", evidence_hash="g2")

    def _gen():
        yield e1
        yield e2

    write_ledger(_gen())
    result = read_ledger()
    assert result == [e1, e2]


# ---------------------------------------------------------------------------
# 14-21: prune_ledger
# ---------------------------------------------------------------------------

NOW_ANCHOR = "2026-05-04T12:00:00+00:00"


def test_prune_ttl_drops_entries_older_than_30_days():
    fresh = _entry("R1", "2026-05-01T00:00:00+00:00", evidence_hash="hf1")
    stale = _entry("R2", "2026-03-01T00:00:00+00:00", evidence_hash="hs1")
    result = prune_ledger([fresh, stale], now=NOW_ANCHOR)
    assert fresh in result
    assert stale not in result


def test_prune_ttl_keeps_entries_with_malformed_ts():
    """Spec: malformed `ts` → KEEP (loud > silent)."""
    bad = _entry("R1", "not-an-iso-timestamp", evidence_hash="hbad1")
    bad2 = {**_entry("R2", "irrelevant", evidence_hash="hbad2"), "ts": None}
    result = prune_ledger([bad, bad2], now=NOW_ANCHOR)
    assert bad in result
    assert bad2 in result


def test_prune_skiplist_drops_by_evidence_hash():
    keep = _entry("R1", "2026-05-04T10:00:00+00:00", evidence_hash="aaa")
    drop = _entry("R2", "2026-05-04T11:00:00+00:00", evidence_hash="bbb")
    result = prune_ledger([keep, drop], now=NOW_ANCHOR, skiplist={"bbb"})
    assert keep in result
    assert drop not in result


def test_prune_dedup_keeps_most_recent_ts_per_hash():
    older = _entry("R1", "2026-05-03T10:00:00+00:00", evidence_hash="dup")
    newer = _entry("R2", "2026-05-04T10:00:00+00:00", evidence_hash="dup")
    other = _entry("R3", "2026-05-04T11:00:00+00:00", evidence_hash="other")
    result = prune_ledger([older, newer, other], now=NOW_ANCHOR)
    assert newer in result
    assert older not in result
    assert other in result
    assert len(result) == 2


def test_prune_fifo_cap_drops_oldest_first():
    entries = [
        _entry(f"R{i}", f"2026-05-04T1{i}:00:00+00:00",
               evidence_hash=f"h{i}")
        for i in range(5)
    ]
    result = prune_ledger(entries, now=NOW_ANCHOR, cap=3)
    rule_ids = {e["rule_id"] for e in result}
    # Oldest two (R0, R1) get evicted; R2/R3/R4 survive.
    assert rule_ids == {"R2", "R3", "R4"}
    assert len(result) == 3


def test_prune_rule_order_ttl_drops_before_dedup_can_save():
    """If a duplicate's *only* recent representative is TTL-stale, the
    dedup step never sees it — so the older one survives via dedup-of-one.
    Confirms TTL runs before dedup."""
    stale_recent = _entry("R1", "2026-03-01T00:00:00+00:00",
                          evidence_hash="dup")  # would be "newest" but stale
    fresh_older = _entry("R2", "2026-05-01T00:00:00+00:00",
                         evidence_hash="dup")  # survives TTL
    result = prune_ledger([stale_recent, fresh_older], now=NOW_ANCHOR)
    # Stale entry got dropped by TTL; fresh_older survives dedup as the
    # only remaining member of bucket "dup".
    assert stale_recent not in result
    assert fresh_older in result
    assert len(result) == 1


def test_prune_does_not_mutate_input():
    entries = [
        _entry("R1", "2026-05-04T10:00:00+00:00", evidence_hash="a"),
        _entry("R2", "2026-03-01T00:00:00+00:00", evidence_hash="b"),
    ]
    snapshot = [dict(e) for e in entries]
    prune_ledger(entries, now=NOW_ANCHOR, skiplist={"a"})
    assert entries == snapshot


def test_prune_accepts_now_as_datetime_or_string():
    fresh = _entry("R1", "2026-05-01T00:00:00+00:00", evidence_hash="a")
    stale = _entry("R2", "2026-03-01T00:00:00+00:00", evidence_hash="b")
    as_string = prune_ledger([fresh, stale], now=NOW_ANCHOR)
    as_dt = prune_ledger(
        [fresh, stale],
        now=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert as_string == as_dt
    # Naive datetime should also work — we coerce to UTC internally.
    as_naive = prune_ledger(
        [fresh, stale],
        now=datetime(2026, 5, 4, 12, 0, 0),
    )
    assert as_naive == as_dt


# ---------------------------------------------------------------------------
# Bonus coverage — atomic-overwrite-doesn't-clobber + dedup tie-break
# ---------------------------------------------------------------------------

def test_write_ledger_overwrites_previous_contents(monkeypatch, tmp_path):
    _set_assemble_home(monkeypatch, tmp_path)
    write_ledger([_entry("R1", "2026-05-04T10:00:00+00:00")])
    write_ledger([_entry("R2", "2026-05-04T11:00:00+00:00"),
                  _entry("R3", "2026-05-04T12:00:00+00:00")])
    result = read_ledger()
    assert [e["rule_id"] for e in result] == ["R2", "R3"]


def test_prune_dedup_tie_keeps_first_occurrence():
    """Stable on tied ts — first entry to claim the hash wins."""
    first = _entry("R1", "2026-05-04T10:00:00+00:00", evidence_hash="dup")
    second = _entry("R2", "2026-05-04T10:00:00+00:00", evidence_hash="dup")
    result = prune_ledger([first, second], now=NOW_ANCHOR)
    assert result == [first]
