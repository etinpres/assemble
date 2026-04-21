from pathlib import Path
from server.inventory import enumerate_skill_paths, enumerate_agent_paths


def _touch(p: Path, body: str = ""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body or "---\nname: x\n---\n")


def test_enumerate_user_skills(tmp_path):
    home = tmp_path
    _touch(home / ".claude/skills/foo/SKILL.md")
    _touch(home / ".claude/skills/bar/SKILL.md")
    _touch(home / ".claude/skills/foo/nested/SKILL.md")  # gstack-style nested
    paths = enumerate_skill_paths(home=home)
    names = sorted(str(p.relative_to(home)) for p in paths)
    assert names == [
        ".claude/skills/bar/SKILL.md",
        ".claude/skills/foo/SKILL.md",
        ".claude/skills/foo/nested/SKILL.md",
    ]


def test_enumerate_plugin_skills(tmp_path):
    home = tmp_path
    _touch(home / ".claude/plugins/cache/m1/p1/1.0.0/skills/sk/SKILL.md")
    _touch(home / ".claude/plugins/cache/m2/p2/v/sub/SKILL.md")  # gstack nested under plugin
    paths = enumerate_skill_paths(home=home)
    rel = sorted(str(p.relative_to(home)) for p in paths)
    assert ".claude/plugins/cache/m1/p1/1.0.0/skills/sk/SKILL.md" in rel
    assert ".claude/plugins/cache/m2/p2/v/sub/SKILL.md" in rel


def test_enumerate_agents(tmp_path):
    home = tmp_path
    _touch(home / ".claude/agents/ios-checker.md")
    _touch(home / ".claude/plugins/cache/m1/p1/v/agents/codex-rescue.md")
    paths = enumerate_agent_paths(home=home)
    rel = sorted(str(p.relative_to(home)) for p in paths)
    assert rel == [
        ".claude/agents/ios-checker.md",
        ".claude/plugins/cache/m1/p1/v/agents/codex-rescue.md",
    ]
