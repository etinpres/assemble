"""Spike X C1 — keeper SECURITY.md threat-model invariants.

Mirrors shipper ★ + verifier ★ SECURITY.md structure. Asserts the
seven enumerated threats (T1-T7), six mitigations (M1-M6), the
five Explicit non-goals items, the Audit-evidence trust model
section, and the single-run V4 trust assumption string.
"""
from pathlib import Path


SECURITY = (
    Path.home() / ".claude/skills/assemble/bundled/keeper/SECURITY.md"
)


# ---------------------------------------------------------------------------
# Test 1 — SECURITY.md exists at the canonical location
# ---------------------------------------------------------------------------

def test_security_md_exists():
    """bundled/keeper/SECURITY.md must exist as the keeper threat model."""
    assert SECURITY.exists(), f"keeper SECURITY.md not found at {SECURITY}"
    assert SECURITY.is_file(), f"{SECURITY} exists but is not a regular file"


# ---------------------------------------------------------------------------
# Test 2 — Seven threats T1-T7 enumerated
# ---------------------------------------------------------------------------

def test_seven_threats_enumerated():
    """SECURITY.md body must enumerate T1 through T7 as threat headings."""
    body = SECURITY.read_text()
    for n in range(1, 8):
        token = f"T{n}"
        assert token in body, f"SECURITY.md missing threat token {token!r}"


# ---------------------------------------------------------------------------
# Test 3 — Six mitigations M1-M6 listed
# ---------------------------------------------------------------------------

def test_six_mitigations_listed():
    """SECURITY.md body must list M1 through M6 as mitigation tokens."""
    body = SECURITY.read_text()
    for n in range(1, 7):
        token = f"M{n}"
        assert token in body, f"SECURITY.md missing mitigation token {token!r}"


# ---------------------------------------------------------------------------
# Test 4 — Five Explicit non-goals (section + 5 numbered items)
# ---------------------------------------------------------------------------

def test_five_non_goals():
    """SECURITY.md must declare ## Explicit non-goals section with 5 items."""
    body = SECURITY.read_text()
    assert "## Explicit non-goals" in body, (
        "SECURITY.md missing '## Explicit non-goals' section header"
    )

    # Locate the section body between this heading and the next ## heading
    start = body.index("## Explicit non-goals")
    rest = body[start + len("## Explicit non-goals"):]
    next_section = rest.find("\n## ")
    section_body = rest if next_section == -1 else rest[:next_section]

    # Count numbered list markers 1. through 5. anchored at line start
    for n in range(1, 6):
        marker = f"\n{n}. "
        assert marker in section_body, (
            f"Explicit non-goals section missing item {n}. (looked for {marker!r})"
        )


# ---------------------------------------------------------------------------
# Test 5 — Single-run V4 trust assumption explicitly stated
# ---------------------------------------------------------------------------

def test_single_run_only_string_present():
    """SECURITY.md must document the V4 single-run trust assumption."""
    body = SECURITY.read_text().lower()
    assert ("single-run" in body) or ("single run" in body), (
        "SECURITY.md must document V4 single-run trust assumption "
        "(string 'single-run' or 'single run')"
    )


# ---------------------------------------------------------------------------
# Test 6 — Audit-evidence trust model section present
# ---------------------------------------------------------------------------

def test_audit_evidence_trust_model_section():
    """SECURITY.md must declare ## Audit-evidence trust model section."""
    body = SECURITY.read_text()
    assert "## Audit-evidence trust model" in body, (
        "SECURITY.md missing '## Audit-evidence trust model' section header"
    )
