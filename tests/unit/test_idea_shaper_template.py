"""Idea-shaper template substitution + render correctness tests."""
from __future__ import annotations

from pathlib import Path

ASSEMBLE_ROOT = Path.home() / ".claude" / "skills" / "assemble"
TEMPLATE_PATH = ASSEMBLE_ROOT / "bundled" / "idea-shaper" / "templates" / "IDEA.md.template"

EXPECTED_PLACEHOLDERS = {
    "{{USER}}",
    "{{PROBLEM}}",
    "{{WEDGE}}",
    "{{NON_GOALS}}",
    "{{TASK_SUMMARY}}",
}


def test_template_exists():
    assert TEMPLATE_PATH.is_file(), f"Missing template at {TEMPLATE_PATH}"


def test_template_has_all_5_placeholders():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    found = {p for p in EXPECTED_PLACEHOLDERS if p in body}
    missing = EXPECTED_PLACEHOLDERS - found
    assert not missing, f"Missing placeholders: {missing}"


def test_template_has_5_sections():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    section_headers = [line for line in body.splitlines() if line.startswith("## ")]
    # Template has 5 H2 sections: User / Problem / Wedge / Non-goals / Next step
    assert len(section_headers) == 5, (
        f"Expected 5 H2 sections (User/Problem/Wedge/Non-goals/Next step), got {len(section_headers)}: {section_headers}"
    )


def test_template_substitution_round_trip():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = (
        body
        .replace("{{USER}}", "택시 기사")
        .replace("{{PROBLEM}}", "월말 정산이 손으로 한 시간")
        .replace("{{WEDGE}}", "기존 가계부 앱은 직장인용")
        .replace("{{NON_GOALS}}", "위젯 + 다국어")
        .replace("{{TASK_SUMMARY}}", "택시 기사 가계부")
    )
    assert "{{" not in rendered, f"Unsubstituted placeholder remains in rendered output:\n{rendered}"
    assert "택시 기사" in rendered
    assert "월말 정산" in rendered


def test_template_korean_section_headers():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    for required in ("## User", "## Problem", "## Wedge", "## Non-goals", "## Next step"):
        assert required in body, f"Missing section header: {required}"
