"""Design-pack template substitution + 8-entry anti-pattern verbatim tests."""
from __future__ import annotations

import re
from pathlib import Path

# Repo-relative resolution: tests/unit/test_design_pack_template.py → tests/unit/ → tests/ → repo root.
ASSEMBLE_ROOT = Path(__file__).resolve().parents[2]
DESIGN_TEMPLATE = ASSEMBLE_ROOT / "bundled" / "design-pack" / "templates" / "DESIGN.md.template"
ANTI_PATTERNS_TEMPLATE = ASSEMBLE_ROOT / "bundled" / "design-pack" / "templates" / "ANTI_PATTERNS.md.template"

DESIGN_PLACEHOLDERS = {
    "{{TONE}}",
    "{{COLOR_PRIMARY}}",
    "{{COMPONENTS}}",
    "{{TYPO}}",
    "{{IDEA_OR_PRD_SUMMARY}}",
}

EXPECTED_ANTI_PATTERNS = (
    "gradient-text",
    "glass morphism",
    "보라색 일색",
    "emoji 폭격",
    "Lorem ipsum",
    "TODO 미완성",
    "광고 카피체",
    "회색 그라데이션 박스",
)


def test_design_template_exists():
    assert DESIGN_TEMPLATE.is_file(), f"Missing template at {DESIGN_TEMPLATE}"


def test_anti_patterns_template_exists():
    assert ANTI_PATTERNS_TEMPLATE.is_file(), f"Missing template at {ANTI_PATTERNS_TEMPLATE}"


def test_design_template_placeholder_set_matches_expected():
    """Both directions: missing AND extra placeholders fail. Locks the contract."""
    body = DESIGN_TEMPLATE.read_text(encoding="utf-8")
    found = set(re.findall(r"\{\{[A-Z_]+\}\}", body))
    assert found == DESIGN_PLACEHOLDERS, (
        f"placeholders drift — found={found}, expected={DESIGN_PLACEHOLDERS}, "
        f"missing={DESIGN_PLACEHOLDERS - found}, extra={found - DESIGN_PLACEHOLDERS}"
    )


def test_anti_patterns_has_tone_header_placeholder():
    body = ANTI_PATTERNS_TEMPLATE.read_text(encoding="utf-8")
    assert "{{TONE}}" in body, "ANTI_PATTERNS header must use {{TONE}}"


def test_anti_patterns_has_8_verbatim_entries():
    body = ANTI_PATTERNS_TEMPLATE.read_text(encoding="utf-8")
    for entry in EXPECTED_ANTI_PATTERNS:
        assert entry in body, f"Missing anti-pattern entry: {entry}"


def test_anti_patterns_numbered_1_through_8():
    body = ANTI_PATTERNS_TEMPLATE.read_text(encoding="utf-8")
    for n in range(1, 9):
        assert f"{n}. **" in body, f"Missing numbered entry {n}."


def test_design_template_substitution_round_trip():
    body = DESIGN_TEMPLATE.read_text(encoding="utf-8")
    rendered = (
        body
        .replace("{{TONE}}", "미니멀 모노")
        .replace("{{COLOR_PRIMARY}}", "#2563eb")
        .replace("{{COMPONENTS}}", "shadcn/ui")
        .replace("{{TYPO}}", "Pretendard")
        .replace("{{IDEA_OR_PRD_SUMMARY}}", "택시 기사 가계부 MVP")
    )
    assert "{{" not in rendered
    # Assert each substituted value made it into rendered output.
    for substituted_value in (
        "미니멀 모노",
        "#2563eb",
        "shadcn/ui",
        "Pretendard",
        "택시 기사 가계부 MVP",
    ):
        assert substituted_value in rendered, f"Missing substituted value: {substituted_value!r}"


def test_design_template_no_slop_phrases():
    """DESIGN.md.template must NOT contain words that would violate ANTI_PATTERNS deny list."""
    body = DESIGN_TEMPLATE.read_text(encoding="utf-8")
    forbidden = ("gradient-text", "혁신적", "차세대")
    for word in forbidden:
        assert word not in body, f"DESIGN.md.template must not contain {word!r}"
