import re
from pathlib import Path

SKILL_MD = Path(__file__).resolve().parents[2] / "bundled" / "shipper" / "SKILL.md"


def test_shipper_skill_md_exists():
    assert SKILL_MD.is_file()


def test_shipper_frontmatter_declares_ship_stage_inline():
    text = SKILL_MD.read_text()
    # inline form per Spike VI B1 fix — block-list form would be parsed as empty
    assert re.search(r'stages:\s*\[\s*"ship"\s*\]', text), 'stages: ["ship"] inline form required'


def test_shipper_appears_in_inventory_after_d2_wiring():
    """After Phase D2 lands _BUNDLED_DIR_TO_STAGE['shipper']='ship', inventory scan classifies shipper.

    NOTE: this test will pass only AFTER D2 wiring lands. Until then, expected to xfail or skip.
    Phase B/C task scope = create the SKILL.md; Phase D = wire harness/inventory.
    """
    import pytest

    pytest.skip("requires D2 wiring; will be enabled in Phase D2 commit")
