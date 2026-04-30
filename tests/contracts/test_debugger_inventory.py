"""Phase C guard — inventory scanner exposes debugger entry with
bundled=True. Mirrors the Phase A `_is_bundled` check that was added
for plan-pack.

NOTE: server.inventory.scan() returns a dict with shape
  {"skills": {name: entry, ...}, "agents": {...}, ...}
The plan spec assumed a scan_skills() returning a list; adjusted here
to match the actual API.

ASSEMBLE_HOME must NOT be overridden here — the scanner must resolve
against the real home so it finds the real bundled/ tree.
"""

from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"


def test_debugger_in_inventory():
    from server.inventory import scan  # actual scanner
    inv = scan(force=True)
    skills = inv.get("skills", {})
    debugger = skills.get("debugger")
    assert debugger is not None, (
        f"debugger skill missing from inventory; "
        f"scanned names: {sorted(skills.keys())}"
    )
    assert debugger["bundled"] is True
    # Light shape check — full schema is verified in Phase C7.
    assert "description" in debugger
    assert debugger["path"].endswith("bundled/debugger/SKILL.md")
