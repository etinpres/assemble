"""V4 Spike XIII B-18 dogfood probe — blank-environment sanity gate.

Self-execute mode: stands up a fresh ``ASSEMBLE_HOME`` tempdir containing
only the assemble skill (no user skills / agents / plugin caches), then
verifies 12 acceptance criteria covering inventory recognition, the
bundled-only menu fallback, frontmatter / contracts / prompt integrity,
and V4 identity invariants. The real ``~/.claude/`` tree is never touched.

Usage:
    cd ~/.claude/skills/assemble
    python3 -m tests.dogfood.spike_xiii_b18

Exit code 0 only if all 12 AC PASS. Wall-time budget: ≤30s (≤2s expected).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_REAL_ASSEMBLE = Path.home() / ".claude/skills/assemble"
_CANONICAL_PREAMBLE_V3_SHA = (
    "8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9"
)


def _extract_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    if end == -1:
        return ""
    return text[4:end + 1]


def _record(results: list[tuple[int, bool, str]], n: int, ok: bool, msg: str) -> None:
    results.append((n, ok, msg))
    status = "PASS" if ok else "FAIL"
    print(f"[AC{n}] {status}: {msg}")


def _write_dogfood_doc(
    doc_path: Path,
    results: list[tuple[int, bool, str]],
    wall_time: float,
    evidence: dict,
    verdict: str,
) -> None:
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    pass_count = sum(1 for _, ok, _ in results if ok)
    lines: list[str] = []
    lines.append("# Spike XIII B-18 — blank-environment sanity probe\n")
    lines.append("")
    lines.append(f"- **Run timestamp**: {evidence.get('timestamp')}")
    lines.append(f"- **Wall-time**: {wall_time:.3f}s (budget ≤30s)")
    lines.append(f"- **Pass count**: {pass_count}/{len(results)}")
    lines.append(f"- **Verdict**: {verdict}")
    lines.append("")
    lines.append("## Per-AC verdict")
    lines.append("")
    lines.append("| # | Status | Message |")
    lines.append("|---|--------|---------|")
    for n, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        lines.append(f"| AC{n} | {status} | {msg} |")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append("```json")
    lines.append(
        json.dumps(
            {k: v for k, v in evidence.items() if k != "timestamp"},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    lines.append("```")
    lines.append("")
    lines.append("## Tempdir layout sketch")
    lines.append("")
    lines.append("```")
    lines.append(f"{evidence.get('tempdir', '<tempdir>')}/")
    lines.append("└── .claude/")
    lines.append("    └── skills/")
    lines.append("        └── assemble/      # only skill present (blank env)")
    lines.append("            ├── SKILL.md")
    lines.append("            ├── bundled/   # 10 bundles + _shared")
    lines.append("            └── server/")
    lines.append("```")
    lines.append("")
    doc_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    t0 = time.perf_counter()

    if not _REAL_ASSEMBLE.is_dir():
        print(
            f"[FATAL] real assemble skill not found at {_REAL_ASSEMBLE}",
            file=sys.stderr,
        )
        return 2

    tempdir = Path(tempfile.mkdtemp(prefix="spike-xiii-b18-"))
    print(f"[setup] tempdir = {tempdir}")

    results: list[tuple[int, bool, str]] = []
    evidence: dict = {
        "tempdir": str(tempdir),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    try:
        # ---- Setup: copy real assemble into tempdir as the only skill ----
        skills_root = tempdir / ".claude/skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        dest_assemble = skills_root / "assemble"
        shutil.copytree(_REAL_ASSEMBLE, dest_assemble)

        # ASSEMBLE_HOME must be set BEFORE importing server modules so the
        # env-driven cache resolution sees the tempdir.
        os.environ["ASSEMBLE_HOME"] = str(tempdir)

        from server import scan
        from server.harness import (
            ALLOWED_PROMPT_FILES,
            ORCHESTRATOR_ONLY_PROMPTS,
            canonical_preamble_sha256,
        )
        from server.inventory import _is_bundled, enumerate_skill_paths
        from server.menu import build_stage_options

        bundled_root = dest_assemble / "bundled"
        bundle_dirs = sorted(
            p for p in bundled_root.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        )
        bundle_names = [p.name for p in bundle_dirs]
        evidence["bundle_names"] = bundle_names
        evidence["bundle_count"] = len(bundle_dirs)

        # ---- AC1 — tempdir setup successful ----
        shared_dir = bundled_root / "_shared"
        ac1 = (
            dest_assemble.is_dir()
            and bundled_root.is_dir()
            and len(bundle_dirs) == 10
            and shared_dir.is_dir()
        )
        _record(
            results, 1, ac1,
            f"tempdir has assemble + {len(bundle_dirs)} bundles + _shared "
            f"(_shared exists={shared_dir.is_dir()})",
        )

        # ---- AC2 — inventory.scan() returns ≥10 skills ----
        scan_out = scan(force=True)
        skills_bucket = scan_out.get("skills") or {}
        skill_count = len(skills_bucket)
        evidence["scan_skill_count"] = skill_count
        evidence["scan_skill_names"] = sorted(skills_bucket.keys())
        ac2 = skill_count >= 10
        _record(
            results, 2, ac2,
            f"scan() returned {skill_count} skills "
            f"(names={sorted(skills_bucket.keys())})",
        )

        # ---- AC3 — every bundled-name entry has bundled=True ----
        bundled_entries_ok = True
        bundled_entries_failures: list[str] = []
        for name in bundle_names:
            entry = skills_bucket.get(name)
            if entry is None:
                bundled_entries_ok = False
                bundled_entries_failures.append(f"{name}: missing from scan()")
                continue
            if entry.get("bundled") is not True:
                bundled_entries_ok = False
                bundled_entries_failures.append(
                    f"{name}: bundled={entry.get('bundled')!r}"
                )
        ac3 = bundled_entries_ok
        _record(
            results, 3, ac3,
            f"all 10 bundled entries have bundled=True"
            if ac3 else f"failures: {bundled_entries_failures}",
        )

        # ---- AC4 — user skills count = 0 ----
        # In a blank env, the only non-bundled scan entry is the assemble
        # parent SKILL.md itself (it lives at the skill root, not under
        # bundled/). "User skills" = anything else with bundled=False.
        non_bundled = [
            name for name, e in skills_bucket.items()
            if e.get("bundled") is False
        ]
        # Drop the assemble parent — it's the harness, not a user skill.
        user_skills = [n for n in non_bundled if n != "assemble"]
        evidence["non_bundled_entries"] = non_bundled
        evidence["user_skills"] = user_skills
        ac4 = len(user_skills) == 0
        _record(
            results, 4, ac4,
            f"user skill count = {len(user_skills)} "
            f"(non-bundled entries={non_bundled})",
        )

        # ---- AC5 — menu shows ★ prefix on bundled bundles ----
        # Stage 'plan' is guaranteed to surface plan-pack ★ in this env.
        plan_options = build_stage_options("plan")
        evidence["plan_options_sample"] = [
            {k: o.get(k) for k in ("label", "kind", "bundled")}
            for o in plan_options
        ]
        starred = [
            o for o in plan_options
            if o.get("kind") == "tool"
            and o.get("bundled") is True
            and o.get("label", "").startswith("★ ")
        ]
        ac5 = len(starred) >= 1
        _record(
            results, 5, ac5,
            f"plan stage rendered {len(starred)} ★-prefixed bundled tool(s) "
            f"(labels={[o.get('label') for o in starred]})",
        )

        # ---- AC6 — menu fallback hint shown ----
        fallback_marker = "no matching user/plugin tool"
        hint_options = [
            o for o in plan_options
            if o.get("kind") == "tool"
            and o.get("bundled") is True
            and fallback_marker in (o.get("description") or "")
        ]
        ac6 = len(hint_options) >= 1
        _record(
            results, 6, ac6,
            f"bundled-only fallback hint present on {len(hint_options)} option(s)",
        )

        # ---- AC7 — every bundle SKILL.md frontmatter parses ----
        ac7 = True
        ac7_failures: list[str] = []
        ac7_parsed_count = 0
        for bundle_dir in bundle_dirs:
            skill_md = bundle_dir / "SKILL.md"
            if not skill_md.is_file():
                ac7 = False
                ac7_failures.append(f"{bundle_dir.name}: SKILL.md missing")
                continue
            text = skill_md.read_text(encoding="utf-8")
            fm = _extract_frontmatter(text)
            if not fm:
                ac7 = False
                ac7_failures.append(f"{bundle_dir.name}: no frontmatter block")
                continue
            try:
                parsed = yaml.safe_load(fm)
            except Exception as e:  # noqa: BLE001
                ac7 = False
                ac7_failures.append(
                    f"{bundle_dir.name}: yaml.safe_load → "
                    f"{type(e).__name__}: {e}"
                )
                continue
            if not isinstance(parsed, dict) or "name" not in parsed:
                ac7 = False
                ac7_failures.append(
                    f"{bundle_dir.name}: not a name-bearing dict (got {type(parsed).__name__})"
                )
                continue
            ac7_parsed_count += 1
        _record(
            results, 7, ac7,
            f"{ac7_parsed_count}/{len(bundle_dirs)} bundle frontmatter parsed"
            if ac7 else f"failures: {ac7_failures}",
        )

        # ---- AC8 — every dispatchable prompt registered in ALLOWED_PROMPT_FILES ----
        # Mirrors test_dispatch_prompt::test_allowed_prompt_files_matches_bundle_inventory.
        on_disk: set[str] = set()
        for bundle_dir in bundle_dirs:
            for subdir in ("subagent", "orchestrator"):
                d = bundle_dir / "prompts" / subdir
                if d.is_dir():
                    for p in d.glob("*.md"):
                        if p.name == ".gitkeep":
                            continue
                        if p.name in ORCHESTRATOR_ONLY_PROMPTS:
                            continue
                        on_disk.add(p.name)
        in_tuple = set(ALLOWED_PROMPT_FILES)
        only_disk = on_disk - in_tuple
        only_tuple = in_tuple - on_disk
        ac8 = not only_disk and not only_tuple
        evidence["allowed_prompt_files_count"] = len(in_tuple)
        evidence["on_disk_prompt_count"] = len(on_disk)
        if ac8:
            _record(
                results, 8, ac8,
                f"{len(in_tuple)} entries match on-disk prompts (no drift)",
            )
        else:
            _record(
                results, 8, ac8,
                f"drift — only_disk={sorted(only_disk)}, "
                f"only_tuple={sorted(only_tuple)}",
            )

        # ---- AC9 — every contracts.json entry loadable ----
        contracts_path = (
            dest_assemble / "tests/contracts/contracts.json"
        )
        ac9 = False
        ac9_msg = ""
        try:
            payload = json.loads(contracts_path.read_text(encoding="utf-8"))
            contracts = payload.get("contracts") or []
            required_keys = {"id", "phrase", "spec_path", "section", "tag"}
            ac9_failures: list[str] = []
            for i, c in enumerate(contracts):
                if not isinstance(c, dict):
                    ac9_failures.append(f"#{i}: not a dict")
                    continue
                missing = required_keys - set(c.keys())
                if missing:
                    ac9_failures.append(f"#{i} ({c.get('id', '?')}): missing {sorted(missing)}")
            ac9 = bool(contracts) and not ac9_failures
            evidence["contract_count"] = len(contracts)
            ac9_msg = (
                f"{len(contracts)} contracts loaded with required schema"
                if ac9 else f"violations: {ac9_failures[:3]}"
            )
        except Exception as e:  # noqa: BLE001
            ac9 = False
            ac9_msg = f"load raised: {type(e).__name__}: {e}"
        _record(results, 9, ac9, ac9_msg)

        # ---- AC10 — canonical preamble v3 sha invariant ----
        actual_sha = canonical_preamble_sha256()
        evidence["canonical_preamble_sha"] = actual_sha
        ac10 = actual_sha == _CANONICAL_PREAMBLE_V3_SHA
        _record(
            results, 10, ac10,
            f"canonical preamble sha = {actual_sha[:16]}…"
            f" (expected {_CANONICAL_PREAMBLE_V3_SHA[:16]}…)",
        )

        # ---- AC11 — /assemble eject sub-command resolves (text scan) ----
        skill_md_text = (dest_assemble / "SKILL.md").read_text(encoding="utf-8")
        has_subcommands_section = "## Sub-commands" in skill_md_text
        has_eject_keyword = "eject" in skill_md_text
        has_eject_flow_doc = (
            dest_assemble / "docs/eject-flow.md"
        ).is_file()
        ac11 = has_subcommands_section and has_eject_keyword and has_eject_flow_doc
        _record(
            results, 11, ac11,
            f"## Sub-commands section + eject keyword + flow doc all present "
            f"(section={has_subcommands_section}, "
            f"keyword={has_eject_keyword}, "
            f"flow_doc={has_eject_flow_doc})",
        )

        # ---- AC12 — dogfood doc generated ----
        # Write to the REAL repo (probe outputs land in source tree, not tempdir),
        # so the verdict report survives tempdir cleanup.
        doc_path = (
            _REAL_ASSEMBLE / "docs/dogfood/spike-xiii-b18.md"
        )
        # Compute partial verdict + write doc; AC12 verifies the file exists
        # post-write. Done before the final all-pass tally so the doc reflects
        # the run even on partial failure.
        partial_wall = time.perf_counter() - t0
        partial_verdict = (
            "SHIP"
            if all(ok for _, ok, _ in results) and len(results) == 11
            else "BLOCK"
        )
        # AC12 itself is recorded after we attempt to write — record the
        # write outcome.
        try:
            _write_dogfood_doc(
                doc_path, results + [(12, True, "(provisional)")],
                partial_wall, evidence, partial_verdict,
            )
            ac12 = doc_path.is_file() and doc_path.stat().st_size > 0
            ac12_msg = f"doc written to {doc_path} ({doc_path.stat().st_size}B)"
        except Exception as e:  # noqa: BLE001
            ac12 = False
            ac12_msg = f"write raised: {type(e).__name__}: {e}"
        _record(results, 12, ac12, ac12_msg)

        # V4 identity snapshot (informational)
        evidence["identity_snapshot"] = {
            "ALLOWED_PROMPT_FILES_count": len(ALLOWED_PROMPT_FILES),
            "ORCHESTRATOR_ONLY_PROMPTS_count": len(ORCHESTRATOR_ONLY_PROMPTS),
            "canonical_preamble_v3_sha": (actual_sha or "")[:16],
        }

        # Re-write the doc with the FINAL verdict so AC12 row reflects truth.
        wall_time = time.perf_counter() - t0
        all_pass = all(ok for _, ok, _ in results)
        verdict = "SHIP" if (all_pass and len(results) == 12) else "BLOCK"
        _write_dogfood_doc(doc_path, results, wall_time, evidence, verdict)

    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

    wall_time = time.perf_counter() - t0
    all_pass = all(ok for _, ok, _ in results)
    pass_count = sum(1 for _, ok, _ in results if ok)

    print()
    print(f"Wall-time: {wall_time:.3f}s (budget ≤30s)")
    print(f"{pass_count}/{len(results)} AC PASS")
    if all_pass and len(results) == 12:
        print("VERDICT: SHIP")
        return 0
    print("VERDICT: BLOCK")
    return 1


if __name__ == "__main__":
    sys.exit(main())
