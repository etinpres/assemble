"""Spike VI B8 — reviewer step prompt structural guards."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
SUBAGENT = ASSEMBLE / "bundled/reviewer/prompts/subagent"


def test_parse_scope_writes_parsed_scope_json():
    text = (SUBAGENT / "parse_scope_step1.md").read_text()
    assert "parsed_scope.json" in text


def test_diff_collect_writes_diff_inventory_and_raw_diff():
    text = (SUBAGENT / "diff_collect_step2.md").read_text()
    assert "diff_inventory.json" in text
    assert "raw.diff" in text


def test_classify_writes_classification_json():
    text = (SUBAGENT / "classify_files_step3.md").read_text()
    assert "classification.json" in text


def test_rule3_writes_rule3_audit_json():
    text = (SUBAGENT / "rule3_check_step4.md").read_text()
    assert "rule3_audit.json" in text
    assert "out-of-scope-refactor" in text


def test_severity_writes_severity_grid_json_and_verdict_logic():
    text = (SUBAGENT / "severity_assess_step5.md").read_text()
    assert "severity_grid.json" in text
    assert "merge-ready" in text
    assert "needs-fix" in text


def test_report_writes_review_report_md():
    text = (SUBAGENT / "report_step6.md").read_text()
    assert "REVIEW_REPORT.md" in text
    assert "{{VERDICT}}" in text
