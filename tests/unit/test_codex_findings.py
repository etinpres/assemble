"""Regression tests for architecture-review findings.

Each test covers a concrete bug or weakness caught during external review:
precedence, concurrency, state transitions, menu dedupe, agent classification,
corrupt-state handling, transition guards. Numbers map to finding IDs
documented in SKILL.md Troubleshooting.
"""
import json
import threading
from pathlib import Path

import pytest

from server import (
    scan, apply_classification,
    unclassified_names, unclassified_entries,
    build_stage_options,
    create_run, load_progress, mark_stage,
)


def _touch(p: Path, body: str = ""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body or "---\nname: x\n---\n")


# Finding #1: user skill precedence (user > plugin)
def test_user_skill_wins_over_plugin_same_name(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/foo/SKILL.md",
           "---\nname: foo\ndescription: USER_VERSION\n---\nuser body\n")
    _touch(tmp_path / ".claude/plugins/cache/m/p/v/skills/foo/SKILL.md",
           "---\nname: foo\ndescription: PLUGIN_VERSION\n---\nplugin body\n")
    inv = scan()
    assert inv["skills"]["foo"]["description"] == "USER_VERSION"
    assert "user body" in inv["skills"]["foo"]["body_excerpt"]


# Finding #1 (agent variant): agent precedence not broken by overwrite.
def test_user_agent_wins_over_plugin_same_name(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/agents/my-agent.md",
           "---\nname: my-agent\ndescription: USER_AGENT\n---\n")
    _touch(tmp_path / ".claude/plugins/cache/m/p/v/agents/my-agent.md",
           "---\nname: my-agent\ndescription: PLUGIN_AGENT\n---\n")
    inv = scan()
    assert inv["agents"]["my-agent"]["description"] == "USER_AGENT"


# Finding #2: concurrent scan/apply writes don't trample each other.
def test_concurrent_apply_classification_serialized(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    for n in ("a", "b", "c", "d"):
        _touch(tmp_path / f".claude/skills/{n}/SKILL.md", f"---\nname: {n}\n---\n")
    scan()

    errors: list[Exception] = []

    def worker(name: str):
        try:
            apply_classification(
                name,
                [{"stage": "execute", "role": "r"}],
                confidence="high",
                reasoning="race",
            )
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(n,))
               for n in ("a", "b", "c", "d")]
    for t in threads: t.start()
    for t in threads: t.join()
    assert errors == []

    inv = scan()
    for n in ("a", "b", "c", "d"):
        assert inv["skills"][n]["source"] == "llm-classified", \
            f"{n} lost its classification under concurrent writes"


# Finding #3: 'back' must NOT persist as a stage status.
def test_back_does_not_persist_as_stage_status(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "design", "execute"])
    mark_stage(rid, "plan", status="done", tool_used="w")
    mark_stage(rid, "design", status="done", tool_used="d")
    # User on 'execute' picks 'back' → cursor moves, but execute's status
    # must remain 'pending' (prior: it got overwritten to 'back').
    mark_stage(rid, "execute", status="back")
    p = load_progress(rid)
    assert p["current_stage_index"] == 1
    assert p["stages"][2]["status"] == "pending"
    assert p["stages"][1]["status"] == "done"
    # wrap-up count must still work (no 'back' in the counts)
    done = sum(1 for s in p["stages"] if s["status"] == "done")
    assert done == 2


# Finding #7: enforce legal transitions — can't drop 'done' back into 'in_progress'.
def test_terminal_cannot_re_enter_in_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan"])
    mark_stage(rid, "plan", status="done", tool_used="w")
    with pytest.raises(ValueError, match="illegal transition"):
        mark_stage(rid, "plan", status="in_progress")


# Finding #4: helper/tool dedupe when skill matches both via direct stage
# and via meta/safety helper role.
def test_build_stage_options_dedupes_helper_and_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/dual-skill/SKILL.md",
           "---\nname: dual-skill\ndescription: dual\n---\n")
    scan()
    # Map to both 'discover' (direct) and 'meta' with a role stage_roles[discover]
    # advertises ('skill-discovery'). menu must surface only one 'dual-skill'.
    apply_classification(
        "dual-skill",
        [
            {"stage": "discover", "role": "finder"},
            {"stage": "meta", "role": "skill-discovery"},
        ],
        confidence="high",
        reasoning="test dedupe",
    )
    opts = build_stage_options("discover")
    dual = [o for o in opts if o["label"] == "dual-skill"]
    assert len(dual) == 1, "helper should not appear when tool entry is present"
    assert dual[0]["kind"] == "tool"


# Finding #5 (a): unclassified_entries includes both skills and agents.
def test_unclassified_entries_includes_skills_and_agents(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/mystery-skill/SKILL.md",
           "---\nname: mystery-skill\n---\n")
    _touch(tmp_path / ".claude/agents/mystery-agent.md",
           "---\nname: mystery-agent\n---\n")
    scan()
    entries = unclassified_entries()
    kinds = {(e["kind"], e["name"]) for e in entries}
    assert ("skill", "mystery-skill") in kinds
    assert ("agent", "mystery-agent") in kinds
    # back-compat: unclassified_names() still skills-only
    assert "mystery-skill" in unclassified_names()
    assert "mystery-agent" not in unclassified_names()


# Finding #5 (b): agent CAN be promoted out of unclassified via apply_classification.
def test_apply_classification_supports_agents(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/agents/my-worker.md",
           "---\nname: my-worker\ndescription: bg worker\n---\n")
    scan()
    apply_classification(
        "my-worker",
        [{"stage": "execute", "role": "background-worker"}],
        confidence="medium",
        reasoning="best guess",
    )
    inv = scan()
    entry = inv["agents"]["my-worker"]
    assert entry["source"] == "llm-classified"
    assert entry["mappings"] == [{"stage": "execute",
                                  "role": "background-worker"}]


# Finding #6: corrupt inventory.json is quarantined, not silently discarded.
def test_corrupt_cache_is_quarantined_and_rebuilt(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/x/SKILL.md",
           "---\nname: x\ndescription: ok\n---\nbody\n")
    scan()
    cache = tmp_path / ".claude/channels/assemble/inventory.json"
    cache.write_text("{not valid json")
    # Trigger rebuild; bad file must be preserved alongside, not overwritten.
    inv = scan()
    assert "x" in inv["skills"]
    backups = list(cache.parent.glob("inventory.json.bad-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "{not valid json"


# Finding #8: enumerate_* rejects symlinks whose resolved target escapes
# ~/.claude (prevents inventory.json from excerpting arbitrary local files).
def test_enumerate_rejects_symlink_escape_outside_claude_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # Real, legitimate skill inside ~/.claude
    _touch(tmp_path / ".claude/skills/legit/SKILL.md",
           "---\nname: legit\ndescription: real\n---\nreal body\n")
    # Hostile target outside ~/.claude with the right filename
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text(
        "---\nname: evil\ndescription: EXFIL\n---\nSECRET\n"
    )
    # Rogue symlink planted in the user skills root pointing outside
    link_dir = tmp_path / ".claude/skills/evil"
    link_dir.mkdir(parents=True)
    (link_dir / "SKILL.md").symlink_to(outside / "SKILL.md")

    inv = scan()
    # Legit skill is indexed; escape target is not
    assert "legit" in inv["skills"]
    assert "evil" not in inv["skills"]
    for e in inv["skills"].values():
        assert "SECRET" not in (e.get("body_excerpt") or "")
        assert "EXFIL" not in (e.get("description") or "")


# Finding #9: persisted stage records must use the 'stage' key — SKILL.md
# resume snippet reads p['stages'][idx]['stage'] and will KeyError otherwise.
def test_stage_records_expose_stage_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = create_run(task="t", sequence=["plan", "execute"])
    p = load_progress(rid)
    for row in p["stages"]:
        assert "stage" in row, "SKILL.md resume snippet depends on this key"
        assert "id" not in row, "no legacy 'id' alias; don't resurrect it"


# Corrupt preserved across apply_classification too — it uses the same lock.
def test_apply_on_corrupt_cache_does_not_lose_data(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _touch(tmp_path / ".claude/skills/x/SKILL.md", "---\nname: x\n---\n")
    scan()
    # apply while cache is corrupt: scan() will quarantine → apply sees fresh inv
    cache = tmp_path / ".claude/channels/assemble/inventory.json"
    cache.write_text("{broken")
    # Force rebuild so next apply has a real inv to mutate.
    scan()
    apply_classification("x", [{"stage": "plan", "role": "r"}],
                         confidence="high", reasoning="x")
    inv = scan()
    assert inv["skills"]["x"]["source"] == "llm-classified"
