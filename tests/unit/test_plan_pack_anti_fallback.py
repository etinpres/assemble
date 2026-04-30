"""Spike I — anti-fallback rule presence in SKILL.md head."""

from pathlib import Path

SKILL = Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md"


def test_skill_head_has_critical_block():
    body = SKILL.read_text()
    # 첫 1500자 안에 CRITICAL block 등장 (head 보장)
    head = body[:1500]
    assert "CRITICAL" in head, "SKILL.md head must have CRITICAL block"
    assert "orchestrator-only" in head, "CRITICAL block must mention orchestrator-only"


def test_anti_fallback_explicit_wording():
    body = SKILL.read_text()
    must_phrases = [
        "MUST NOT fall back",
        "Bash/Edit/Write/python3",
        "AskUserQuestion",
        "guard_run_dir.sh",
    ]
    for phrase in must_phrases:
        assert phrase in body, f"anti-fallback wording missing: {phrase!r}"
