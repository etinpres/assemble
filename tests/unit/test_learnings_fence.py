"""Unit tests for `server.learnings.render_learnings_fence`.

Spike X Task A1: render the `[PRIOR LEARNINGS — 우선 회피]` body-prefix fence.
Pre-render guards: newline collapse, 200-char truncation, empty → empty string.
"""

from server.learnings import (
    MAX_SUMMARY_CHARS,
    render_learnings_fence,
)


def _entry(rule_id, summary):
    return {
        "ts": "2026-05-04T10:00:00Z",
        "run_id": "r-" + rule_id,
        "rule_id": rule_id,
        "category": "scope-deviation",
        "summary": summary,
        "evidence_hash": "0" * 64,
        "evidence": {},
    }


def test_empty_entries_returns_empty_string():
    """No fence at all when there are no learnings — keeps prompt byte-identical."""
    assert render_learnings_fence([]) == ""


def test_single_entry_renders_with_open_close_markers():
    fence = render_learnings_fence([_entry("R2", "edited deny path")])
    assert fence.startswith("[PRIOR LEARNINGS — 우선 회피]\n")
    assert fence.endswith("\n[/PRIOR LEARNINGS]")
    assert "1. (R2) edited deny path" in fence


def test_multi_entry_numbers_sequentially_from_1():
    entries = [
        _entry("R1", "first"),
        _entry("R2", "second"),
        _entry("R3", "third"),
    ]
    fence = render_learnings_fence(entries)
    assert "1. (R1) first" in fence
    assert "2. (R2) second" in fence
    assert "3. (R3) third" in fence
    # numbers are in order — "2." appears after "1."
    assert fence.index("1.") < fence.index("2.") < fence.index("3.")


def test_summary_longer_than_200_truncated_with_ellipsis():
    long_summary = "A" * 250
    fence = render_learnings_fence([_entry("R1", long_summary)])
    # Visible summary: 197 'A' chars + "…" (1 char) = 198 chars total,
    # comfortably under the 200-char cap and explicitly marked as truncated.
    line = [l for l in fence.splitlines() if l.startswith("1. (R1)")][0]
    summary_part = line[len("1. (R1) "):]
    assert summary_part.endswith("…")
    assert len(summary_part) <= MAX_SUMMARY_CHARS
    assert summary_part == "A" * (MAX_SUMMARY_CHARS - 3) + "…"


def test_summary_at_exactly_200_chars_is_not_truncated():
    """Boundary case: 200 chars must pass through unchanged."""
    summary = "X" * MAX_SUMMARY_CHARS
    fence = render_learnings_fence([_entry("R1", summary)])
    assert summary in fence
    assert "…" not in fence


def test_newlines_in_summary_collapsed_to_single_space():
    summary = "first line\nsecond line\nthird"
    fence = render_learnings_fence([_entry("R1", summary)])
    line = [l for l in fence.splitlines() if l.startswith("1. (R1)")][0]
    assert "\n" not in line[len("1. "):]  # rest of line, no embedded newline
    assert "first line second line third" in line


def test_carriage_return_newline_collapsed_too():
    """Windows-style CRLF must also collapse to a single space."""
    summary = "alpha\r\nbeta"
    fence = render_learnings_fence([_entry("R1", summary)])
    assert "alpha beta" in fence
    assert "\r" not in fence


def test_korean_and_english_mix_renders():
    """Spike X is Korean-led; fence header itself is Korean. Mixed summaries
    must render unchanged (no encoding loss, no truncation surprise)."""
    summary = "scope deviation: src/auth.py 수정했지만 deny 패턴이었음 — 회피"
    fence = render_learnings_fence([_entry("R7", summary)])
    assert summary in fence
    assert "[PRIOR LEARNINGS — 우선 회피]" in fence


def test_fence_format_full_block():
    """Spec acceptance — exact end-to-end shape with two entries."""
    entries = [
        _entry("R2", "Edited src/auth.py despite deny pattern auth/* — fix scope"),
        _entry("R3", "Verify exited 1 — check pytest path"),
    ]
    fence = render_learnings_fence(entries)
    expected = (
        "[PRIOR LEARNINGS — 우선 회피]\n"
        "1. (R2) Edited src/auth.py despite deny pattern auth/* — fix scope\n"
        "2. (R3) Verify exited 1 — check pytest path\n"
        "[/PRIOR LEARNINGS]"
    )
    assert fence == expected
