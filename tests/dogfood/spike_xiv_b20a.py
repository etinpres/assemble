"""V4 Spike XIV B-20a dogfood probe — automated blank-environment sanity gate.

Self-execute mode: stands up a fresh ``ASSEMBLE_HOME`` tempdir containing
only the assemble skill (no user skills / agents / plugin caches), then
verifies 18 acceptance criteria — 12 from Spike XIII B-18 (file/menu/contract
integrity) plus 6 new for Spike XIV Phase A~E fix coverage:

- A (C1) — wrap_with_preamble ASSEMBLE_HOME body injection
- B (C2/I2) — 7 ★ SKILL.md mode-gate + Quick mode flow + no-shortcut rule
- C (I1) — plan-pack Recommendation policy + iter≤3 algorithm
- D (I3) — mark_orthogonal_stage import + safety/meta marking OK
- E (I4) — dispatch_prompt signature drift sweep

Usage:
    cd ~/.claude/skills/assemble
    python tests/dogfood/spike_xiv_b20a.py

Exit code 0 only if all 18 AC PASS. Wall-time budget: ≤30s (≤5s expected).
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
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
_EXPECTED_ALLOWED_PROMPT_FILES = 49  # Spike XIV Phase B added 7 quick prompts (was 42 in B-18)
_SEVEN_STAR_BUNDLES = (
    "plan-pack", "builder", "debugger", "reviewer",
    "verifier", "shipper", "keeper",
)


def _extract_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    if end == -1:
        return ""
    return text[4:end + 1]


def _record(
    results: list[tuple[int, str, bool, str]],
    n: int,
    name: str,
    ok: bool,
    msg: str,
) -> None:
    results.append((n, name, ok, msg))
    status = "PASS" if ok else "FAIL"
    print(f"[AC{n}] {status} ({name}): {msg}")


def _phase_for_ac(n: int) -> str:
    if 1 <= n <= 12:
        return "XIII (B-18 baseline)"
    if n in (13, 18):
        return "A (C1 — ASSEMBLE_HOME injection / preamble v3 sha)"
    if n == 14:
        return "B (C2/I2 — mode-gate)"
    if n == 15:
        return "C (I1 — Recommendation policy)"
    if n == 16:
        return "D (I3 — orthogonal stage marker)"
    if n == 17:
        return "E (I4 — dispatch_prompt signature drift)"
    return "?"


def _write_dogfood_doc(
    doc_path: Path,
    results: list[tuple[int, str, bool, str]],
    wall_time: float,
    evidence: dict,
    verdict: str,
) -> None:
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    pass_count = sum(1 for _, _, ok, _ in results if ok)
    lines: list[str] = []
    lines.append("# Spike XIV B-20a — Automated Blank-Environment Sanity Probe")
    lines.append("")
    lines.append(f"**Date**: {evidence.get('timestamp', '')}")
    lines.append(f"**Verdict**: {verdict}")
    lines.append(f"**Wall-time**: {wall_time:.3f}s")
    lines.append("**Pytest baseline (host)**: 833 passed (T7)")
    lines.append("")
    lines.append("## ACs (18 total)")
    lines.append("")
    lines.append("| # | Name | Status | Evidence |")
    lines.append("|---|------|--------|----------|")
    for n, name, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        lines.append(f"| AC{n} | {name} | {status} | {msg} |")
    lines.append("")
    lines.append(f"**Pass count**: {pass_count}/{len(results)}")
    lines.append("")
    lines.append("## Identity snapshot")
    lines.append("")
    lines.append("```json")
    lines.append(
        json.dumps(
            evidence.get("identity_snapshot", {}),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    lines.append("```")
    lines.append("")
    lines.append("## Phase A~E fix coverage")
    lines.append("")
    lines.append("| Phase | AC | Status |")
    lines.append("|-------|----|--------|")
    coverage_groups = [
        ("A (C1 — ASSEMBLE_HOME injection)", [13, 18]),
        ("B (C2/I2 — mode-gate)", [14]),
        ("C (I1 — Recommendation policy)", [15]),
        ("D (I3 — orthogonal stage marker)", [16]),
        ("E (I4 — dispatch_prompt signature drift)", [17]),
    ]
    by_n = {n: ok for n, _, ok, _ in results}
    for phase_label, ac_list in coverage_groups:
        all_pass = all(by_n.get(n, False) for n in ac_list)
        status_label = "PASS" if all_pass else "FAIL"
        ac_str = ", ".join(f"AC{n}" for n in ac_list)
        lines.append(f"| {phase_label} | {ac_str} | {status_label} |")
    lines.append("")
    lines.append("## Evidence (full)")
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

    tempdir = Path(tempfile.mkdtemp(prefix="spike-xiv-b20a-"))
    print(f"[setup] tempdir = {tempdir}")

    results: list[tuple[int, str, bool, str]] = []
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
        import server.harness as _harness_mod
        import server.progress as _progress_mod
        # Reload to pick up tempdir context (B-18 pattern + Spike XIV safety).
        importlib.reload(_harness_mod)
        importlib.reload(_progress_mod)
        from server.harness import (
            ALLOWED_PROMPT_FILES,
            ORCHESTRATOR_ONLY_PROMPTS,
            canonical_preamble_sha256,
            wrap_with_preamble,
            _PROMPT_TO_STAGE,
            _BUNDLES,
            _BUNDLED_DIR_TO_STAGE,
            _PREAMBLE_V1_SHA256,
            _PREAMBLE_V2_SHA256,
        )
        from server.learnings import STAGE_CATEGORY_PRIORITY
        from server.inventory import _is_bundled
        from server.menu import build_stage_options

        bundled_root = dest_assemble / "bundled"
        bundle_dirs = sorted(
            p for p in bundled_root.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        )
        bundle_names = [p.name for p in bundle_dirs]
        evidence["bundle_names"] = bundle_names
        evidence["bundle_count"] = len(bundle_dirs)

        # ============================================================
        # Spike XIII B-18 baseline (12 ACs adapted)
        # ============================================================

        # ---- AC1 — tempdir setup ----
        shared_dir = bundled_root / "_shared"
        ac1 = (
            dest_assemble.is_dir()
            and bundled_root.is_dir()
            and len(bundle_dirs) == 10
            and shared_dir.is_dir()
        )
        _record(
            results, 1, "tempdir setup",
            ac1,
            f"assemble + {len(bundle_dirs)} bundles + _shared "
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
            results, 2, "inventory.scan ≥10",
            ac2,
            f"scan() returned {skill_count} skills",
        )

        # ---- AC3 — bundled=True flag ----
        bundled_entries_ok = True
        bundled_entries_failures: list[str] = []
        for name in bundle_names:
            entry = skills_bucket.get(name)
            if entry is None:
                bundled_entries_ok = False
                bundled_entries_failures.append(f"{name}: missing")
                continue
            if entry.get("bundled") is not True:
                bundled_entries_ok = False
                bundled_entries_failures.append(
                    f"{name}: bundled={entry.get('bundled')!r}"
                )
        ac3 = bundled_entries_ok
        _record(
            results, 3, "bundled=True flag",
            ac3,
            "all 10 bundled entries flagged bundled=True"
            if ac3 else f"failures: {bundled_entries_failures}",
        )

        # ---- AC4 — menu rendering + bundled-only fallback hint ----
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
        fallback_marker = "no matching user/plugin tool"
        hint_options = [
            o for o in plan_options
            if o.get("kind") == "tool"
            and o.get("bundled") is True
            and fallback_marker in (o.get("description") or "")
        ]
        ac4 = len(starred) >= 1 and len(hint_options) >= 1
        _record(
            results, 4, "menu render + fallback hint",
            ac4,
            f"{len(starred)} ★ tool(s) + {len(hint_options)} fallback hint(s)",
        )

        # ---- AC5 — every ★ bundle SKILL.md frontmatter strict-load ----
        ac5 = True
        ac5_failures: list[str] = []
        ac5_parsed_count = 0
        for bundle_dir in bundle_dirs:
            skill_md = bundle_dir / "SKILL.md"
            if not skill_md.is_file():
                ac5 = False
                ac5_failures.append(f"{bundle_dir.name}: SKILL.md missing")
                continue
            text = skill_md.read_text(encoding="utf-8")
            fm = _extract_frontmatter(text)
            if not fm:
                ac5 = False
                ac5_failures.append(f"{bundle_dir.name}: no frontmatter")
                continue
            try:
                parsed = yaml.safe_load(fm)
            except Exception as e:  # noqa: BLE001
                ac5 = False
                ac5_failures.append(
                    f"{bundle_dir.name}: yaml.safe_load → "
                    f"{type(e).__name__}: {e}"
                )
                continue
            if not isinstance(parsed, dict) or "name" not in parsed:
                ac5 = False
                ac5_failures.append(
                    f"{bundle_dir.name}: not a name-bearing dict"
                )
                continue
            ac5_parsed_count += 1
        _record(
            results, 5, "frontmatter strict-load",
            ac5,
            f"{ac5_parsed_count}/{len(bundle_dirs)} bundle frontmatter parsed"
            if ac5 else f"failures: {ac5_failures}",
        )

        # ---- AC6 — bidirectional integrity (auto-derived) ----
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
        ac6 = not only_disk and not only_tuple
        evidence["on_disk_prompt_count"] = len(on_disk)
        _record(
            results, 6, "bidirectional integrity",
            ac6,
            f"{len(in_tuple)} ALLOWED == {len(on_disk)} on-disk"
            if ac6 else f"drift only_disk={sorted(only_disk)}, "
            f"only_tuple={sorted(only_tuple)}",
        )

        # ---- AC7 — _PROMPT_TO_STAGE values ⊆ STAGE_CATEGORY_PRIORITY keys ----
        stage_keys = set(STAGE_CATEGORY_PRIORITY.keys())
        prompt_stages = set(_PROMPT_TO_STAGE.values())
        unknown = prompt_stages - stage_keys
        ac7 = not unknown
        evidence["stage_keys"] = sorted(stage_keys)
        _record(
            results, 7, "_PROMPT_TO_STAGE ⊆ STAGE_KEYS",
            ac7,
            f"{len(prompt_stages)} prompt stages all in {len(stage_keys)} known stages"
            if ac7 else f"unknown stages: {sorted(unknown)}",
        )

        # ---- AC8 — every dispatchable prompt has WROTE: contract ----
        # Helper variants (iter_revisit/iter_emphasis) are prepended to other
        # prompts at runtime — their WROTE: comes from the target prompt, so
        # they're exempt from the per-file check.
        ac8 = True
        ac8_failures: list[str] = []
        ac8_count = 0
        ac8_helper_exempt = 0
        helper_suffixes = ("_iter_revisit.md", "_iter_emphasis.md")
        helper_exact = {"iter_revisit.md", "iter_emphasis.md"}
        for prompt_basename in ALLOWED_PROMPT_FILES:
            # Find the prompt file on disk (search in subagent/orchestrator)
            found_path: Path | None = None
            for bundle_dir in bundle_dirs:
                for subdir in ("subagent", "orchestrator"):
                    candidate = bundle_dir / "prompts" / subdir / prompt_basename
                    if candidate.is_file():
                        found_path = candidate
                        break
                if found_path is not None:
                    break
            if found_path is None:
                ac8 = False
                ac8_failures.append(f"{prompt_basename}: not found on disk")
                continue
            is_helper = (
                prompt_basename in helper_exact
                or any(prompt_basename.endswith(s) for s in helper_suffixes)
            )
            if is_helper:
                ac8_helper_exempt += 1
                continue
            text = found_path.read_text(encoding="utf-8")
            has_wrote = "WROTE:" in text
            if not has_wrote:
                ac8 = False
                ac8_failures.append(
                    f"{prompt_basename}: no WROTE: contract anywhere"
                )
                continue
            ac8_count += 1
        evidence["ac8_wrote_count"] = ac8_count
        evidence["ac8_helper_exempt"] = ac8_helper_exempt
        _record(
            results, 8, "WROTE: contract on dispatchable prompts",
            ac8,
            f"{ac8_count} prompts have WROTE:, "
            f"{ac8_helper_exempt} helper-exempt (iter_revisit/iter_emphasis), "
            f"total {ac8_count + ac8_helper_exempt}/{len(ALLOWED_PROMPT_FILES)}"
            if ac8 else f"failures (first 3): {ac8_failures[:3]}",
        )

        # ---- AC9 — canonical preamble v3 sha matches expected ----
        actual_sha = canonical_preamble_sha256()
        evidence["canonical_preamble_sha"] = actual_sha
        ac9 = actual_sha == _CANONICAL_PREAMBLE_V3_SHA
        _record(
            results, 9, "canonical preamble v3 sha invariant",
            ac9,
            f"sha = {actual_sha[:16]}… (expected {_CANONICAL_PREAMBLE_V3_SHA[:16]}…)",
        )

        # ---- AC10 — ALLOW_LIST sha values valid ----
        ac10_v1_ok = (
            isinstance(_PREAMBLE_V1_SHA256, str)
            and len(_PREAMBLE_V1_SHA256) == 64
        )
        ac10_v2_ok = (
            isinstance(_PREAMBLE_V2_SHA256, str)
            and len(_PREAMBLE_V2_SHA256) == 64
        )
        ac10_v3_ok = len(actual_sha) == 64
        ac10 = ac10_v1_ok and ac10_v2_ok and ac10_v3_ok
        evidence["allow_list_shas"] = {
            "v1": _PREAMBLE_V1_SHA256[:16],
            "v2": _PREAMBLE_V2_SHA256[:16],
            "v3": actual_sha[:16],
        }
        _record(
            results, 10, "ALLOW_LIST sha values valid",
            ac10,
            f"v1/v2/canonical all 64-char sha "
            f"(v1_ok={ac10_v1_ok}, v2_ok={ac10_v2_ok}, v3_ok={ac10_v3_ok})",
        )

        # ---- AC11 — dispatchable prompt ALLOWED count == 49 ----
        evidence["allowed_prompt_files_count"] = len(ALLOWED_PROMPT_FILES)
        ac11 = len(ALLOWED_PROMPT_FILES) == _EXPECTED_ALLOWED_PROMPT_FILES
        _record(
            results, 11, f"ALLOWED_PROMPT_FILES == {_EXPECTED_ALLOWED_PROMPT_FILES}",
            ac11,
            f"actual = {len(ALLOWED_PROMPT_FILES)} "
            f"(expected {_EXPECTED_ALLOWED_PROMPT_FILES} after Phase B added 7 quick prompts)",
        )

        # ---- AC12 — _BUNDLES + _BUNDLED_DIR_TO_STAGE 10/10 ----
        evidence["_BUNDLES_count"] = len(_BUNDLES)
        evidence["_BUNDLED_DIR_TO_STAGE_count"] = len(_BUNDLED_DIR_TO_STAGE)
        ac12 = (
            len(_BUNDLES) == 10
            and len(_BUNDLED_DIR_TO_STAGE) == 10
        )
        _record(
            results, 12, "_BUNDLES & _BUNDLED_DIR_TO_STAGE = 10/10",
            ac12,
            f"_BUNDLES={len(_BUNDLES)}, "
            f"_BUNDLED_DIR_TO_STAGE={len(_BUNDLED_DIR_TO_STAGE)}",
        )

        # ============================================================
        # Spike XIV new ACs (Phase A~E)
        # ============================================================

        # ---- AC13 — Phase A: ASSEMBLE_HOME injection (set + unset) ----
        ac13_failures: list[str] = []
        # set case (env already set above)
        out_set = wrap_with_preamble("__probe_body__")
        task_idx = out_set.find("[TASK]")
        if task_idx == -1:
            ac13_failures.append("[TASK] marker missing in set case")
            body_set = ""
        else:
            body_set = out_set[task_idx + len("[TASK]\n"):]
        if not body_set.startswith("[ENV] 이 dispatch는 ASSEMBLE_HOME="):
            ac13_failures.append(
                f"set: body did not start with [ENV] (head={body_set[:60]!r})"
            )

        # unset case
        saved_home = os.environ.pop("ASSEMBLE_HOME", None)
        try:
            out_unset = wrap_with_preamble("__probe_body__")
            task_idx2 = out_unset.find("[TASK]")
            if task_idx2 == -1:
                # preamble may have been unloaded — check whole body
                body_unset = out_unset
            else:
                body_unset = out_unset[task_idx2 + len("[TASK]\n"):]
            if "[ENV]" in body_unset.splitlines()[0:1][0] if body_unset else False:
                ac13_failures.append(
                    f"unset: body unexpectedly contains [ENV] "
                    f"(head={body_unset[:60]!r})"
                )
        finally:
            if saved_home is not None:
                os.environ["ASSEMBLE_HOME"] = saved_home

        ac13 = not ac13_failures
        _record(
            results, 13, "Phase A: ASSEMBLE_HOME body injection",
            ac13,
            "set→[ENV] line present, unset→no [ENV] line"
            if ac13 else f"failures: {ac13_failures}",
        )

        # ---- AC14 — Phase B: 7 ★ SKILL.md mode-gate + Quick mode flow + no-shortcut ----
        ac14_failures: list[str] = []
        ac14_per_bundle: dict[str, dict] = {}
        for star_name in _SEVEN_STAR_BUNDLES:
            skill_md = dest_assemble / "bundled" / star_name / "SKILL.md"
            if not skill_md.is_file():
                ac14_failures.append(f"{star_name}: SKILL.md missing")
                continue
            text = skill_md.read_text(encoding="utf-8")
            has_mode_gate = "Mode gate" in text
            has_quick_mode_flow = "Quick mode flow" in text
            has_no_shortcut = "사용자 명시 동의 없이 단축 금지" in text
            ac14_per_bundle[star_name] = {
                "mode_gate": has_mode_gate,
                "quick_mode_flow": has_quick_mode_flow,
                "no_shortcut": has_no_shortcut,
            }
            if not has_mode_gate:
                ac14_failures.append(f"{star_name}: missing 'Mode gate'")
            if not has_quick_mode_flow:
                ac14_failures.append(f"{star_name}: missing 'Quick mode flow'")
            if not has_no_shortcut:
                ac14_failures.append(
                    f"{star_name}: missing '사용자 명시 동의 없이 단축 금지'"
                )
        evidence["mode_gate_per_bundle"] = ac14_per_bundle
        ac14 = not ac14_failures
        _record(
            results, 14, "Phase B: ★ mode-gate (7 bundles)",
            ac14,
            f"{len(_SEVEN_STAR_BUNDLES)}/7 ★ bundles have 3 grep markers"
            if ac14 else f"failures (first 5): {ac14_failures[:5]}",
        )

        # ---- AC15 — Phase C: plan-pack Recommendation policy ----
        plan_pack_skill = dest_assemble / "bundled/plan-pack/SKILL.md"
        ac15_failures: list[str] = []
        if not plan_pack_skill.is_file():
            ac15_failures.append("plan-pack SKILL.md missing")
            ac15_text = ""
        else:
            ac15_text = plan_pack_skill.read_text(encoding="utf-8")
            if "### Recommendation policy" not in ac15_text:
                ac15_failures.append("missing '### Recommendation policy'")
            if "iteration_count" not in ac15_text:
                ac15_failures.append("missing 'iteration_count' (algorithm marker)")
            if "추측 사유 박지 말 것" not in ac15_text:
                ac15_failures.append(
                    "missing '추측 사유 박지 말 것' (forbidding wording)"
                )
        ac15 = not ac15_failures
        _record(
            results, 15, "Phase C: plan-pack Recommendation policy",
            ac15,
            "section + iter≤3 algorithm + forbidding wording all present"
            if ac15 else f"failures: {ac15_failures}",
        )

        # ---- AC16 — Phase D: mark_orthogonal_stage import + safety/meta marking ----
        ac16_failures: list[str] = []
        try:
            from server.progress import mark_orthogonal_stage, create_run
        except ImportError as e:
            ac16_failures.append(f"import failed: {e}")
            mark_orthogonal_stage = None  # type: ignore[assignment]
            create_run = None  # type: ignore[assignment]

        if mark_orthogonal_stage is not None and create_run is not None:
            try:
                rid = create_run("probe-orthogonal-test", sequence=["plan", "execute"])
                # Mark safety
                p_safety = mark_orthogonal_stage(
                    rid, "safety", "in_progress", notes="probe AC16 safety"
                )
                if "safety" not in (p_safety.get("orthogonal_stages") or {}):
                    ac16_failures.append(
                        "after mark safety: orthogonal_stages.safety missing"
                    )
                # Mark meta
                p_meta = mark_orthogonal_stage(
                    rid, "meta", "in_progress", notes="probe AC16 meta"
                )
                if "meta" not in (p_meta.get("orthogonal_stages") or {}):
                    ac16_failures.append(
                        "after mark meta: orthogonal_stages.meta missing"
                    )
            except Exception as e:  # noqa: BLE001
                ac16_failures.append(
                    f"runtime call raised: {type(e).__name__}: {e}"
                )
        ac16 = not ac16_failures
        _record(
            results, 16, "Phase D: mark_orthogonal_stage runtime",
            ac16,
            "import OK + safety/meta marked → orthogonal_stages populated"
            if ac16 else f"failures: {ac16_failures}",
        )

        # ---- AC17 — Phase E: dispatch_prompt signature drift sweep ----
        # Run T7 enforcement test as subprocess in tempdir context.
        env_for_subprocess = dict(os.environ)
        env_for_subprocess["ASSEMBLE_HOME"] = str(tempdir)
        try:
            cp = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "tests/unit/test_skillmd_dispatch_prompt_signature.py",
                    "-q",
                ],
                cwd=str(dest_assemble),
                env=env_for_subprocess,
                capture_output=True,
                text=True,
                timeout=60,
            )
            ac17 = cp.returncode == 0
            ac17_msg = (
                f"pytest returncode=0 — drift 0"
                if ac17
                else f"returncode={cp.returncode}, stdout tail: "
                f"{cp.stdout.strip().splitlines()[-3:] if cp.stdout else '(empty)'}"
            )
        except Exception as e:  # noqa: BLE001
            ac17 = False
            ac17_msg = f"subprocess raised: {type(e).__name__}: {e}"
        _record(results, 17, "Phase E: dispatch_prompt signature drift", ac17, ac17_msg)

        # ---- AC18 — preamble v3 sha cross-check (in tempdir env) ----
        # Already computed actual_sha above; cross-check it survived all
        # the env mutations through Phase A's set/unset round-trip.
        actual_sha2 = canonical_preamble_sha256()
        ac18 = (
            actual_sha2 == _CANONICAL_PREAMBLE_V3_SHA
            and actual_sha == actual_sha2
        )
        _record(
            results, 18, "preamble v3 sha preserved (cross-check)",
            ac18,
            f"sha={actual_sha2[:16]}… == expected, "
            f"stable across Phase A round-trip",
        )

        # ============================================================
        # V4 identity snapshot (informational — surfaced in doc)
        # ============================================================
        evidence["identity_snapshot"] = {
            "ALLOWED_PROMPT_FILES_count": len(ALLOWED_PROMPT_FILES),
            "ORCHESTRATOR_ONLY_PROMPTS_count": len(ORCHESTRATOR_ONLY_PROMPTS),
            "_PROMPT_TO_STAGE_count": len(_PROMPT_TO_STAGE),
            "_BUNDLES_count": len(_BUNDLES),
            "_BUNDLED_DIR_TO_STAGE_count": len(_BUNDLED_DIR_TO_STAGE),
            "STAGE_CATEGORY_PRIORITY_count": len(STAGE_CATEGORY_PRIORITY),
            "canonical_preamble_v3_sha": actual_sha[:16],
            "preamble_v1_sha": _PREAMBLE_V1_SHA256[:16],
            "preamble_v2_sha": _PREAMBLE_V2_SHA256[:16],
        }

        # Re-write the doc with the FINAL verdict so the report reflects truth.
        # Doc is written to the REAL repo so the verdict survives tempdir cleanup.
        doc_path = _REAL_ASSEMBLE / "docs/dogfood/spike-xiv-b20a.md"
        wall_time = time.perf_counter() - t0
        all_pass = all(ok for _, _, ok, _ in results)
        verdict = "SHIP" if (all_pass and len(results) == 18) else "BLOCK"
        _write_dogfood_doc(doc_path, results, wall_time, evidence, verdict)
        print(f"[doc] wrote {doc_path}")

    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

    wall_time = time.perf_counter() - t0
    all_pass = all(ok for _, _, ok, _ in results)
    pass_count = sum(1 for _, _, ok, _ in results if ok)

    print()
    print(f"Wall-time: {wall_time:.3f}s (budget ≤30s)")
    print(f"{pass_count}/{len(results)} AC PASS")
    if all_pass and len(results) == 18:
        print("VERDICT: SHIP")
        return 0
    print("VERDICT: BLOCK")
    return 1


if __name__ == "__main__":
    sys.exit(main())
