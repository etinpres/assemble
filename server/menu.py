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


META_ACTIONS = [
    {"label": "물어보기", "kind": "ask",
     "description": "자유 입력으로 Claude한테 추천 받기"},
    {"label": "skip",     "kind": "skip",
     "description": "이 단계 건너뛰기"},
    {"label": "직접",     "kind": "manual",
     "description": "내가 손으로 처리, 다음 stage로 진행"},
    {"label": "back",     "kind": "back",
     "description": "이전 stage로 돌아가기"},
    {"label": "done",     "kind": "done",
     "description": "여기서 종료"},
]


def build_stage_options(stage: str) -> list[dict]:
    options: list[dict] = []
    for t in tools_for_stage(stage):
        options.append({
            "label": t["name"],
            "kind": "tool",
            "description": (t.get("description") or "(설명 없음)")[:80],
            "tool_path": t.get("path"),
        })
    options.extend(META_ACTIONS)
    for h in contextual_helpers(stage):
        options.append({
            "label": h["name"],
            "kind": "helper",
            "description": (h.get("description") or "(설명 없음)")[:80] + "  [보조]",
            "tool_path": h.get("path"),
        })
    return options


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
