"""Spike I — sub-agent path-only return contract tests.

Verifies SKILL.md teaches main Claude to parse stdout WROTE: lines
(not body text) and that all 7 sub-agent prompts emit WROTE: convention.
"""

from pathlib import Path

SKILL = Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md"
PROMPTS_DIR = Path.home() / ".claude/skills/assemble/bundled/plan-pack/prompts"


def test_skill_md_teaches_wrote_parse():
    body = SKILL.read_text()
    # 메인이 stdout에서 WROTE 파싱하라는 문구 (예시 또는 instruction)
    assert "WROTE:" in body, "SKILL.md must teach WROTE: stdout convention"
    assert "^WROTE: (.+)$" in body or "WROTE: <path>" in body, \
        "SKILL.md must show parse pattern"


def test_skill_md_no_main_split_sections():
    body = SKILL.read_text()
    # 메인 코드가 split_sections 정의하지 않아야 (sub-agent 안으로 이동)
    assert "def split_sections" not in body, \
        "split_sections must move into sub-agent prompts, not SKILL.md main code"


def test_skill_md_no_main_write_run_artifact_call():
    body = SKILL.read_text()
    # SKILL.md 본문에 메인이 write_run_artifact 호출하는 코드 블록 없어야
    # (단, sub-agent 안내 텍스트로 함수명 언급은 OK — 정확한 import 라인이 main 코드가 아닌지 확인)
    main_code_blocks = [b for b in body.split("```python") if "ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE" not in b]
    for blk in main_code_blocks:
        assert "from server import write_run_artifact" not in blk, \
            "Main Claude code in SKILL.md must not import write_run_artifact directly"


def test_all_prompts_emit_wrote_or_orchestrator_facing():
    """7개 sub-agent prompt + 1 orchestrator-facing iter_emphasis."""
    sub_agent_files = ["prd_step2.md", "prd_step3.md", "prd_step4.md",
                       "arch_step8.md", "adr_step11.md", "ui_step13.md",
                       "cross_doc_step9.md"]
    for fname in sub_agent_files:
        body = (PROMPTS_DIR / "subagent" / fname).read_text()
        assert "WROTE:" in body, f"{fname} sub-agent prompt missing WROTE: stdout convention"
        assert "ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE" in body, \
            f"{fname} missing magic marker for hook v1 passthrough"
    # iter_emphasis is orchestrator-facing (no marker required)
    iter_body = (PROMPTS_DIR / "orchestrator" / "iter_emphasis.md").read_text()
    assert "ITERATION MODE" in iter_body or "emphasis" in iter_body.lower(), \
        "iter_emphasis must guide orchestrator on emphasis fan-out"
