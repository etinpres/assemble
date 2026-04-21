from server.inventory import scan, load_stage_roles
from server.i18n import tdict, t


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
    return sorted(out, key=lambda x: x["name"])


_META_KINDS = ["ask", "skip", "manual", "back", "done"]


def _meta_actions() -> list[dict]:
    """Localized meta-action menu entries.

    Rebuilt each call so a locale change (e.g. tests switching env vars)
    is observed without reimporting.
    """
    actions: list[dict] = []
    for kind in _META_KINDS:
        entry = tdict(f"menu.{kind}")
        actions.append({
            "label": entry.get("label") or kind,
            "kind": kind,
            "description": entry.get("description") or "",
        })
    return actions


def build_stage_options(stage: str) -> list[dict]:
    """Tool + meta actions + safety/meta helpers, merged into one menu.

    If the same skill is both directly mapped to this stage AND tagged as a
    contextual helper (via meta/safety role), surface it once under `tool`
    and drop the helper duplicate.
    """
    no_desc = t("menu.no_description")
    helper_suffix = t("menu.helper_suffix")
    options: list[dict] = []
    seen_keys: set[str] = set()
    for tool in tools_for_stage(stage):
        key = tool.get("path") or tool["name"]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        options.append({
            "label": tool["name"],
            "kind": "tool",
            "description": (tool.get("description") or no_desc)[:80],
            "tool_path": tool.get("path"),
        })
    options.extend(_meta_actions())
    for helper in contextual_helpers(stage):
        key = helper.get("path") or helper["name"]
        if key in seen_keys:
            continue  # already surfaced as a tool — avoid duplicate
        seen_keys.add(key)
        options.append({
            "label": helper["name"],
            "kind": "helper",
            "description": (helper.get("description") or no_desc)[:80] + helper_suffix,
            "tool_path": helper.get("path"),
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
    return sorted(out, key=lambda x: x["name"])
