"""Idea-shaper template substitution + render correctness tests."""
from __future__ import annotations

import re
from pathlib import Path

# Repo-relative resolution: tests/unit/test_idea_shaper_template.py → tests/unit/ → tests/ → repo root.
ASSEMBLE_ROOT = Path(__file__).resolve().parents[2]
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


def test_template_placeholder_set_matches_expected():
    """Both directions: missing placeholders AND extra placeholders fail.
    Catches drift in either direction so the template contract is locked.
    """
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    found = set(re.findall(r"\{\{[A-Z_]+\}\}", body))
    assert found == EXPECTED_PLACEHOLDERS, (
        f"placeholders drift — found={found}, expected={EXPECTED_PLACEHOLDERS}, "
        f"missing={EXPECTED_PLACEHOLDERS - found}, extra={found - EXPECTED_PLACEHOLDERS}"
    )


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
    # Assert each substituted value made it into the rendered output (catches a template bug
    # where a placeholder is referenced in two locations and one is mistakenly hardcoded).
    for substituted_value in (
        "택시 기사",
        "월말 정산이 손으로 한 시간",
        "기존 가계부 앱은 직장인용",
        "위젯 + 다국어",
        "택시 기사 가계부",
    ):
        assert substituted_value in rendered, f"Missing substituted value in rendered output: {substituted_value!r}"


def test_template_korean_section_headers():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    for required in ("## User", "## Problem", "## Wedge", "## Non-goals", "## Next step"):
        assert required in body, f"Missing section header: {required}"
