"""Spike VIII A7 — verifier SKILL.md full body + iter revisit helper invariants."""
from pathlib import Path

import yaml

from server.harness import ALLOWED_PROMPT_FILES

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SKILL = ASSEMBLE / "bundled/verifier/SKILL.md"
ITER_REVISIT = ASSEMBLE / "bundled/verifier/prompts/orchestrator/verifier_iter_revisit.md"

# Canonical H2 sections expected in the body (in order)
EXPECTED_H2 = [
    "## When to invoke",
    "## Inputs",
    "## Artifacts",
    "## Verdict logic (deterministic)",
    "## CRITICAL — orchestrator-only enforcement",
    "## Step-by-step workflow",
    "## Iteration audit invariant",
    "## Sub-agent matrix",
    "## Security",
    "## Identity guards",
]

# The 4 canonical subagent prompt filenames
SUBAGENT_PROMPTS = [
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
]


def _read_frontmatter(text: str) -> tuple[str, str]:
    """Split SKILL.md text into frontmatter block (with delimiters) and body."""
    if not text.startswith("---"):
        return "", text
    end = text.index("---", 3)
    frontmatter = text[: end + 3]
    body = text[end + 3 :]
    return frontmatter, body


# ---------------------------------------------------------------------------
# Test 1 — frontmatter contains expected fields (A1 set, must be untouched)
# ---------------------------------------------------------------------------

def test_skill_md_frontmatter_unchanged():
    """Frontmatter must contain name='verifier', description field, stages=['verify']."""
    text = SKILL.read_text()
    fm, _ = _read_frontmatter(text)
    assert 'name: "verifier"' in fm, "name field missing from frontmatter"
    assert "description:" in fm, "description field missing from frontmatter"
    assert 'stages: ["verify"]' in fm, "stages field missing or changed from frontmatter"


# ---------------------------------------------------------------------------
# Test 2 — YAML strict-load passes (Spike VI Phase A invariant)
# ---------------------------------------------------------------------------

def test_skill_md_yaml_strict_load():
    """YAML frontmatter must strict-load without errors."""
    text = SKILL.read_text()
    fm, _ = _read_frontmatter(text)
    # Strip the --- delimiters before loading
    inner = fm.strip().strip("---").strip()
    parsed = yaml.safe_load(inner)
    assert isinstance(parsed, dict), "Frontmatter did not parse to a dict"
    assert parsed.get("name") == "verifier"
    assert parsed.get("stages") == ["verify"]


# ---------------------------------------------------------------------------
# Test 3 — body contains all canonical H2 sections in order
# ---------------------------------------------------------------------------

def test_skill_md_has_all_h2_sections():
    """Body must contain all 10 canonical H2 headings in the correct order."""
    text = SKILL.read_text()
    _, body = _read_frontmatter(text)

    positions = []
    for section in EXPECTED_H2:
        idx = body.find(section)
        assert idx != -1, f"Missing H2 section: {section!r}"
        positions.append(idx)

    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1], (
            f"H2 section order violated: {EXPECTED_H2[i]!r} should come before "
            f"{EXPECTED_H2[i + 1]!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — SECURITY.md is referenced in the body
# ---------------------------------------------------------------------------

def test_skill_md_references_security_md():
    """Body must reference SECURITY.md (verifier Security section links to it)."""
    text = SKILL.read_text()
    assert "SECURITY.md" in text, "SECURITY.md link missing from SKILL.md body"


# ---------------------------------------------------------------------------
# Test 5 — all 4 subagent prompt filenames appear in the body
# ---------------------------------------------------------------------------

def test_skill_md_lists_4_subagent_prompts():
    """Body must reference all 4 canonical verifier subagent prompt filenames."""
    text = SKILL.read_text()
    for name in SUBAGENT_PROMPTS:
        assert name in text, f"Subagent prompt filename missing from SKILL.md: {name!r}"


# ---------------------------------------------------------------------------
# Test 6 — verifier_iter_revisit.md helper exists
# ---------------------------------------------------------------------------

def test_iter_revisit_helper_exists():
    """verifier_iter_revisit.md must exist at bundled/verifier/prompts/orchestrator/."""
    assert ITER_REVISIT.exists(), (
        f"verifier_iter_revisit.md not found at {ITER_REVISIT}"
    )


# ---------------------------------------------------------------------------
# Test 7 — verifier_iter_revisit.md is NOT in ALLOWED_PROMPT_FILES
# ---------------------------------------------------------------------------

def test_iter_revisit_not_in_allowlist():
    """verifier_iter_revisit.md is an orchestrator helper — NOT dispatched; must not be in ALLOWED_PROMPT_FILES."""
    assert "verifier_iter_revisit.md" not in ALLOWED_PROMPT_FILES, (
        "verifier_iter_revisit.md must NOT be in ALLOWED_PROMPT_FILES — "
        "it is an orchestrator helper, not a subagent prompt"
    )


# ---------------------------------------------------------------------------
# Test 8 — verifier_iter_revisit.md has no harness placeholder variables
# ---------------------------------------------------------------------------

def test_iter_revisit_no_inputs_placeholder_block():
    """verifier_iter_revisit.md must not contain {{RUN_DIR}} or {{RUN_ID}} placeholders."""
    text = ITER_REVISIT.read_text()
    assert "{{RUN_DIR}}" not in text, (
        "verifier_iter_revisit.md must not contain {{RUN_DIR}} — orchestrator reads directly, no harness substitution"
    )
    assert "{{RUN_ID}}" not in text, (
        "verifier_iter_revisit.md must not contain {{RUN_ID}} — orchestrator reads directly, no harness substitution"
    )
