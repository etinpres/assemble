from pathlib import Path
from server.menu import tools_for_stage, contextual_helpers
from server.inventory import scan, apply_classification


def _touch(p: Path, body: str = ""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body or "---\nname: x\n---\n")


def test_tools_for_stage_filters_by_mapping(tmp_path, monkeypatch):
    """Skill rich in plan keywords vs one rich in verify keywords."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/my-planner/SKILL.md",
           "---\nname: my-planner\n"
           "description: Plan from a spec or requirements before you write code\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/my-qa/SKILL.md",
           "---\nname: my-qa\n"
           "description: QA test this site, verify, test and fix bugs\n"
           "---\n")
    scan()
    plan_names = [t["name"] for t in tools_for_stage("plan")]
    assert "my-planner" in plan_names
    assert "my-qa" not in plan_names


def test_tools_includes_multi_stage(tmp_path, monkeypatch):
    """Description with both review and debug keywords should surface in both stages."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/second-opinion/SKILL.md",
           "---\nname: second-opinion\n"
           "description: Code review and pre-landing review, also debug and "
           "investigate root cause, troubleshoot bug\n---\n")
    scan()
    review = [t["name"] for t in tools_for_stage("review")]
    debug = [t["name"] for t in tools_for_stage("debug")]
    assert "second-opinion" in review
    assert "second-opinion" in debug


def test_contextual_helpers_for_execute(tmp_path, monkeypatch):
    """Rich safety/meta descriptions let the heuristic assign a role too."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/freeze/SKILL.md",
           "---\nname: freeze\n"
           "description: Freeze edits, restrict edits to a folder, lock down changes\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/careful/SKILL.md",
           "---\nname: careful\n"
           "description: Warn before destructive commands, careful mode, guard\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/checkpoint/SKILL.md",
           "---\nname: checkpoint\n"
           "description: Save state and save progress, checkpoint and resume\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/learn/SKILL.md",
           "---\nname: learn\n"
           "description: Capture learnings and retro for the project\n"
           "---\n")
    scan()
    helpers = [h["name"] for h in contextual_helpers("execute")]
    assert "freeze" in helpers
    assert "careful" in helpers
    assert "checkpoint" in helpers
    # learning-capture is not part of execute (per stage_roles.json)
    assert "learn" not in helpers


from server.menu import build_stage_options


def test_build_stage_options_includes_meta_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/my-planner/SKILL.md",
           "---\nname: my-planner\n"
           "description: Plan from a spec or requirements\n---\n")
    _touch(tmp_path / ".claude/skills/checkpoint/SKILL.md",
           "---\nname: checkpoint\n"
           "description: Save state and save progress, checkpoint and resume\n"
           "---\n")
    scan()
    options = build_stage_options("plan")
    labels = [o["label"] for o in options]
    assert "my-planner" in labels
    assert "checkpoint" in labels  # contextual helper via state-save role
    for required in ["ask", "skip", "manual", "back", "done"]:
        assert required in labels
    assert all("description" in o for o in options)
