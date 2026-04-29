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


from server.inventory import load_stages, load_stage_roles


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


def test_scan_heuristic_classifies_rich_description(tmp_path, monkeypatch):
    """Multiple stage keywords in a description → heuristic classifies immediately."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/my-planner/SKILL.md",
           "---\nname: my-planner\n"
           "description: Use when you have a spec or requirements to plan before code\n"
           "---\n")
    inv = scan()
    entry = inv["skills"]["my-planner"]
    assert entry["source"] == "heuristic-classified"
    assert any(m["stage"] == "plan" for m in entry["mappings"])


def test_scan_marks_unknown(tmp_path, monkeypatch):
    """If the heuristic can't match, leave as unclassified (defer to LLM pass)."""
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
    """Rich planner description → heuristic-classified; vague odd-tool stays unclassified."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/planner/SKILL.md",
           "---\nname: planner\n"
           "description: Use when you have a spec or requirements to plan\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/odd-tool/SKILL.md",
           "---\nname: odd-tool\ndescription: mystery purpose\n---\n")
    scan()
    from server.inventory import unclassified_names
    assert unclassified_names() == ["odd-tool"]


# -------------------------------------------------------------------------
# Heuristic-classifier regression tests (post pre_mapping.json retirement)
# -------------------------------------------------------------------------

def test_heuristic_catches_ship_description(tmp_path, monkeypatch):
    """Clear deploy/ship keywords → classified to ship stage immediately."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/shipper/SKILL.md",
           "---\nname: shipper\n"
           "description: Ship and deploy to production, push to main, release\n"
           "---\n")
    inv = scan()
    e = inv["skills"]["shipper"]
    assert e["source"] == "heuristic-classified"
    assert any(m["stage"] == "ship" for m in e["mappings"])


def test_heuristic_defers_on_vague_description(tmp_path, monkeypatch):
    """When not confident, leave unclassified so the LLM loop can handle it."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/vague/SKILL.md",
           "---\nname: vague\ndescription: does something maybe\n---\n")
    inv = scan()
    e = inv["skills"]["vague"]
    assert e["source"] == "unclassified"
    assert e["mappings"] == []


def test_heuristic_assigns_proper_role_for_safety(tmp_path, monkeypatch):
    """A safety skill's role must match a stage_roles.json key for contextual_helper to pick it up."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/my-freezer/SKILL.md",
           "---\nname: my-freezer\n"
           "description: Freeze project edits, restrict edits to a folder, lock down\n"
           "---\n")
    inv = scan()
    mappings = inv["skills"]["my-freezer"]["mappings"]
    assert any(m["stage"] == "safety" and m["role"] == "edit-scope-limit"
               for m in mappings)


def test_prior_llm_classification_beats_heuristic(tmp_path, monkeypatch):
    """User/LLM classifications survive rebuilds; the heuristic does not overwrite them."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/dual-signal/SKILL.md",
           "---\nname: dual-signal\n"
           "description: Ship and deploy, push to main, release changelog\n"
           "---\n")
    scan()
    # User overrides with "actually this is a plan tool"
    apply_classification("dual-signal",
                         [{"stage": "plan", "role": "custom"}],
                         confidence="high", reasoning="user override")
    inv = scan(force=True)
    e = inv["skills"]["dual-signal"]
    assert e["source"] == "llm-classified"
    assert e["mappings"] == [{"stage": "plan", "role": "custom"}]


def test_bundled_only_excludes_user_skills(tmp_path, monkeypatch):
    """ASSEMBLE_BUNDLED_ONLY=1 hides skills installed outside the assemble bundled tree.

    Blank-Mac dogfood gates use this flag to simulate a fresh user with only
    the bundled tools available, without nuking ~/.claude/skills/.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.setenv("ASSEMBLE_BUNDLED_ONLY", "1")
    _touch(tmp_path / ".claude/skills/test_user_skill/SKILL.md",
           "---\nname: test_user_skill\ndescription: a user-installed skill\n---\n")
    _touch(tmp_path / ".claude/skills/assemble/bundled/plan-pack/SKILL.md",
           "---\nname: plan-pack\ndescription: bundled plan helper\n---\n")
    inv = scan()
    assert "test_user_skill" not in inv["skills"]


def test_bundled_only_keeps_bundled(tmp_path, monkeypatch):
    """ASSEMBLE_BUNDLED_ONLY=1 still surfaces skills under the assemble bundled tree."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.setenv("ASSEMBLE_BUNDLED_ONLY", "1")
    _touch(tmp_path / ".claude/skills/test_user_skill/SKILL.md",
           "---\nname: test_user_skill\ndescription: a user-installed skill\n---\n")
    _touch(tmp_path / ".claude/skills/assemble/bundled/plan-pack/SKILL.md",
           "---\nname: plan-pack\ndescription: bundled plan helper\n---\n")
    inv = scan()
    assert "plan-pack" in inv["skills"]
