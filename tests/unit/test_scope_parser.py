"""Tests for server.scope_parser.parse_scope_md.

8 test cases covering the full grammar spec:
  T1  ascii_simple       — standard ASCII allow + deny + completion
  T2  korean_strict      — strict grammar Korean path + note
  T3  korean_freeform_deny — B-11 reproducer: freeform Korean deny entry
  T4  missing_allow      — no ## Allow list header
  T5  empty_completion   — present fence but empty body
  T6  em_dash_variants   — en-dash and double-hyphen both rejected
  T7  note_less          — backtick-wrapped and plain note-less bullets
  T8  mixed              — 4 valid + 2 freeform Korean deny entries
"""

from pathlib import Path

import pytest

from server.scope_parser import parse_scope_md

# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "scope_md"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T1 — ascii_simple: normal happy-path with allow + deny + completion
# ---------------------------------------------------------------------------

def test_t1_ascii_simple_parses_entries():
    result = parse_scope_md(_load("ascii_simple.md"))
    assert result["errors"] == []
    # Allow list: 2 entries
    allow = result["allow"]
    assert len(allow) == 2
    assert allow[0]["path"] == "server/scope_parser.py"
    assert allow[0]["note"] == "new file: deterministic parser"
    assert allow[1]["path"] == "server/__init__.py"
    assert allow[1]["note"] == "additive export only"
    # Deny list: 1 entry
    deny = result["deny"]
    assert len(deny) == 1
    assert deny[0]["path"] == "server/harness.py"
    # Completion captured
    assert result["completion"] == "pytest tests/unit/test_scope_parser.py -v"
    # task_summary
    assert result["task_summary"] == "Add deterministic SCOPE.md parser"


# ---------------------------------------------------------------------------
# T2 — korean_strict: strict grammar Korean path + note
# ---------------------------------------------------------------------------

def test_t2_korean_strict_parses_korean():
    result = parse_scope_md(_load("korean_strict.md"))
    assert result["errors"] == []
    allow = result["allow"]
    assert len(allow) == 1
    # Path preserved verbatim including Korean characters
    assert allow[0]["path"] == "path/with/한글.md"
    assert allow[0]["note"] == "한글 노트"


# ---------------------------------------------------------------------------
# T3 — korean_freeform_deny: B-11 reproducer
# ---------------------------------------------------------------------------

def test_t3_korean_freeform_deny_emits_grammar_error():
    result = parse_scope_md(_load("korean_freeform_deny.md"))
    assert "deny-entry-0-grammar" in result["errors"]
    # Entry must NOT be stored as a malformed path
    assert result["deny"] == []
    # Allow list still parses correctly
    assert len(result["allow"]) == 1
    assert result["allow"][0]["path"] == "server/scope_parser.py"


# ---------------------------------------------------------------------------
# T4 — missing_allow: no ## Allow list header
# ---------------------------------------------------------------------------

def test_t4_missing_allow_emits_error():
    result = parse_scope_md(_load("missing_allow.md"))
    assert "allow-section-missing" in result["errors"]
    assert result["allow"] == []
    # Deny section is optional and should still parse normally if present
    # (missing_allow.md has a deny entry)
    assert len(result["deny"]) == 1
    assert result["deny"][0]["path"] == "server/harness.py"


# ---------------------------------------------------------------------------
# T5 — empty_completion: fence present but body empty
# ---------------------------------------------------------------------------

def test_t5_empty_completion_emits_error():
    result = parse_scope_md(_load("empty_completion.md"))
    assert "completion-empty" in result["errors"]
    assert result["completion"] == ""


# ---------------------------------------------------------------------------
# T6 — em_dash_variants: en-dash and double-hyphen rejected
# ---------------------------------------------------------------------------

def test_t6_em_dash_variants_rejected():
    result = parse_scope_md(_load("em_dash_variants.md"))
    errors = result["errors"]
    # Both bullets (index 0 and index 1) should fail grammar
    assert "allow-entry-0-grammar" in errors
    assert "allow-entry-1-grammar" in errors
    # Neither entry should be stored
    assert result["allow"] == []


# ---------------------------------------------------------------------------
# T7 — note_less: bullets with no em-dash separator
# ---------------------------------------------------------------------------

def test_t7_note_less_parses_with_empty_note():
    result = parse_scope_md(_load("note_less.md"))
    assert result["errors"] == []
    allow = result["allow"]
    assert len(allow) == 2
    # Both entries should have empty note
    assert allow[0]["path"] == "server/scope_parser.py"
    assert allow[0]["note"] == ""
    assert allow[1]["path"] == "server/__init__.py"
    assert allow[1]["note"] == ""


# ---------------------------------------------------------------------------
# T8 — mixed: 4 valid entries + 2 freeform Korean deny entries
# ---------------------------------------------------------------------------

def test_t8_mixed_four_valid_two_errors():
    result = parse_scope_md(_load("mixed.md"))
    errors = result["errors"]
    # 2 allow entries stored
    assert len(result["allow"]) == 2
    # 2 valid deny entries stored (index 0 and 2 — the freeform ones at 1 and 3 are skipped)
    assert len(result["deny"]) == 2
    assert result["deny"][0]["path"] == "server/harness.py"
    assert result["deny"][1]["path"] == "server/inventory.py"
    # 2 deny grammar errors (at index 1 and 3)
    assert "deny-entry-1-grammar" in errors
    assert "deny-entry-3-grammar" in errors
    # No other errors
    assert "allow-section-missing" not in errors
    assert "completion-empty" not in errors


# ---------------------------------------------------------------------------
# Bonus: scope-missing for empty input
# ---------------------------------------------------------------------------

def test_empty_text_returns_scope_missing():
    result = parse_scope_md("")
    assert result["errors"] == ["scope-missing"]
    assert result["task_summary"] == ""
    assert result["allow"] == []
    assert result["deny"] == []
    assert result["completion"] == ""


def test_whitespace_only_returns_scope_missing():
    result = parse_scope_md("   \n\t\n  ")
    assert result["errors"] == ["scope-missing"]
