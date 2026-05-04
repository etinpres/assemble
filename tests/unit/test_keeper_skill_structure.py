"""Spike X B1 — keeper SKILL.md frontmatter + body invariants.

Mirrors Spike VIII verifier / Spike IX shipper SKILL.md structure tests.
Asserts frontmatter, the 4-step subagent matrix, anti-bypass section,
3-outcome verdict block, and the orchestrator-only iteration helper.
"""
from pathlib import Path


SKILL = (
    Path.home() / ".claude/skills/assemble/bundled/keeper/SKILL.md"
)


# The 4 canonical subagent prompt filenames (B2-B5)
SUBAGENT_PROMPTS = [
    "keeper_audit_step1.md",
    "keeper_extract_step2.md",
    "keeper_summarize_step3.md",
    "keeper_ledger_step4.md",
]

# The orchestrator-only helper (B6) — must NOT be conflated with subagent prompts
ORCHESTRATOR_HELPER = "keeper_iter_revisit.md"


# ---------------------------------------------------------------------------
# Test 1 — SKILL.md exists at the canonical location
# ---------------------------------------------------------------------------

def test_skill_md_exists():
    """bundled/keeper/SKILL.md must exist as the user-facing skill description."""
    assert SKILL.exists(), f"keeper SKILL.md not found at {SKILL}"
    assert SKILL.is_file(), f"{SKILL} exists but is not a regular file"


# ---------------------------------------------------------------------------
# Test 2 — frontmatter contains name='keeper' and stages=['meta']
# ---------------------------------------------------------------------------

def test_frontmatter_name_and_stage():
    """Frontmatter must declare name='keeper' and stages=['meta']."""
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---"), "SKILL.md must begin with YAML frontmatter delimiter"
    end = text.index("---", 3)
    fm = text[: end + 3]
    assert 'name: "keeper"' in fm, "frontmatter must declare name: \"keeper\""
    assert 'stages: ["meta"]' in fm, "frontmatter must declare stages: [\"meta\"]"


# ---------------------------------------------------------------------------
# Test 3 — body contains all 4 subagent prompt filenames
# ---------------------------------------------------------------------------

def test_subagent_matrix_lists_4_step_prompts():
    """Body must reference all 4 canonical keeper subagent prompt filenames."""
    text = SKILL.read_text(encoding="utf-8")
    for name in SUBAGENT_PROMPTS:
        assert name in text, (
            f"keeper subagent prompt filename missing from SKILL.md body: {name!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — CRITICAL anti-bypass section enumerates the allowlist
# ---------------------------------------------------------------------------

def test_critical_anti_bypass_section_present():
    """Body must contain the §CRITICAL — orchestrator-only enforcement section
    enumerating the prompt allowlist (Spike VIII inheritance)."""
    text = SKILL.read_text(encoding="utf-8")
    assert "## CRITICAL — orchestrator-only enforcement" in text, (
        "Body must contain '## CRITICAL — orchestrator-only enforcement' section"
    )
    # Allowlist must reference ALLOWED_PROMPT_FILES + halt-on-bypass language
    assert "ALLOWED_PROMPT_FILES" in text, (
        "Body must mention ALLOWED_PROMPT_FILES in the allowlist enumeration"
    )
    assert "harness raises and halts" in text or "raises and halts" in text, (
        "Body must spell out the bypass-halt invariant"
    )


# ---------------------------------------------------------------------------
# Test 5 — verdict block lists all 3 outcomes
# ---------------------------------------------------------------------------

def test_verdict_block_3_outcomes():
    """Body must enumerate the 3 deterministic verdicts: audit-clean,
    audit-flagged, audit-skipped."""
    text = SKILL.read_text(encoding="utf-8")
    for verdict in ("audit-clean", "audit-flagged", "audit-skipped"):
        assert verdict in text, f"verdict outcome missing from SKILL.md body: {verdict!r}"


# ---------------------------------------------------------------------------
# Test 6 — orchestrator helper is named correctly + distinct from subagent prompts
# ---------------------------------------------------------------------------

def test_orchestrator_helper_named_correctly():
    """Body must mention keeper_iter_revisit.md (the orchestrator-only iteration
    helper) AND distinguish it from the 4 subagent prompts."""
    text = SKILL.read_text(encoding="utf-8")
    assert ORCHESTRATOR_HELPER in text, (
        f"orchestrator helper {ORCHESTRATOR_HELPER!r} missing from SKILL.md body"
    )
    # Distinctness: must spell out it is NOT in the subagent allowlist
    assert "ORCHESTRATOR_ONLY_PROMPTS" in text or "NOT in the allowlist" in text, (
        "Body must explicitly mark keeper_iter_revisit.md as orchestrator-only "
        "(not in the subagent allowlist)"
    )
    # And must NOT have the helper appear under the same heading as the 4 subagent prompts
    # (cheap proxy: the helper lives under prompts/orchestrator/, mention that path)
    assert "prompts/orchestrator/" in text, (
        "Body must locate keeper_iter_revisit.md under prompts/orchestrator/ "
        "to keep it distinct from subagent prompts"
    )
