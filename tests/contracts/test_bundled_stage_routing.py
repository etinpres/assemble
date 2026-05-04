"""Spike V.2 — bundled ★ skills must surface in their declared stage menu.

Regression guard: B-10 dogfood Critical (2026-05-04) showed that V4
concierge layer was failing to recommend the builder ★ bundle for execute
tasks because heuristic classification scored description keywords too
strictly. The fix introduced two new resolution paths:

1. `frontmatter-declared` — `stages: [...]` field in SKILL.md frontmatter
   bypasses heuristic.
2. `bundled-dirhint` — bundled directory name fallback for skills missing
   the explicit field (e.g. `bundled/builder` → execute).

These tests verify the routing end-to-end via `build_stage_options()` so
that ★-prefixed bundle entries appear at the top of the user-facing menu.
"""

from server import scan, build_stage_options


def test_builder_appears_in_execute_menu():
    scan(force=True)
    opts = build_stage_options("execute")
    bundled = [o for o in opts if o.get("bundled")]
    assert bundled, "no bundled ★ entries in execute stage menu"
    names = [o.get("label", "") for o in bundled]
    assert any("builder" in name for name in names), (
        f"builder ★ missing from execute menu; bundled entries: {names}"
    )


def test_builder_is_first_in_execute_menu():
    """Bundled ★ entries are sorted before user/plugin tools in
    `build_stage_options`. builder must surface as the top recommendation
    when the user is on the execute stage."""
    scan(force=True)
    opts = build_stage_options("execute")
    assert opts, "execute menu is empty"
    first = opts[0]
    assert first.get("bundled") is True, (
        f"first execute option is not bundled: {first.get('label')}"
    )
    assert "builder" in first.get("label", ""), (
        f"first execute option is not builder: {first.get('label')}"
    )


def test_debugger_appears_in_debug_menu():
    scan(force=True)
    opts = build_stage_options("debug")
    bundled = [o for o in opts if o.get("bundled")]
    names = [o.get("label", "") for o in bundled]
    assert any("debugger" in n for n in names), (
        f"debugger ★ missing from debug menu; bundled entries: {names}"
    )


def test_plan_pack_appears_in_plan_menu():
    scan(force=True)
    opts = build_stage_options("plan")
    bundled = [o for o in opts if o.get("bundled")]
    names = [o.get("label", "") for o in bundled]
    assert any("plan-pack" in n for n in names), (
        f"plan-pack ★ missing from plan menu; bundled entries: {names}"
    )


def test_bundled_skills_have_frontmatter_declared_source():
    """All three bundled ★ skills declare `stages:` in frontmatter and
    should resolve via the explicit-frontmatter path, not heuristic."""
    inv = scan(force=True)
    for name in ("builder", "debugger", "plan-pack"):
        entry = inv["skills"].get(name)
        assert entry is not None, f"bundled skill {name!r} missing from inventory"
        assert entry.get("source") == "frontmatter-declared", (
            f"{name}: expected source='frontmatter-declared', "
            f"got {entry.get('source')!r}"
        )
        assert entry["mappings"], f"{name}: empty mappings"
        roles = {m.get("role") for m in entry["mappings"]}
        assert roles == {"frontmatter-declared"}, (
            f"{name}: mappings should all have role='frontmatter-declared', "
            f"got {roles}"
        )


def test_bundled_dirhint_fallback_when_no_frontmatter_stages(tmp_path, monkeypatch):
    """If a bundled skill ships without `stages:` frontmatter, the directory
    name → stage hint table provides a fallback. Sanity-checked against the
    canonical 3 bundles."""
    # Direct unit test against the dict — implementation detail test.
    from server.inventory import _BUNDLED_DIR_TO_STAGE
    assert _BUNDLED_DIR_TO_STAGE["builder"] == "execute"
    assert _BUNDLED_DIR_TO_STAGE["debugger"] == "debug"
    assert _BUNDLED_DIR_TO_STAGE["plan-pack"] == "plan"
