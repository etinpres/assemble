"""Unit tests for `bundled/keeper/templates/KEEPER_REPORT*.md.template`
(V4 Spike X, Task B7).

Grep-gate tests on the template files — locks in:
  * 7-section happy variant + 4-section abort variant H2 counts.
  * Both templates exist where ledger_update.py expects them.
  * No leftover TODO markers (lest R4 flag the keeper's own templates).
  * Placeholder set matches the contract documented in the spec —
    ledger_update.py substitutes exactly these names.
"""

import re
from pathlib import Path

import pytest


TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2]
    / "bundled"
    / "keeper"
    / "templates"
)
HAPPY = TEMPLATES_DIR / "KEEPER_REPORT.md.template"
ABORT = TEMPLATES_DIR / "KEEPER_REPORT_ABORT.md.template"


# Documented placeholder sets per template — keep in sync with the spec.
EXPECTED_HAPPY_PLACEHOLDERS = {
    "RUN_ID", "VERDICT", "REASON", "GENERATED_TS", "RUN_SUMMARY",
    "BUNDLES_OBSERVED", "ARTIFACTS_PRESENT_COUNT", "VERDICTS_COLLECTED",
    "CLEAN_TREE_STATUS", "BRANCH", "HEAD_SHA_SHORT",
    "GIT_DIFF_FILES_COUNT", "RULES_FIRED_TABLE", "LEARNINGS_EMITTED_LIST",
    "BEFORE_PRUNE_COUNT", "AFTER_PRUNE_COUNT", "NET_DELTA",
    "APPENDED_COUNT", "DROPPED_TTL", "DROPPED_SKIP", "DROPPED_DEDUP",
    "DROPPED_CAP", "PRUNE_SUMMARY_NOTE", "NEXT_RUN_RECALL_PREVIEW",
}

EXPECTED_ABORT_PLACEHOLDERS = {
    "RUN_ID", "REASON", "GENERATED_TS", "RUN_SUMMARY",
    "ABORT_INVENTORY_NOTE", "SKIP_REASON_DETAIL", "NEXT_STEPS_GUIDANCE",
}


def _placeholders_in(text: str) -> set[str]:
    """Extract `{{NAME}}` placeholder names from template body."""
    return set(re.findall(r"\{\{([A-Z_]+)\}\}", text))


def _h2_count(text: str) -> int:
    """Count `^## ` H2 headers in the rendered body. Excludes HTML
    comments at the top — those don't contain `## ` lines anyway.
    """
    return len(re.findall(r"^## ", text, re.MULTILINE))


def test_happy_template_exists():
    assert HAPPY.is_file(), f"happy KEEPER_REPORT template missing at {HAPPY}"


def test_abort_template_exists():
    assert ABORT.is_file(), f"abort KEEPER_REPORT template missing at {ABORT}"


def test_happy_template_7_h2_count():
    """Happy variant must have exactly 8 H2 sections (1. Run summary,
    2. Audit inventory, 3. Rules fired, 4. Learnings emitted, 5. Ledger
    state delta, 6. Prune summary, 7. Next-run recall preview, plus
    "Mode usage" appended in Spike XIV Phase B for paradigm hybrid).
    """
    body = HAPPY.read_text(encoding="utf-8")
    count = _h2_count(body)
    assert count == 8, (
        f"happy template must have exactly 8 H2 sections "
        f"(7 base + Mode usage), got {count}"
    )


def test_abort_template_4_h2_count():
    """Abort variant must have exactly 4 H2 sections (1. Run summary,
    2. Audit inventory, 3. Skip reason, 4. Next steps).
    """
    body = ABORT.read_text(encoding="utf-8")
    count = _h2_count(body)
    assert count == 4, (
        f"abort template must have exactly 4 H2 sections, got {count}"
    )


def test_no_leftover_TODO_markers_in_templates():
    """Templates must not contain TODO/FIXME/XXX markers — keeper R4
    would (correctly) flag any commit that lands such a marker, and the
    keeper's own templates should not be a self-induced violation.
    """
    for path in (HAPPY, ABORT):
        body = path.read_text(encoding="utf-8")
        for marker in ("TODO", "FIXME", "XXX"):
            assert not re.search(rf"\b{marker}\b", body), (
                f"{path.name} contains forbidden marker {marker!r} — "
                f"R4 would flag this on next keeper run"
            )


def test_placeholder_set_matches_expected_happy():
    body = HAPPY.read_text(encoding="utf-8")
    found = _placeholders_in(body)
    missing = EXPECTED_HAPPY_PLACEHOLDERS - found
    extra = found - EXPECTED_HAPPY_PLACEHOLDERS
    assert not missing, f"happy template missing placeholders: {sorted(missing)}"
    assert not extra, f"happy template has unexpected placeholders: {sorted(extra)}"


def test_placeholder_set_matches_expected_abort():
    body = ABORT.read_text(encoding="utf-8")
    found = _placeholders_in(body)
    missing = EXPECTED_ABORT_PLACEHOLDERS - found
    extra = found - EXPECTED_ABORT_PLACEHOLDERS
    assert not missing, f"abort template missing placeholders: {sorted(missing)}"
    assert not extra, f"abort template has unexpected placeholders: {sorted(extra)}"
