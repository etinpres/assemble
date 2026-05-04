"""Guardian template substitution + checklist coverage tests."""
from __future__ import annotations

import re
from pathlib import Path

# Repo-relative resolution: tests/unit/test_guardian_template.py → tests/unit/ → tests/ → repo root.
ASSEMBLE_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ASSEMBLE_ROOT / "bundled" / "guardian" / "templates" / "GUARDIAN.md.template"

EXPECTED_PLACEHOLDERS = {
    "{{TIMESTAMP}}",
    "{{FROZEN_DIRS}}",
    "{{DENY_COMMANDS}}",
    "{{PLANNED_DESTRUCTIVE}}",
}

EXPECTED_CHECKLIST_KEYWORDS = (
    "백업",
    "dry-run",
    "영향 범위",
    "롤백",
    "명시적 승인",
)


def test_template_exists():
    assert TEMPLATE_PATH.is_file(), f"Missing template at {TEMPLATE_PATH}"


def test_template_placeholder_set_matches_expected():
    """Both directions: missing AND extra placeholders fail. Locks the contract."""
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    found = set(re.findall(r"\{\{[A-Z_]+\}\}", body))
    assert found == EXPECTED_PLACEHOLDERS, (
        f"placeholders drift — found={found}, expected={EXPECTED_PLACEHOLDERS}, "
        f"missing={EXPECTED_PLACEHOLDERS - found}, extra={found - EXPECTED_PLACEHOLDERS}"
    )


def test_template_has_5_checklist_keywords():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    for keyword in EXPECTED_CHECKLIST_KEYWORDS:
        assert keyword in body, f"Missing checklist keyword: {keyword}"


def test_template_has_5_checkbox_lines():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    checkboxes = [line for line in body.splitlines() if line.strip().startswith("- [ ]")]
    assert len(checkboxes) == 5, f"Expected 5 checkbox items, got {len(checkboxes)}: {checkboxes}"


def test_template_substitution_round_trip():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = (
        body
        .replace("{{TIMESTAMP}}", "2026-05-04T15:00:00Z")
        .replace("{{FROZEN_DIRS}}", "- ~/Documents\n- /etc")
        .replace("{{DENY_COMMANDS}}", "- git push --force\n- rm -rf")
        .replace("{{PLANNED_DESTRUCTIVE}}", "- DB 마이그레이션 (다음 화요일)")
    )
    assert "{{" not in rendered, f"Unsubstituted placeholder remains:\n{rendered}"
    # Assert each substituted value made it into rendered output.
    for substituted_value in (
        "2026-05-04T15:00:00Z",
        "~/Documents",
        "git push --force",
        "DB 마이그레이션",
    ):
        assert substituted_value in rendered, f"Missing substituted value: {substituted_value!r}"


def test_template_section_headers_present():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    for required in (
        "## Frozen directories",
        "## Deny commands",
        "## Planned destructive operations",
        "## 사용자 체크리스트",
        "## 다른 번들에 알림",
    ):
        assert required in body, f"Missing section header: {required}"
