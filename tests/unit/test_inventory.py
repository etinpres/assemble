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


from server.inventory import parse_skill_frontmatter


def test_parse_simple(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text(
        "---\n"
        "name: writing-plans\n"
        'description: Use when you have a spec\n'
        "---\n"
        "Body text\n"
    )
    meta = parse_skill_frontmatter(f)
    assert meta["name"] == "writing-plans"
    assert meta["description"].startswith("Use when")
    assert meta["body_excerpt"].startswith("Body text")


def test_parse_block_description(tmp_path):
    """gstack uses `description: |` block style."""
    f = tmp_path / "SKILL.md"
    f.write_text(
        "---\n"
        "name: office-hours\n"
        "description: |\n"
        "  YC Office Hours — two modes.\n"
        "  Detailed second line.\n"
        "---\n"
    )
    meta = parse_skill_frontmatter(f)
    assert meta["name"] == "office-hours"
    assert "YC Office Hours" in meta["description"]
    assert "Detailed second line" in meta["description"]


def test_parse_missing_frontmatter(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("Just a plain markdown file\n")
    meta = parse_skill_frontmatter(f)
    assert meta["name"] is None
    assert meta["description"] is None
    assert meta["body_excerpt"].startswith("Just a plain")
