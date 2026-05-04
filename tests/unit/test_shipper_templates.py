"""C3 guard — shipper templates have correct H2 section counts and the
required set of placeholders.

SHIP_REPORT.md.template = 7 canonical H2 sections (Summary, Pre-flight,
Version bump, Build artifact, Tag, Verdict reasoning, Hand-off) + an H1
title block. SHIP_REPORT_ABORT.md.template = 4 H2 sections (Summary,
Pre-flight, Verdict reasoning, Hand-off) — Sections 3/4/5 omitted with
an admonition under §Pre-flight.
"""

import re
from pathlib import Path

TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2]
    / "bundled"
    / "shipper"
    / "templates"
)


def test_ship_report_template_exists():
    assert (TEMPLATES_DIR / "SHIP_REPORT.md.template").is_file()


def test_ship_report_abort_template_exists():
    assert (TEMPLATES_DIR / "SHIP_REPORT_ABORT.md.template").is_file()


def test_ship_report_has_seven_h2_sections():
    text = (TEMPLATES_DIR / "SHIP_REPORT.md.template").read_text()
    h2_count = len(re.findall(r"^## ", text, re.MULTILINE))
    assert h2_count == 7, f"expected 7 H2 sections, got {h2_count}"


def test_ship_report_abort_has_four_h2_sections():
    text = (TEMPLATES_DIR / "SHIP_REPORT_ABORT.md.template").read_text()
    h2_count = len(re.findall(r"^## ", text, re.MULTILINE))
    assert h2_count == 4, f"expected 4 H2 sections, got {h2_count}"


def test_ship_report_placeholder_count_at_least_14():
    text = (TEMPLATES_DIR / "SHIP_REPORT.md.template").read_text()
    placeholders = set(re.findall(r"\{\{(\w+)\}\}", text))
    assert len(placeholders) >= 14, (
        f"expected >=14 distinct placeholders, got "
        f"{len(placeholders)}: {sorted(placeholders)}"
    )


def test_ship_report_required_placeholders_present():
    text = (TEMPLATES_DIR / "SHIP_REPORT.md.template").read_text()
    required = {
        "RUN_ID",
        "VERDICT",
        "TAG_NAME",
        "TAG_SHA",
        "NEW_VERSION",
        "BUILD_EXIT_CODE",
        "VERDICT_REASON",
        "HANDOFF_COMMANDS",
    }
    found = set(re.findall(r"\{\{(\w+)\}\}", text))
    missing = required - found
    assert not missing, f"missing required placeholders: {missing}"


def test_ship_report_abort_required_placeholders_present():
    text = (TEMPLATES_DIR / "SHIP_REPORT_ABORT.md.template").read_text()
    required = {
        "RUN_ID",
        "VERDICT",
        "VERDICT_REASON",
        "HANDOFF_COMMANDS",
        "CLEAN_TREE",
        "BRANCH",
        "HEAD_SHA",
        "VERIFY_VERDICT",
    }
    found = set(re.findall(r"\{\{(\w+)\}\}", text))
    missing = required - found
    assert not missing, (
        f"abort template missing required placeholders: {missing}"
    )


def test_ship_report_has_doc_comment_block():
    """Top of each template documents its placeholders in an HTML
    comment block — keeps the canonical placeholder list co-located."""
    for name in ("SHIP_REPORT.md.template", "SHIP_REPORT_ABORT.md.template"):
        text = (TEMPLATES_DIR / name).read_text()
        assert text.lstrip().startswith("<!--"), (
            f"{name} must start with an HTML comment block listing "
            "placeholders"
        )
        assert "PLACEHOLDERS" in text.split("-->", 1)[0], (
            f"{name} comment block must contain a PLACEHOLDERS heading"
        )
