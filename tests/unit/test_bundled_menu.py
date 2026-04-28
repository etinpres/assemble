from pathlib import Path
from server.menu import build_stage_options


def _touch(p: Path, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _bundle(home: Path, name: str, description: str):
    body = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    _touch(home / f".claude/skills/assemble/bundled/{name}/SKILL.md", body)


def _user_skill(home: Path, name: str, description: str):
    body = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    _touch(home / f".claude/skills/{name}/SKILL.md", body)


def test_bundled_label_gets_star_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    opts = build_stage_options("plan")
    tool_labels = [o["label"] for o in opts if o["kind"] == "tool"]
    assert "★ plan-pack" in tool_labels


def test_bundled_sorts_before_user_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    _user_skill(tmp_path, "my-planner",
                "spec, requirements, plan, design doc — user planner")
    opts = [o for o in build_stage_options("plan") if o["kind"] == "tool"]
    labels = [o["label"] for o in opts]
    assert labels.index("★ plan-pack") < labels.index("my-planner")


def test_bundled_only_match_emits_fallback_hint(tmp_path, monkeypatch):
    """When no user/plugin tool matches a stage, the bundled entry's
    description gains a localized fallback hint."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    opts = [o for o in build_stage_options("plan") if o["kind"] == "tool"]
    assert len(opts) == 1
    assert opts[0]["label"] == "★ plan-pack"
    assert "fallback" in opts[0]["description"].lower()


def test_user_match_present_skips_fallback_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    _user_skill(tmp_path, "my-planner",
                "spec, requirements, plan, design doc — user planner")
    opts = [o for o in build_stage_options("plan") if o["kind"] == "tool"]
    bundled = next(o for o in opts if o["label"] == "★ plan-pack")
    assert "fallback" not in bundled["description"].lower()
