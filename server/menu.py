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
    return sorted(out, key=lambda x: (not x.get("bundled", False), x["name"]))


_META_KINDS = ["ask", "skip", "manual", "back", "done"]


def _meta_actions() -> list[dict]:
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
    no_desc = t("menu.no_description")
    helper_suffix = t("menu.helper_suffix")
    bundled_prefix = t("menu.bundled_prefix")
    fallback_hint = t("notices.bundled_only_hint")

    matched_tools = tools_for_stage(stage)
    # Loop var deliberately not named `t` — would shadow the i18n callable above.
    has_non_bundled = any(not tool_entry.get("bundled", False) for tool_entry in matched_tools)

    options: list[dict] = []
    seen_keys: set[str] = set()
    for tool in matched_tools:
        key = tool.get("path") or tool["name"]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        is_bundled = bool(tool.get("bundled", False))
        label = f"{bundled_prefix}{tool['name']}" if is_bundled else tool["name"]
        # 80-char cap is for the description body; the fallback hint may extend
        # past it because it carries the load-bearing signal in bundled-only menus.
        desc = (tool.get("description") or no_desc)[:80]
        if is_bundled and not has_non_bundled:
            desc = f"{desc} {fallback_hint}"
        options.append({
            "label": label,
            "kind": "tool",
            "description": desc,
            "tool_path": tool.get("path"),
            "bundled": is_bundled,
        })
    options.extend(_meta_actions())
    for helper in contextual_helpers(stage):
        key = helper.get("path") or helper["name"]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        options.append({
            "label": helper["name"],
            "kind": "helper",
            "description": (helper.get("description") or no_desc)[:80] + helper_suffix,
            "tool_path": helper.get("path"),
        })
    return options


def contextual_helpers(stage: str) -> list[dict]:
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
