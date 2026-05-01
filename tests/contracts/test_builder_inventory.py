"""Spike V Phase B — builder bundle inventory guard.
Mirrors tests/contracts/test_debugger_inventory.py."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"


def test_builder_in_inventory():
    from server.inventory import scan
    inv = scan(force=True)
    skills = inv.get("skills", {})
    builder = skills.get("builder")
    assert builder is not None, (
        f"builder skill missing from inventory; "
        f"scanned names: {sorted(skills.keys())}"
    )
    assert builder["bundled"] is True
    assert "description" in builder
    assert builder["path"].endswith("bundled/builder/SKILL.md")
