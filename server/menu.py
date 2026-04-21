from server.inventory import scan, load_stage_roles


def _all_skills() -> dict:
    inv = scan()
    return {**inv["skills"], **inv["agents"]}


def tools_for_stage(stage: str) -> list[dict]:
    """Return every installed skill/agent mapped to the given stage."""
    out: list[dict] = []
    for name, entry in _all_skills().items():
        for m in entry.get("mappings", []):
            if m.get("stage") == stage:
                out.append({**entry, "role_in_stage": m.get("role")})
                break
    return sorted(out, key=lambda t: t["name"])


def contextual_helpers(stage: str) -> list[dict]:
    """Return safety/meta tools whose role matches stage_roles[stage]."""
    wanted = set(load_stage_roles().get(stage, []))
    if not wanted:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for name, entry in _all_skills().items():
        for m in entry.get("mappings", []):
            if m.get("stage") in {"safety", "meta"} and m.get("role") in wanted:
                if name not in seen:
                    out.append({**entry, "role_in_stage": m["role"]})
                    seen.add(name)
                break
    return sorted(out, key=lambda t: t["name"])
