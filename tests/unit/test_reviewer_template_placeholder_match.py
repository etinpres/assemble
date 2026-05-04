"""Spike VI B2 — REVIEW_REPORT.md.template structural contract."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
TEMPLATE = ASSEMBLE / "bundled/reviewer/templates/REVIEW_REPORT.md.template"

CANONICAL_SECTIONS = [
    "## Summary",
    "## Scope baseline",
    "## Diff inventory",
    "## Allow/Deny classification",
    "## Surgical Changes audit",
    "## Severity assessment",
    "## Recommendations",
]


def test_template_exists():
    assert TEMPLATE.exists(), f"missing {TEMPLATE.relative_to(ASSEMBLE)}"


def test_template_has_seven_canonical_sections_in_order():
    text = TEMPLATE.read_text(encoding="utf-8")
    last_idx = -1
    for header in CANONICAL_SECTIONS:
        idx = text.find(header, last_idx + 1)
        assert idx > last_idx, (
            f"section header out of order or missing: '{header}' "
            f"(searched after index {last_idx})"
        )
        last_idx = idx


def test_template_has_required_placeholders():
    text = TEMPLATE.read_text(encoding="utf-8")
    required = [
        "{{RUN_ID}}",
        "{{VERDICT}}",
        "{{VERDICT_REASON}}",
        "{{SCOPE_ALLOW}}",
        "{{SCOPE_DENY}}",
        "{{COMPLETION_CRITERION}}",
        "{{DIFF_FILES}}",
        "{{CLASSIFICATION_BODY}}",
        "{{RULE3_BODY}}",
        "{{SEVERITY_BODY}}",
        "{{RECOMMENDATIONS}}",
    ]
    missing = [p for p in required if p not in text]
    assert not missing, f"template missing placeholders: {missing}"
