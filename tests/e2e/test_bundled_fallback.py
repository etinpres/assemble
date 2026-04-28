"""End-to-end check: a 'fresh laptop' that owns no user/plugin skills must
still see the V4 bundled tool surface in the plan menu, marked with ★ and
flagged as a fallback. This is the V4 self-sufficiency guarantee in test form.
"""
from pathlib import Path
from server.menu import build_stage_options


def _bundle(home: Path, name: str, description: str):
    body = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    p = home / f".claude/skills/assemble/bundled/{name}/SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_empty_home_falls_back_to_bundle(tmp_path, monkeypatch):
    """No user skills installed at all → bundled plan tool is the only
    `tool`-kind option for the plan stage, labeled with ★ and a fallback hint.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _bundle(tmp_path, "plan-pack",
            "spec, requirements, plan, design doc — bundled plan tool")
    opts = build_stage_options("plan")
    tool_opts = [o for o in opts if o["kind"] == "tool"]
    assert len(tool_opts) == 1, [o["label"] for o in tool_opts]
    only = tool_opts[0]
    assert only["label"].startswith("★ "), only
    assert only["bundled"] is True, only
    assert "fallback" in only["description"].lower(), only
