from pathlib import Path
from server.inventory import scan


def _touch(p: Path, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _bundle(home: Path, name: str, description: str):
    body = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    _touch(home / f".claude/skills/assemble/bundled/{name}/SKILL.md", body)


def _user_skill(home: Path, name: str, description: str):
    body = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    _touch(home / f".claude/skills/{name}/SKILL.md", body)


def test_bundled_entry_marked_true(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    inv = scan(force=True)
    assert "plan-pack" in inv["skills"]
    assert inv["skills"]["plan-pack"]["bundled"] is True


def test_user_skill_not_marked_bundled(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _user_skill(tmp_path, "my-planner",
                "spec, requirements, plan, design doc — user planner")
    inv = scan(force=True)
    assert inv["skills"]["my-planner"]["bundled"] is False


def test_bundled_path_under_user_skills_still_classifies(tmp_path, monkeypatch):
    """Bundled skill's heuristic classification still runs (not bypassed)."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    inv = scan(force=True)
    mappings = inv["skills"]["plan-pack"]["mappings"]
    assert any(m["stage"] == "plan" for m in mappings), mappings
