from pathlib import Path
from server.inventory import scan, apply_classification
from server.menu import build_stage_options
from server.progress import create_run, mark_stage, load_progress, find_resumable


def _touch(p: Path, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_concierge_happy_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))

    # Pre-populate with richly-described skills (heuristic catches stages) + 1 ambiguous
    _touch(tmp_path / ".claude/skills/my-planner/SKILL.md",
           "---\nname: my-planner\n"
           "description: Plan from a spec or requirements before writing code\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/freeze/SKILL.md",
           "---\nname: freeze\n"
           "description: Freeze edits, restrict edits to a folder, lock down\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/checkpoint/SKILL.md",
           "---\nname: checkpoint\n"
           "description: Save state and save progress, checkpoint and resume\n"
           "---\n")
    _touch(tmp_path / ".claude/skills/odd-skill/SKILL.md",
           "---\nname: odd-skill\ndescription: mystery unclear purpose\n---\n")

    inv = scan()
    assert "my-planner" in inv["skills"]
    assert inv["skills"]["odd-skill"]["source"] == "unclassified"

    # Simulate the LLM classifying odd-skill (heuristic missed it → LLM falls through)
    apply_classification("odd-skill",
                         [{"stage": "execute", "role": "mystery-helper"}],
                         confidence="medium",
                         reasoning="best guess from description")

    # Approve a sequence
    rid = create_run(task="prototype tool", sequence=["plan","execute"])

    # Plan stage — heuristic puts my-planner in the plan stage
    plan_opts = [o["label"] for o in build_stage_options("plan")]
    assert "my-planner" in plan_opts
    assert "checkpoint" in plan_opts  # contextual helper via state-save role
    mark_stage(rid, "plan", status="done", tool_used="my-planner")

    # Execute stage — odd-skill (just classified) should now appear
    exec_opts = [o["label"] for o in build_stage_options("execute")]
    assert "odd-skill" in exec_opts
    assert "freeze" in exec_opts  # contextual safety helper for execute
    mark_stage(rid, "execute", status="done", tool_used="odd-skill")

    final = load_progress(rid)
    assert [s["status"] for s in final["stages"]] == ["done","done"]
    # Run is complete → not resumable
    assert rid not in find_resumable()
