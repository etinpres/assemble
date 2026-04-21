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


from server.inventory import load_pre_mapping, load_stages, load_stage_roles


def test_load_pre_mapping():
    m = load_pre_mapping()
    assert m["writing-plans"] == [{"stage": "plan", "role": "requirements-spec"}]
    assert {"stage": "review", "role": "second-opinion-review"} in m["codex"]
    assert {"stage": "debug",  "role": "second-opinion"} in m["codex"]


def test_load_stages():
    s = load_stages()
    seq_ids = [x["id"] for x in s["sequential"]]
    assert seq_ids == ["discover","plan","design","execute","debug","review","verify","ship"]
    orth_ids = [x["id"] for x in s["orthogonal"]]
    assert orth_ids == ["safety","meta"]


def test_load_stage_roles():
    r = load_stage_roles()
    assert "edit-scope-limit" in r["execute"]
    assert "dangerous-cmd-warn" in r["debug"]
    assert "skill-discovery" in r["discover"]


import os
import time
from server.inventory import scan, INVENTORY_REL


def test_scan_writes_inventory(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/writing-plans/SKILL.md",
           "---\nname: writing-plans\ndescription: spec\n---\nbody")
    inv = scan()
    assert "writing-plans" in inv["skills"]
    entry = inv["skills"]["writing-plans"]
    assert entry["mappings"] == [{"stage": "plan", "role": "requirements-spec"}]
    assert entry["source"] == "pre-mapped"


def test_scan_marks_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/some-new-skill/SKILL.md",
           "---\nname: some-new-skill\ndescription: who knows\n---\n")
    inv = scan()
    e = inv["skills"]["some-new-skill"]
    assert e["mappings"] == []
    assert e["source"] == "unclassified"


def test_scan_uses_cache_when_mtime_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/x/SKILL.md", "---\nname: x\n---\n")
    first = scan()
    cache = tmp_path / ".claude/channels/assemble/inventory.json"
    cache_mtime = cache.stat().st_mtime
    time.sleep(0.05)
    second = scan()
    cache_mtime2 = cache.stat().st_mtime
    assert cache_mtime == cache_mtime2  # cache reused, no rewrite
    assert first == second


def test_scan_rebuilds_when_skills_dir_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/x/SKILL.md", "---\nname: x\n---\n")
    scan()
    time.sleep(0.05)
    _touch(tmp_path / ".claude/skills/y/SKILL.md", "---\nname: y\n---\n")
    inv = scan()
    assert "y" in inv["skills"]


def test_force_flag_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/x/SKILL.md", "---\nname: x\n---\n")
    scan()
    cache = tmp_path / ".claude/channels/assemble/inventory.json"
    before = cache.stat().st_mtime
    time.sleep(0.05)
    scan(force=True)
    assert cache.stat().st_mtime > before


from server.inventory import apply_classification


def test_apply_classification_updates_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/new-thing/SKILL.md",
           "---\nname: new-thing\n---\n")
    scan()
    apply_classification("new-thing", [{"stage": "execute", "role": "tdd-implementation"}],
                         confidence="high", reasoning="looks like TDD")
    inv = scan()
    e = inv["skills"]["new-thing"]
    assert e["mappings"] == [{"stage": "execute", "role": "tdd-implementation"}]
    assert e["source"] == "llm-classified"
    assert e["classification"]["confidence"] == "high"


def test_unclassified_lists_only_unmapped(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/writing-plans/SKILL.md",
           "---\nname: writing-plans\n---\n")
    _touch(tmp_path / ".claude/skills/odd-tool/SKILL.md",
           "---\nname: odd-tool\n---\n")
    scan()
    from server.inventory import unclassified_names
    names = unclassified_names()
    assert names == ["odd-tool"]
