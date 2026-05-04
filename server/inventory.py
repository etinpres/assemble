from pathlib import Path
from typing import Any, Iterable


def _home(home: Path | None) -> Path:
    return Path(home) if home else Path.home()


USER_PRIORITY = 0
PLUGIN_PRIORITY = 1


def _under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def enumerate_skill_paths(home: Path | None = None) -> list[Path]:
    """Return SKILL.md paths ordered user > plugin.

    User skills come before plugin skills so `scan()`'s first-wins dedupe
    keeps the user version when names collide. Within a priority, sort by
    path string so enumeration is reproducible.

    Resolved paths that escape the `~/.claude` tree via symlink are rejected,
    so a rogue `~/.claude/skills/x -> /etc/passwd` doesn't get indexed or
    excerpted into inventory.json.
    """
    base = _home(home)
    claude_root = (base / ".claude").resolve()
    roots: list[tuple[Path, int]] = [
        (base / ".claude" / "skills", USER_PRIORITY),
        (base / ".claude" / "plugins" / "cache", PLUGIN_PRIORITY),
    ]
    by_path: dict[Path, int] = {}
    for root, prio in roots:
        if not root.exists():
            continue
        for p in root.rglob("SKILL.md"):
            rp = p.resolve()
            if not _under(rp, claude_root):
                continue
            existing = by_path.get(rp)
            if existing is None or prio < existing:
                by_path[rp] = prio
    return [p for p, _ in sorted(by_path.items(), key=lambda t: (t[1], str(t[0])))]


def enumerate_agent_paths(home: Path | None = None) -> list[Path]:
    """Return agent .md paths ordered user > plugin (first-wins precedence).

    Same symlink-escape guard as `enumerate_skill_paths`.
    """
    base = _home(home)
    claude_root = (base / ".claude").resolve()
    user_root = base / ".claude" / "agents"
    plugin_root = base / ".claude" / "plugins" / "cache"
    by_path: dict[Path, int] = {}
    if user_root.exists():
        for p in user_root.glob("*.md"):
            rp = p.resolve()
            if not _under(rp, claude_root):
                continue
            by_path[rp] = USER_PRIORITY
    if plugin_root.exists():
        for p in plugin_root.glob("*/*/*/agents/*.md"):
            rp = p.resolve()
            if not _under(rp, claude_root):
                continue
            existing = by_path.get(rp)
            if existing is None or PLUGIN_PRIORITY < existing:
                by_path[rp] = PLUGIN_PRIORITY
    return [p for p, _ in sorted(by_path.items(), key=lambda t: (t[1], str(t[0])))]


EXCERPT_LEN = 500


def parse_skill_frontmatter(path: Path) -> dict[str, Any]:
    """Parse YAML-ish frontmatter into {name, description, body_excerpt, stages}.

    Hand-rolled — no PyYAML dependency. Supports:
      - simple `key: value`
      - block style `key: |` with indented continuation
      - inline list `key: [a, b, c]` (V.2: used for `stages` field)

    `stages` is a list of stage ids (e.g. `[execute]`) — when present,
    bypasses the heuristic classifier in `scan()`. Authors of bundled
    skills can declare their stage routing explicitly without depending
    on description-keyword density.
    """
    text = path.read_text()
    name: str | None = None
    description: str | None = None
    stages: list[str] = []
    body_start = 0

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            block = text[4:end]
            body_start = end + len("\n---") + 1  # +1 for trailing newline
            name, description, stages = _parse_yaml_ish(block)

    excerpt = text[body_start:body_start + EXCERPT_LEN].strip()
    return {
        "name": name,
        "description": description,
        "body_excerpt": excerpt,
        "stages": stages,
    }


def _parse_yaml_ish(block: str) -> tuple[str | None, str | None, list[str]]:
    name: str | None = None
    desc_lines: list[str] | None = None
    in_desc_block = False
    stages: list[str] = []
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
        elif line.startswith("stages:"):
            val = line.split(":", 1)[1].strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if inner:
                    stages = [
                        s.strip().strip('"').strip("'")
                        for s in inner.split(",")
                        if s.strip()
                    ]
    description = " ".join(desc_lines).strip() if desc_lines is not None else None
    return name, description or None, stages


import json

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_stages() -> dict:
    """Return stage catalog, merged with the active locale's labels/descriptions.

    Shape preserved for callers:
      {
        "sequential": [{"id", "label", "desc"}, ...],
        "orthogonal": [{"id", "label", "desc"}, ...]
      }

    Stage ids live in `config/stages.json`; display strings come from
    `config/i18n/<locale>.json` (with en fallback). Missing locale data
    degrades to an empty label/desc so the skill still runs for beginners.
    """
    from server.i18n import tdict
    raw = json.loads((CONFIG_DIR / "stages.json").read_text())

    def _decorate(ids: list[str]) -> list[dict]:
        out: list[dict] = []
        for sid in ids:
            meta = tdict(f"stages.{sid}")
            out.append({
                "id": sid,
                "label": meta.get("label") or sid.capitalize(),
                "desc": meta.get("desc") or "",
            })
        return out

    return {
        "sequential": _decorate(raw.get("sequential", [])),
        "orthogonal": _decorate(raw.get("orthogonal", [])),
    }


def load_stage_roles() -> dict[str, list[str]]:
    return json.loads((CONFIG_DIR / "stage_roles.json").read_text())


# -------------------------------------------------------------------------
# Heuristic classifier (replaces pre_mapping.json)
#
# The legacy name-based pre-mapping table was retired on 2026-04-21 because
# you can't pre-map tools that aren't installed yet. Instead, each skill
# self-describes via its SKILL.md frontmatter (description + body), and we
# derive a stage from keyword hits. If the author wrote a good description
# the skill lands in a stage; if not, it's left as 'unclassified' for the
# LLM pass.
#
# Rule of thumb: require >=2 keyword hits before assigning a stage
# (reduces false positives).
# -------------------------------------------------------------------------

STAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "discover": ("brainstorm", "explore", "office hours", "find skill",
                 "discover", "ideation"),
    "plan":     ("plan", "spec", "requirements", "architect", "outline",
                 "design doc"),
    "design":   ("design system", "mockup", "ui design", "visual",
                 "brand", "color", "typography", "aesthetic",
                 "design variant", "design review"),
    "execute":  ("implement", "scaffold", "generate code", "build component",
                 "write code", "build app", "tdd"),
    "debug":    ("debug", "investigate", "root cause", "troubleshoot",
                 "bug", "stack trace", "why is"),
    "review":   ("code review", "pre-landing", "second opinion",
                 "review diff", "review this pr", "review the diff"),
    "verify":   ("qa", "test this site", "verify", "check accessibility",
                 "benchmark", "performance", "lighthouse", "test and fix",
                 "audit"),
    "ship":     ("ship", "deploy", "merge", "push to", "release",
                 "create pr", "canary", "land", "publish", "changelog"),
    "safety":   ("careful", "warn before", "destructive", "safety",
                 "guard", "restrict edits", "freeze", "lock down"),
    "meta":     ("checkpoint", "resume", "save state", "save progress",
                 "memory", "learnings", "recall", "retro", "session"),
}

# Role hints — role names MUST match those declared in stage_roles.json
# so contextual_helpers picks up the matching skill at stage time.
STAGE_ROLE_HINTS: list[tuple[str, tuple[str, ...], str]] = [
    ("meta",   ("checkpoint", "resume", "save state", "save progress"),
        "state-save"),
    ("meta",   ("memory", "recall", "session"),
        "prior-learning"),
    ("meta",   ("find skill", "discover skill"),
        "skill-discovery"),
    ("meta",   ("learnings", "retro"),
        "learning-capture"),
    ("safety", ("freeze", "restrict edits", "lock down"),
        "edit-scope-limit"),
    ("safety", ("careful", "warn", "destructive", "guard"),
        "dangerous-cmd-warn"),
]

MIN_HEURISTIC_HITS = 2


def _classify_heuristic(meta: dict) -> list[dict]:
    """Infer stage candidates from SKILL.md frontmatter + early body.

    Returns empty list if confidence is low — caller should keep 'unclassified'
    and let LLM classification handle it later.
    """
    desc = (meta.get("description") or "").lower()
    body = (meta.get("body_excerpt") or "").lower()
    text = f"{desc} {body}"
    if not text.strip():
        return []

    stage_hits: dict[str, int] = {}
    for stage, kws in STAGE_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text)
        if score >= MIN_HEURISTIC_HITS:
            stage_hits[stage] = score
    if not stage_hits:
        return []

    mappings: list[dict] = []
    for stage, _ in sorted(stage_hits.items(), key=lambda t: -t[1]):
        role = "auto-heuristic"
        for role_stage, role_kws, role_name in STAGE_ROLE_HINTS:
            if role_stage == stage and any(kw in text for kw in role_kws):
                role = role_name
                break
        mappings.append({"stage": stage, "role": role})
    return mappings


import os
import sys
from datetime import datetime
from server.state_store import write_json_atomic, read_json, update_json_locked

INVENTORY_REL = ".claude/channels/assemble/inventory.json"

WATCH_PATHS = [
    ".claude/skills",
    ".claude/agents",
    ".claude/plugins/installed_plugins.json",
]

_BUNDLED_ROOT_REL = ".claude/skills/assemble/bundled"


# V.2 — bundled directory → default stage. Used as a last-resort fallback
# in `_resolve()` for bundled skills that didn't declare an explicit
# `stages:` list in their SKILL.md frontmatter. Each bundled bundle
# already documents its stage in its directory name (`builder` is
# execute-stage, `debugger` is debug-stage, `plan-pack` is plan-stage),
# so this fallback keeps blank-mac dogfood usable even when authors
# forget the frontmatter field.
# This map is the scan-time fallback for bundles that omit `stages:` in
# their SKILL.md frontmatter. Mirrored by `server.harness._BUNDLED_DIR_TO_STAGE`
# (which is for harness-level dispatch routing). The two MUST stay in sync
# for any bundle whose frontmatter might drop `stages:`.
# A1 carryforward (Spike VIII): see also `server.harness._BUNDLED_DIR_TO_STAGE`.
# Convention going forward (Spike IX onward): every shipped bundle gets a
# defensive entry here as a scan-time fallback, regardless of whether its
# SKILL.md declares `stages:` inline. The map is cheap and prevents silent
# "unclassified" drift if a future SKILL.md edit drops the frontmatter field.
# Historical note: "verifier" (Spike VIII) was deliberately omitted because
# its SKILL.md declares `stages: ["verify"]` explicitly; if verifier ever
# drops `stages:`, ADD `"verifier": "verify"` here to prevent unclassified.
_BUNDLED_DIR_TO_STAGE: dict[str, str] = {
    "builder": "execute",
    "debugger": "debug",
    "plan-pack": "plan",
    "reviewer": "review",
    "shipper": "ship",
}


def _is_bundled(home: Path, resolved_path: Path) -> bool:
    """True iff the skill/agent file lives under the assemble bundled root.

    `resolved_path` must already be `Path.resolve()`d by the caller (which
    `enumerate_skill_paths` does). We resolve the bundle root the same way
    so a symlinked HOME still matches.
    """
    bundled_root = (home / _BUNDLED_ROOT_REL).resolve()
    try:
        resolved_path.relative_to(bundled_root)
        return True
    except ValueError:
        return False


def _home_for_scan() -> Path:
    env = os.environ.get("ASSEMBLE_HOME")
    return Path(env) if env else Path.home()


def _bundled_only_active() -> bool:
    """True iff ``ASSEMBLE_BUNDLED_ONLY=1`` is set in the environment.

    Used by :func:`scan` to filter path enumeration results down to entries
    that live under the assemble bundled root, simulating a "blank Mac" with
    no user/plugin skills installed. The flag is a simulation aid for
    blank-Mac dogfood gates; it does not affect classification cache state.
    """
    return os.environ.get("ASSEMBLE_BUNDLED_ONLY") == "1"


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


def _quarantine_corrupt_cache(cache: Path) -> None:
    """Quarantine a corrupt inventory.json as `.bad-<ts>` and rebuild.

    The bad file is kept next to the cache (not deleted) so it can be
    inspected later. /assemble is one-shot, so forcing operator intervention
    would block the skill — quarantine + rebuild is the right default.
    """
    try:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = cache.with_name(cache.name + f".bad-{ts}")
        cache.rename(backup)
        print(f"[assemble] corrupt inventory cache quarantined → {backup}",
              file=sys.stderr)
    except OSError as e:
        print(f"[assemble] failed to quarantine corrupt cache: {e}",
              file=sys.stderr)


def scan(force: bool = False) -> dict:
    home = _home_for_scan()
    cache = _inventory_path(home)
    bundled_only = _bundled_only_active()

    # Fast path: cache valid and no watched path changed → return without locking.
    # When ASSEMBLE_BUNDLED_ONLY=1 is set, the cache is bypassed (it may carry
    # entries written by a prior non-flag scan); the in-memory rebuild is
    # returned without persisting back to disk so the cache stays clean for
    # later non-flag callers.
    if not bundled_only and not force and cache.exists():
        cached = read_json(cache)
        if cached is None:
            # File present but unparseable → corrupt. Quarantine before locking.
            _quarantine_corrupt_cache(cache)
        elif cached.get("watched_mtime", 0) >= _max_mtime(home):
            return cached

    # Slow path: rebuild under the lock. `scan()` and `apply_classification()`
    # share `update_json_locked`, so neither writer clobbers the other.
    def _rebuild(prior: dict) -> dict:
        prior = prior or {}
        prior_skills = (prior.get("skills") or {})
        prior_agents = (prior.get("agents") or {})

        def _resolve(
            prior_entry: dict, meta: dict, *, bundled: bool, dir_name: str
        ) -> tuple[list, str]:
            # User/LLM classification wins — preserved across rebuilds.
            if prior_entry.get("source") == "llm-classified":
                return prior_entry.get("mappings", []), "llm-classified"
            # V.2: explicit `stages` in SKILL.md frontmatter bypasses the
            # heuristic. Bundled ★ skills declare their stage routing this
            # way so they don't depend on description-keyword density.
            declared = meta.get("stages") or []
            if declared:
                mappings = [
                    {"stage": s, "role": "frontmatter-declared"}
                    for s in declared
                ]
                return mappings, "frontmatter-declared"
            # V.2: bundled fallback — directory name → stage hint, for
            # bundled skills that didn't declare `stages` explicitly.
            if bundled and dir_name in _BUNDLED_DIR_TO_STAGE:
                stage = _BUNDLED_DIR_TO_STAGE[dir_name]
                return [{"stage": stage, "role": "bundled-dirhint"}], "bundled-dirhint"
            # Recompute the frontmatter-based heuristic every rebuild so
            # description edits are reflected. Cache hits skip _rebuild entirely.
            heuristic = _classify_heuristic(meta)
            if heuristic:
                return heuristic, "heuristic-classified"
            return [], "unclassified"

        skill_paths = enumerate_skill_paths(home)
        agent_paths = enumerate_agent_paths(home)
        if bundled_only:
            skill_paths = [p for p in skill_paths if _is_bundled(home, p)]
            agent_paths = [p for p in agent_paths if _is_bundled(home, p)]

        skills: dict[str, dict] = {}
        for path in skill_paths:
            meta = parse_skill_frontmatter(path)
            name = meta["name"] or path.parent.name
            if name in skills:
                continue  # user > plugin, first-wins (enumerate returns priority order)
            prior_entry = prior_skills.get(name) or {}
            is_bundled = _is_bundled(home, path)
            mappings, source = _resolve(
                prior_entry, meta, bundled=is_bundled, dir_name=path.parent.name
            )
            entry = {
                "name": name,
                "description": meta["description"],
                "body_excerpt": meta["body_excerpt"],
                "path": str(path),
                "bundled": is_bundled,
                "mappings": mappings,
                "source": source,
            }
            if prior_entry.get("classification"):
                entry["classification"] = prior_entry["classification"]
            skills[name] = entry

        agents: dict[str, dict] = {}
        for path in agent_paths:
            name = path.stem
            if name in agents:
                continue  # user > plugin, first-wins (same rule as skills)
            meta = parse_skill_frontmatter(path)  # agent .md shares the YAML frontmatter convention
            prior_entry = prior_agents.get(name) or {}
            is_bundled = _is_bundled(home, path)
            mappings, source = _resolve(
                prior_entry, meta, bundled=is_bundled, dir_name=path.parent.name
            )
            entry = {
                "name": name,
                "description": meta["description"],
                "body_excerpt": meta["body_excerpt"],
                "path": str(path),
                "bundled": is_bundled,
                "mappings": mappings,
                "source": source,
            }
            if prior_entry.get("classification"):
                entry["classification"] = prior_entry["classification"]
            agents[name] = entry

        return {
            "version": 1,
            "generated_at": datetime.now().isoformat(),
            "watched_mtime": _max_mtime(home),
            "skills": skills,
            "agents": agents,
        }

    if bundled_only:
        # In-memory rebuild only — do not persist the filtered view to cache.
        prior = read_json(cache) if cache.exists() else None
        return _rebuild(prior or {})
    return update_json_locked(cache, _rebuild)


CLASSIFICATIONS_LOG_REL = ".claude/channels/assemble/classifications.jsonl"


def _classifications_log_path(home: Path) -> Path:
    return home / CLASSIFICATIONS_LOG_REL


def apply_classification(name: str, mappings: list[dict],
                         confidence: str, reasoning: str) -> None:
    """Apply an LLM classification result to the inventory.

    Looks up `name` in both skill and agent buckets. Shares the same
    `update_json_locked` path as `scan()` so simultaneous apply/rescan calls
    cannot lose each other's writes.
    """
    home = _home_for_scan()
    cache = _inventory_path(home)
    applied: dict = {}

    def _upd(inv: dict) -> dict:
        if not inv:
            return inv
        entry = (inv.get("skills") or {}).get(name) \
             or (inv.get("agents") or {}).get(name)
        if not entry:
            return inv
        applied["prev_mappings"] = entry.get("mappings", [])
        applied["prev_source"] = entry.get("source")
        entry["mappings"] = mappings
        entry["source"] = "llm-classified"
        entry["classification"] = {"confidence": confidence, "reasoning": reasoning}
        inv["watched_mtime"] = _max_mtime(home)
        return inv

    update_json_locked(cache, _upd)

    if applied:
        # Append audit entry (best-effort, never raise)
        try:
            log_path = _classifications_log_path(home)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": datetime.now().isoformat(),
                "name": name,
                "mappings": mappings,
                "confidence": confidence,
                "reasoning": reasoning,
                "prev_mappings": applied.get("prev_mappings", []),
                "prev_source": applied.get("prev_source"),
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def unclassified_names() -> list[str]:
    """Return unclassified names from the skills bucket only (back-compat)."""
    home = _home_for_scan()
    inv = read_json(_inventory_path(home)) or {"skills": {}}
    return sorted(name for name, e in (inv.get("skills") or {}).items()
                  if e.get("source") == "unclassified")


def unclassified_entries() -> list[dict]:
    """Return `{kind, name, path}` for every unclassified skill and agent.

    Lets `bin/classify-inventory` build classification prompts for agents
    (not only skills).
    """
    home = _home_for_scan()
    inv = read_json(_inventory_path(home)) or {"skills": {}, "agents": {}}
    out: list[dict] = []
    for kind, bucket in (("skill", inv.get("skills") or {}),
                         ("agent", inv.get("agents") or {})):
        for name, e in bucket.items():
            if e.get("source") == "unclassified":
                out.append({"kind": kind, "name": name, "path": e.get("path")})
    out.sort(key=lambda x: (x["kind"], x["name"]))
    return out
