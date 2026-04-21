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


import json

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_pre_mapping() -> dict[str, list[dict]]:
    return json.loads((CONFIG_DIR / "pre_mapping.json").read_text())


def load_stages() -> dict:
    return json.loads((CONFIG_DIR / "stages.json").read_text())


def load_stage_roles() -> dict[str, list[str]]:
    return json.loads((CONFIG_DIR / "stage_roles.json").read_text())


import os
from datetime import datetime
from server.state_store import write_json_atomic, read_json

INVENTORY_REL = ".claude/channels/assemble/inventory.json"

WATCH_PATHS = [
    ".claude/skills",
    ".claude/agents",
    ".claude/plugins/installed_plugins.json",
]


def _home_for_scan() -> Path:
    env = os.environ.get("ASSEMBLE_HOME")
    return Path(env) if env else Path.home()


def _inventory_path(home: Path) -> Path:
    return home / INVENTORY_REL


def _max_mtime(home: Path) -> float:
    best = 0.0
    for rel in WATCH_PATHS:
        p = home / rel
        if not p.exists():
            continue
        try:
            best = max(best, p.stat().st_mtime)
        except OSError:
            continue
        if p.is_dir():
            for sub in p.rglob("*"):
                try:
                    best = max(best, sub.stat().st_mtime)
                except OSError:
                    continue
    return best


def scan(force: bool = False) -> dict:
    home = _home_for_scan()
    cache = _inventory_path(home)
    if not force and cache.exists():
        cached = read_json(cache)
        if cached and cached.get("watched_mtime", 0) >= _max_mtime(home):
            return cached

    pre = load_pre_mapping()
    skills: dict[str, dict] = {}
    for path in enumerate_skill_paths(home):
        meta = parse_skill_frontmatter(path)
        name = meta["name"] or path.parent.name
        if name in skills:
            continue  # earliest path wins (user > plugin)
        if name in pre:
            mappings = pre[name]
            source = "pre-mapped"
        else:
            mappings = []
            source = "unclassified"
        skills[name] = {
            "name": name,
            "description": meta["description"],
            "body_excerpt": meta["body_excerpt"],
            "path": str(path),
            "mappings": mappings,
            "source": source,
        }

    agents: dict[str, dict] = {}
    for path in enumerate_agent_paths(home):
        name = path.stem
        agents[name] = {
            "name": name,
            "path": str(path),
            "mappings": pre.get(name, []),
            "source": "pre-mapped" if name in pre else "unclassified",
        }

    inv = {
        "version": 1,
        "generated_at": datetime.now().isoformat(),
        "watched_mtime": _max_mtime(home),
        "skills": skills,
        "agents": agents,
    }
    write_json_atomic(cache, inv)
    return inv


def apply_classification(name: str, mappings: list[dict],
                         confidence: str, reasoning: str) -> None:
    home = _home_for_scan()
    cache = _inventory_path(home)
    inv = read_json(cache)
    if not inv:
        return
    skill = inv["skills"].get(name)
    if not skill:
        return
    skill["mappings"] = mappings
    skill["source"] = "llm-classified"
    skill["classification"] = {"confidence": confidence, "reasoning": reasoning}
    inv["watched_mtime"] = _max_mtime(home)
    write_json_atomic(cache, inv)
