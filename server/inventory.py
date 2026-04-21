from pathlib import Path
from typing import Any, Iterable


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


EXCERPT_LEN = 500


def parse_skill_frontmatter(path: Path) -> dict[str, Any]:
    """Parse YAML-ish frontmatter into {name, description, body_excerpt}.

    Hand-rolled — no PyYAML dependency. Supports:
      - simple `key: value`
      - block style `key: |` with indented continuation
    """
    text = path.read_text()
    name: str | None = None
    description: str | None = None
    body_start = 0

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            block = text[4:end]
            body_start = end + len("\n---") + 1  # +1 for trailing newline
            name, description = _parse_yaml_ish(block)

    excerpt = text[body_start:body_start + EXCERPT_LEN].strip()
    return {"name": name, "description": description, "body_excerpt": excerpt}


def _parse_yaml_ish(block: str) -> tuple[str | None, str | None]:
    name: str | None = None
    desc_lines: list[str] | None = None
    in_desc_block = False
    for line in block.splitlines():
        if in_desc_block:
            if line.startswith("  "):
                desc_lines.append(line[2:])
                continue
            in_desc_block = False
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            val = line.split(":", 1)[1].strip()
            if val == "|":
                desc_lines = []
                in_desc_block = True
            else:
                desc_lines = [val.strip('"').strip("'")]
    description = " ".join(desc_lines).strip() if desc_lines is not None else None
    return name, description or None
