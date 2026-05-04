"""Spike VII Track A regression: bundle prompts must never use
relative `runs/{{RUN_ID}}/...` paths — only absolute `{{RUN_DIR}}/...`.

Sub-agent cwd is unspecified at dispatch time; relative paths resolve
against the SKILL package dir (~/.claude/skills/assemble/), not the
canonical run dir under ~/.claude/channels/assemble/runs/. Spike VI
B-11 real-dispatch only worked due to a manual symlink stop-gap.
"""
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
BUNDLED = SKILL_ROOT / "bundled"


def test_no_relative_run_path_in_prompts():
    offenders = []
    for prompt in BUNDLED.glob("*/prompts/**/*.md"):
        text = prompt.read_text(encoding="utf-8")
        if "runs/{{RUN_ID}}" in text:
            offenders.append(str(prompt.relative_to(BUNDLED)))
    assert not offenders, (
        f"Prompts must use {{{{RUN_DIR}}}}/... not runs/{{{{RUN_ID}}}}/.... "
        f"Offenders: {offenders}"
    )


def test_run_dir_token_present_in_path_writing_bundles():
    """Bundles that write artifacts must reference {{RUN_DIR}}."""
    must_have = ["reviewer", "builder", "debugger"]
    for bundle in must_have:
        bd = BUNDLED / bundle / "prompts"
        if not bd.exists():
            continue
        all_text = "\n".join(p.read_text() for p in bd.glob("**/*.md"))
        assert "{{RUN_DIR}}" in all_text, (
            f"{bundle}: lost RUN_DIR token after migration"
        )
