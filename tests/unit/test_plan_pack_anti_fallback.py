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


def test_skill_md_critical_block_bans_settings_json_edit():
    """Spike II F9: §CRITICAL must explicitly ban ASSEMBLE_GUARD disable.

    B-6 dogfood: main attempted to add `ASSEMBLE_GUARD: "off"` to
    ~/.claude/settings.json after hook blocked it. Rule must be in §CRITICAL
    so it's loaded into main's context (not just sub-agent preamble).
    """
    text = SKILL.read_text(encoding="utf-8")
    assert "ASSEMBLE_GUARD" in text
    assert "settings.json" in text
    # The actual ban phrase
    assert ("환경 변수 무력화 시도 금지" in text) or ("disable" in text.lower() and "settings.json" in text)


def test_skill_md_critical_block_bans_subagent_metadata_delegation():
    """Spike II F11: §CRITICAL must ban delegating orchestrator metadata.

    B-6: main dispatched sub-agent to update iteration_state.json after
    hook blocked direct write. iteration_state.json is orchestrator
    responsibility per cross_doc_step9.md — sub-agent delegation = bypass.
    """
    text = SKILL.read_text(encoding="utf-8")
    assert "iteration_state.json" in text
    assert "위임 금지" in text or "delegate" in text.lower()
    # The 8-file allowlist for sub-agent dispatch
    assert "prompts/" in text and "8" in text


def test_skill_md_critical_block_lists_8_prompt_files():
    """Sub-agent dispatch limited to 8 prompts/<step>.md files."""
    text = SKILL.read_text(encoding="utf-8")
    for prompt_name in ("prd_step2", "prd_step3", "prd_step4", "arch_step8",
                        "adr_step11", "ui_step13", "cross_doc_step9",
                        "iter_emphasis"):
        assert prompt_name in text, f"§CRITICAL must list {prompt_name}"
