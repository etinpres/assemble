"""Spike XIV Phase B — paradigm hybrid enforcement tests.

Verify 7 ★ bundles have mode-gate + Quick mode flow + dispatch contract
one-liner; verify 3 standard bundles do NOT have mode-gate (single-dispatch
default — gate would be redundant for V4 #9 IO exception or already-1-step
bundles).
"""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
BUNDLED = ASSEMBLE / "bundled"

STAR_BUNDLES = ("plan-pack", "builder", "debugger", "reviewer", "verifier", "shipper", "keeper")
STANDARD_BUNDLES = ("idea-shaper", "design-pack", "guardian")


def _read(bundle: str) -> str:
    return (BUNDLED / bundle / "SKILL.md").read_text(encoding="utf-8")


def test_seven_star_bundles_have_mode_gate():
    """All 7 ★ bundles' SKILL.md has the Mode gate head-section."""
    for b in STAR_BUNDLES:
        text = _read(b)
        assert "## Mode gate (V4 Spike XIV — paradigm enforcement)" in text, (
            f"{b}: missing Mode gate head-section"
        )


def test_seven_star_bundles_have_quick_mode_flow_section():
    """All 7 ★ bundles' SKILL.md has the Quick mode flow tail-section."""
    for b in STAR_BUNDLES:
        text = _read(b)
        assert "## Quick mode flow" in text, f"{b}: missing Quick mode flow"


def test_dispatch_contract_has_no_self_shortcut_rule():
    """All 7 ★ bundles' SKILL.md contains the no-shortcut-without-consent rule."""
    needle = "사용자 명시 동의 없이 단축 금지"
    for b in STAR_BUNDLES:
        text = _read(b)
        assert needle in text, f"{b}: missing no-shortcut rule"


def test_three_standard_bundles_have_no_mode_gate():
    """Standard bundles do NOT introduce Mode gate (V4 #9 IO exception or
    already 1-step). Adding a gate would be redundant."""
    for b in STANDARD_BUNDLES:
        text = _read(b)
        assert "## Mode gate (V4 Spike XIV" not in text, (
            f"{b}: standard bundle should not have Mode gate"
        )


def test_keeper_report_template_has_mode_usage_section():
    """KEEPER_REPORT.md.template has Mode usage section (T3 will populate
    with body; T2 just verifies the section heading lands)."""
    template = ASSEMBLE / "bundled/keeper/templates/KEEPER_REPORT.md.template"
    text = template.read_text(encoding="utf-8")
    assert "## Mode usage" in text, "KEEPER_REPORT.md.template missing Mode usage section"
