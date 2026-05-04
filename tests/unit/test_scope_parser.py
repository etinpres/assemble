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


# ---------------------------------------------------------------------------
# I1 — unclosed fence: opening ``` but no closing ```
# ---------------------------------------------------------------------------

def test_unclosed_fence_emits_error():
    """Opening ``` fence with no closing ``` must emit completion-fence-unclosed.

    Option A behavior: captured content is preserved as a warning; the
    downstream verifier Step 1 (500-char cap + len > 0 check) decides what to
    do with it.
    """
    result = parse_scope_md(_load("unclosed_fence.md"))
    # Error label must be present
    assert "completion-fence-unclosed" in result["errors"]
    # Option A: captured content is kept (warning, not destructive truncation)
    assert result["completion"] == "echo hello\nthis should not be captured"


# ---------------------------------------------------------------------------
# I2 — ## inside fenced block at column 0 truncates section (known limitation)
# ---------------------------------------------------------------------------

def test_completion_double_hash_inside_fence_truncates():
    """KNOWN LIMITATION: _NEXT_SECTION_RE fires on ## at column 0 inside a fence.

    The section terminator scan is fence-unaware. Any ``##`` line at column 0
    inside a bash heredoc terminates _extract_section_text before the closing
    ``` is reached. This leaves the fence unclosed, which now correctly emits
    completion-fence-unclosed as a side-effect.

    For B-13 the 500-char single-line completions cannot trigger this; future
    SCOPE authors using heredoc-style multi-line completions need to indent
    ``##`` lines or escape them.
    """
    result = parse_scope_md(_load("double_hash_inside_fence.md"))
    # Only the content before the ## line is captured (known truncation)
    assert result["completion"] == "cat <<EOF"
    # The unclosed-fence error surfaces because ## terminated the section
    # before the closing ``` was seen
    assert "completion-fence-unclosed" in result["errors"]


# ---------------------------------------------------------------------------
# Spike IX A1 — `build` + `tag_prefix` section recognition (additive)
# ---------------------------------------------------------------------------

def test_spike_ix_a1_with_build_section_captures_command():
    """`## Build` section with single-backtick-wrapped command → build = '<cmd>'."""
    result = parse_scope_md(_load("with_build.md"))
    assert result["build"] == "npm run build"
    # Default tag_prefix when section missing
    assert result["tag_prefix"] == "v"
    # No spurious errors introduced by additive parsing
    assert "build-too-long" not in result["errors"]
    assert "build-malformed" not in result["errors"]
    assert "tag-prefix-too-long" not in result["errors"]


def test_spike_ix_a1_without_build_section_defaults_to_none():
    """SCOPE.md without `## Build` section → build = None (no error)."""
    result = parse_scope_md(_load("ascii_simple.md"))
    assert result["build"] is None
    assert result["tag_prefix"] == "v"
    # Existing behavior unchanged
    assert result["errors"] == []
    assert "build-too-long" not in result["errors"]


def test_spike_ix_a1_build_too_long_emits_error_and_nullifies():
    """build > 500 chars → 'build-too-long' error + build = None."""
    result = parse_scope_md(_load("build_too_long.md"))
    assert "build-too-long" in result["errors"]
    assert result["build"] is None


def test_spike_ix_a1_with_tag_prefix_section_captures_string():
    """`## Tag prefix` section with backtick-wrapped string → tag_prefix = '<str>'."""
    result = parse_scope_md(_load("with_tag_prefix.md"))
    assert result["tag_prefix"] == "release-"
    # build defaults to None when only tag_prefix declared
    assert result["build"] is None
    assert "tag-prefix-too-long" not in result["errors"]


def test_spike_ix_a1_default_tag_prefix_when_section_missing():
    """SCOPE.md without `## Tag prefix` section → tag_prefix = 'v' (default)."""
    result = parse_scope_md(_load("ascii_simple.md"))
    assert result["tag_prefix"] == "v"


def test_spike_ix_a1_tag_prefix_too_long_emits_error_and_defaults():
    """tag_prefix > 10 chars → 'tag-prefix-too-long' error + tag_prefix = 'v'."""
    result = parse_scope_md(_load("tag_prefix_too_long.md"))
    assert "tag-prefix-too-long" in result["errors"]
    # Falls back to default when over-length
    assert result["tag_prefix"] == "v"


def test_spike_ix_a1_both_sections_present_parse_independently():
    """Both `## Build` and `## Tag prefix` present → both fields set."""
    result = parse_scope_md(_load("with_build_and_tag_prefix.md"))
    assert result["build"] == "python -m build"
    assert result["tag_prefix"] == "v."
    # No errors for either field
    assert "build-too-long" not in result["errors"]
    assert "build-malformed" not in result["errors"]
    assert "tag-prefix-too-long" not in result["errors"]


def test_spike_ix_a1_build_malformed_emits_error():
    """`## Build` section content not single-backtick-wrapped → 'build-malformed'."""
    result = parse_scope_md(_load("build_malformed.md"))
    assert "build-malformed" in result["errors"]
    assert result["build"] is None


def test_spike_ix_a1_tag_prefix_malformed_emits_error_and_defaults():
    """`## Tag prefix` content not single-backtick-wrapped → 'tag-prefix-malformed' + default 'v'."""
    result = parse_scope_md(_load("tag_prefix_malformed.md"))
    assert "tag-prefix-malformed" in result["errors"]
    assert result["tag_prefix"] == "v"


def test_spike_ix_a1_lowercase_section_headers_recognized():
    """`## build` (lowercase) round-trips identically to `## Build` per IGNORECASE convention."""
    text = (
        "# SCOPE\n\n## Allow list\n\n- `f.py` — note\n\n"
        "## Completion criterion\n\n```bash\necho ok\n```\n\n"
        "## build\n\n`npm run build`\n\n## tag prefix\n\n`release-`\n"
    )
    result = parse_scope_md(text)
    assert result["build"] == "npm run build"
    assert result["tag_prefix"] == "release-"
    assert "build-malformed" not in result["errors"]
    assert "tag-prefix-malformed" not in result["errors"]


def test_spike_ix_a1_empty_text_includes_default_build_and_tag_prefix():
    """Empty text → still emits 'scope-missing' but exposes default fields."""
    result = parse_scope_md("")
    assert result["build"] is None
    assert result["tag_prefix"] == "v"
    assert result["errors"] == ["scope-missing"]


# ---------------------------------------------------------------------------
# Spike X A2 — cross-bundle consumer documentation anchor
# ---------------------------------------------------------------------------

def test_spike_x_a2_module_docstring_lists_cross_bundle_consumers():
    """Module docstring must enumerate every cross-bundle consumer of
    ``parsed_scope.json`` so future schema changes notice all downstream
    bundles. Pure documentation regression anchor — asserts specific
    consumer names, not the entire docstring text.
    """
    import server.scope_parser as scope_parser

    doc = scope_parser.__doc__ or ""
    assert "Cross-bundle consumers" in doc, (
        "scope_parser module docstring must contain a 'Cross-bundle consumers' "
        "section listing every bundle that reads parsed_scope.json"
    )
    assert "reviewer" in doc, "reviewer ★ must be listed as a cross-bundle consumer"
    assert "keeper" in doc, (
        "keeper ★ (Spike X) must be listed — Rule R2 reads allow/deny lists"
    )
