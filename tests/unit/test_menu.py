from pathlib import Path
from server.menu import tools_for_stage, contextual_helpers
from server.inventory import scan, apply_classification


def _touch(p: Path, body: str = ""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body or "---\nname: x\n---\n")


def test_tools_for_stage_filters_by_mapping(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/writing-plans/SKILL.md",
           "---\nname: writing-plans\ndescription: spec\n---\n")
    _touch(tmp_path / ".claude/skills/qa/SKILL.md",
           "---\nname: qa\ndescription: test\n---\n")
    scan()
    plan_tools = tools_for_stage("plan")
    names = [t["name"] for t in plan_tools]
    assert "writing-plans" in names
    assert "qa" not in names


def test_tools_includes_multi_stage(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/codex/SKILL.md",
           "---\nname: codex\ndescription: review tool\n---\n")
    scan()
    review = [t["name"] for t in tools_for_stage("review")]
    debug  = [t["name"] for t in tools_for_stage("debug")]
    assert "codex" in review
    assert "codex" in debug


def test_contextual_helpers_for_execute(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/freeze/SKILL.md",
           "---\nname: freeze\ndescription: scope\n---\n")
    _touch(tmp_path / ".claude/skills/careful/SKILL.md",
           "---\nname: careful\ndescription: warn\n---\n")
    _touch(tmp_path / ".claude/skills/checkpoint/SKILL.md",
           "---\nname: checkpoint\ndescription: save\n---\n")
    _touch(tmp_path / ".claude/skills/learn/SKILL.md",
           "---\nname: learn\ndescription: capture\n---\n")
    scan()
    helpers = [h["name"] for h in contextual_helpers("execute")]
    assert "freeze" in helpers and "careful" in helpers and "checkpoint" in helpers
    assert "learn" not in helpers  # learning-capture not requested by execute


from server.menu import build_stage_options


def test_build_stage_options_includes_meta_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/writing-plans/SKILL.md",
           "---\nname: writing-plans\ndescription: write plan from spec\n---\n")
    _touch(tmp_path / ".claude/skills/checkpoint/SKILL.md",
           "---\nname: checkpoint\ndescription: save state\n---\n")
    scan()
    options = build_stage_options("plan")
    labels = [o["label"] for o in options]
    assert "writing-plans" in labels
    assert "checkpoint" in labels
    for required in ["물어보기", "skip", "직접", "back", "done"]:
        assert required in labels
    assert all("description" in o for o in options)
