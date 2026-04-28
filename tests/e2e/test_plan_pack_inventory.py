"""plan-pack must be discoverable as a bundled, plan-stage tool the moment
its SKILL.md exists in the real repo. This test runs against the live
`~/.claude/skills/assemble/bundled/plan-pack/SKILL.md` (no tmp_path) and is
the inventory-side regression guard for Phase B-1.
"""
from pathlib import Path
from server import scan, build_stage_options, parse_skill_frontmatter


PLAN_PACK = Path.home() / ".claude/skills/assemble/bundled/plan-pack/SKILL.md"


def test_plan_pack_skill_md_exists():
    assert PLAN_PACK.exists(), f"missing: {PLAN_PACK}"


def test_plan_pack_frontmatter_parses():
    fm = parse_skill_frontmatter(PLAN_PACK)
    assert fm["name"] == "plan-pack"
    desc = (fm.get("description") or "").lower()
    assert "prd" in desc or "plan" in desc


def test_plan_pack_in_inventory_marked_bundled():
    inv = scan(force=True)
    entry = inv["skills"].get("plan-pack")
    assert entry is not None, list(inv["skills"])[:20]
    assert entry["bundled"] is True
    assert any(m["stage"] == "plan" for m in entry["mappings"]), entry["mappings"]


def test_plan_pack_in_plan_menu_with_star_prefix():
    opts = build_stage_options("plan")
    labels = [o["label"] for o in opts if o["kind"] == "tool"]
    assert "★ plan-pack" in labels, labels


def test_prd_template_exists_and_has_required_sections():
    tpl = PLAN_PACK.parent / "templates" / "PRD.md.template"
    assert tpl.exists(), f"missing: {tpl}"
    body = tpl.read_text()
    for required in ["## Goal", "## Users", "## Core features",
                     "## Excluded from MVP", "## Acceptance Criteria",
                     "## Design direction", "## Risks"]:
        assert required in body, f"section missing: {required!r}"
