from pathlib import Path
from typing import Iterable


def _home(home: Path | None) -> Path:
    return Path(home) if home else Path.home()


def enumerate_skill_paths(home: Path | None = None) -> list[Path]:
    """Find every SKILL.md under user skills + plugin caches.

    Includes nested SKILL.md (gstack-style sub-skills). Returns absolute paths.
    """
    base = _home(home)
    roots = [
        base / ".claude" / "skills",
        base / ".claude" / "plugins" / "cache",
    ]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("SKILL.md"):
            seen.add(p.resolve())
    return sorted(seen)


def enumerate_agent_paths(home: Path | None = None) -> list[Path]:
    """Find every agent definition (.md) under user agents + plugin caches."""
    base = _home(home)
    roots = [
        base / ".claude" / "agents",
        base / ".claude" / "plugins" / "cache",
    ]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if root.name == "agents":
            for p in root.glob("*.md"):
                seen.add(p.resolve())
        else:
            for p in root.glob("*/*/*/agents/*.md"):
                seen.add(p.resolve())
    return sorted(seen)
