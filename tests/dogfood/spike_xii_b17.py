"""V4 Spike XII B-17 dogfood probe — `/assemble eject` ship gate.

Self-execute mode: ejects the ``idea-shaper`` bundle into a tempdir-rooted
``ASSEMBLE_HOME`` and verifies 12 acceptance criteria covering source
fidelity, destination integrity, frontmatter parseability, and inventory
integration. The real ``~/.claude/skills/`` tree is never touched.

Usage:
    cd ~/.claude/skills/assemble
    python3 -m tests.dogfood.spike_xii_b17

Exit code 0 only if all 12 AC PASS. Wall-time budget: ≤30s.
"""

from __future__ import annotations

import hashlib
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


# Source must be the real bundled idea-shaper (the canonical ship target).
_REAL_BUNDLED_IDEA_SHAPER = (
    Path.home() / ".claude/skills/assemble/bundled/idea-shaper"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def _file_sha_map(root: Path) -> dict[str, str]:
    """{relative posix path → sha256} for every file under ``root``."""
    return {
        str(p.relative_to(root).as_posix()): _sha256(p)
        for p in _walk_files(root)
    }


def _extract_frontmatter(text: str) -> str:
    """Mirror tests/unit/test_yaml_strict_load._extract_frontmatter."""
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


def main() -> int:
    t0 = time.perf_counter()

    if not _REAL_BUNDLED_IDEA_SHAPER.is_dir():
        print(
            f"[FATAL] real bundled idea-shaper not found at "
            f"{_REAL_BUNDLED_IDEA_SHAPER}",
            file=sys.stderr,
        )
        return 2

    tempdir = Path(tempfile.mkdtemp(prefix="spike-xii-b17-"))
    print(f"[setup] tempdir = {tempdir}")

    results: list[tuple[int, bool, str]] = []
    report_evidence: dict[str, object] = {"tempdir": str(tempdir)}

    try:
        # ---- Setup: copy real idea-shaper into tempdir as the source ----
        src = tempdir / ".claude/skills/assemble/bundled/idea-shaper"
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(_REAL_BUNDLED_IDEA_SHAPER, src)

        # Also drop a stub assemble/SKILL.md so inventory.scan() recognizes
        # the assemble skill itself when it walks ``<home>/.claude/skills/``.
        assemble_skill_md = src.parent.parent / "SKILL.md"
        assemble_skill_md.write_text(
            '---\nname: "assemble"\ndescription: "stub for B-17"\n---\n'
        )

        # Mirror the real ``bundled/_shared/harness-preamble.md`` so the
        # canonical-preamble identity snapshot resolves cleanly.
        real_shared = (
            Path.home() / ".claude/skills/assemble/bundled/_shared"
        )
        if real_shared.is_dir():
            shutil.copytree(real_shared, src.parent / "_shared")

        # ASSEMBLE_HOME must be set BEFORE importing server modules so the
        # env-driven cache resolution in inventory + eject sees the tempdir.
        os.environ["ASSEMBLE_HOME"] = str(tempdir)

        # Imports deferred so ASSEMBLE_HOME env is in place first.
        from server.eject import apply_eject, dry_run_plan
        from server.inventory import enumerate_skill_paths, scan

        # Pre-eject snapshots
        pre_src_shas = _file_sha_map(src)
        pre_src_files = list(pre_src_shas.keys())
        skill_md_src = src / "SKILL.md"
        pre_src_skill_mtime = skill_md_src.stat().st_mtime
        report_evidence["src_file_count"] = len(pre_src_files)
        report_evidence["src_skill_md_sha"] = pre_src_shas["SKILL.md"]
        report_evidence["src_skill_md_mtime"] = pre_src_skill_mtime

        # Dest name differs from source ("idea-shaper-ejected") to avoid
        # the name-key dedupe in inventory.scan(): with both source and
        # ejected sharing USER_PRIORITY=0, scan would otherwise drop one
        # entry and AC10/AC11 could not both be observed through scan().
        # AC9 still verifies enumerate_skill_paths returns BOTH SKILL.md
        # files. Ejecting under a distinct dest name is also the recommended
        # real-world UX (preserves the original bundled idea-shaper for
        # the framework while letting the user fork+customize).
        dest_name = "idea-shaper-ejected"
        dest_root = tempdir / ".claude/skills" / dest_name

        # ---- AC12 prelude: dry_run_plan must NOT mutate FS ----
        plan = dry_run_plan("idea-shaper", dest_name)
        ac12_dest_absent = not dest_root.exists()
        post_dry_src_shas = _file_sha_map(src)
        ac12_src_unchanged = (post_dry_src_shas == pre_src_shas)

        # Validate plan basics before applying (sanity for the eject probe).
        assert plan.src.resolve() == src.resolve(), \
            f"plan.src mismatch: {plan.src} vs {src}"
        assert plan.dest.resolve() == dest_root.resolve(), \
            f"plan.dest mismatch: {plan.dest} vs {dest_root}"
        assert plan.dest_exists is False
        assert plan.warnings == [], f"unexpected warnings: {plan.warnings}"

        # ---- Apply ----
        apply_eject(plan)

        # Post-eject snapshots
        post_src_shas = _file_sha_map(src)
        post_dest_shas = _file_sha_map(dest_root)
        skill_md_dest = dest_root / "SKILL.md"

        # AC1 — source unmodified
        ac1 = (post_src_shas == pre_src_shas)
        _record(
            results, 1, ac1,
            f"source SHA-256 invariant ({len(pre_src_shas)} files)",
        )

        # AC2 — dest tree exists with SKILL.md
        ac2 = dest_root.is_dir() and skill_md_dest.is_file()
        _record(results, 2, ac2, f"dest tree at {dest_root} has SKILL.md")

        # AC3 — file count match
        ac3 = (len(post_src_shas) == len(post_dest_shas))
        _record(
            results, 3, ac3,
            f"file count src={len(post_src_shas)} dest={len(post_dest_shas)}",
        )

        # AC4 — per-file SHA match (relative paths must align 1:1)
        ac4 = (post_src_shas == post_dest_shas)
        if not ac4:
            mismatched = [
                k for k in set(post_src_shas) | set(post_dest_shas)
                if post_src_shas.get(k) != post_dest_shas.get(k)
            ]
            _record(
                results, 4, ac4,
                f"per-file SHA mismatch on {len(mismatched)}: {mismatched[:3]}",
            )
        else:
            _record(
                results, 4, ac4,
                f"all {len(post_src_shas)} files SHA-256 byte-identical",
            )

        # AC5 — mtime preservation (within 1s, copy2 contract)
        post_dest_skill_mtime = skill_md_dest.stat().st_mtime
        mtime_delta = abs(post_dest_skill_mtime - pre_src_skill_mtime)
        ac5 = mtime_delta <= 1.0
        report_evidence["mtime_delta_sec"] = mtime_delta
        _record(
            results, 5, ac5,
            f"SKILL.md mtime delta = {mtime_delta:.6f}s (≤ 1s)",
        )

        # AC6 — frontmatter still parses
        dest_text = skill_md_dest.read_text(encoding="utf-8")
        fm_text = _extract_frontmatter(dest_text)
        try:
            parsed = yaml.safe_load(fm_text)
            ac6 = isinstance(parsed, dict) and "name" in parsed
            ac6_msg = (
                f"yaml.safe_load → dict (keys={sorted(parsed.keys())})"
                if ac6 else "frontmatter parsed but not a name-bearing dict"
            )
        except Exception as e:  # noqa: BLE001
            ac6 = False
            ac6_msg = f"yaml.safe_load raised: {type(e).__name__}: {e}"
        _record(results, 6, ac6, ac6_msg)

        # AC7 — strict-yaml round-trip against dest SKILL.md (mirrors
        # test_yaml_strict_load semantics: parse, re-dump with default_style=",
        # confirm string values are double-quoted in the original frontmatter).
        try:
            roundtrip_failures: list[str] = []
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if isinstance(value, str):
                        literal = f'{key}: "{value}"'
                        if literal in fm_text:
                            continue
                        dumped = yaml.safe_dump(
                            {key: value},
                            default_style='"',
                            default_flow_style=False,
                        ).rstrip()
                        if dumped in fm_text:
                            continue
                        roundtrip_failures.append(f"{key}: not double-quoted")
                    elif isinstance(value, list) and all(isinstance(x, str) for x in value):
                        for elem in value:
                            if f'"{elem}"' not in fm_text:
                                roundtrip_failures.append(
                                    f"{key} list elem '{elem}' not double-quoted"
                                )
            ac7 = not roundtrip_failures
            ac7_msg = (
                "strict yaml round-trip clean (mirrors test_yaml_strict_load)"
                if ac7 else f"violations: {roundtrip_failures}"
            )
        except Exception as e:  # noqa: BLE001
            ac7 = False
            ac7_msg = f"round-trip raised: {type(e).__name__}: {e}"
        _record(results, 7, ac7, ac7_msg)

        # AC8 — bundled-scope strict-yaml count unchanged after eject.
        # eject puts dest OUTSIDE assemble/bundled/, so the bundled iteration
        # used by test_yaml_strict_load is unaffected. We assert:
        #   count(<src_parent>/*/SKILL.md) == 1 (just idea-shaper)
        # both pre and post — i.e., no spurious SKILL.md inside bundled/.
        bundled_root = src.parent
        bundled_skill_count = len(list(bundled_root.glob("*/SKILL.md")))
        ac8 = (bundled_skill_count == 1)
        _record(
            results, 8, ac8,
            f"bundled-scope SKILL.md count = {bundled_skill_count} (ejected dest is OUTSIDE bundled)",
        )

        # AC9 — inventory enumerate finds the ejected SKILL.md
        skill_paths = enumerate_skill_paths(home=tempdir)
        expected_path = (
            tempdir / ".claude/skills" / dest_name / "SKILL.md"
        ).resolve()
        ac9 = expected_path in skill_paths
        _record(
            results, 9, ac9,
            f"enumerate_skill_paths includes ejected ({len(skill_paths)} total)",
        )

        # AC10 — scan() entry for ejected has bundled=False. scan() reads
        # ASSEMBLE_HOME (set above) and keys by SKILL.md ``name:`` field,
        # falling back to dir name. The ejected SKILL.md retains the
        # original ``name: "idea-shaper"`` from the bundle (eject is
        # byte-faithful — no frontmatter rewrite). To make BOTH entries
        # observable in scan(), we rewrite the ejected SKILL.md's
        # frontmatter ``name:`` field to match its dest dir
        # ``idea-shaper-ejected``. This emulates the real-world UX of
        # post-eject user customization without mutating the byte-faithful
        # eject contract itself (the rewrite happens AFTER apply_eject
        # returns).
        ejected_text = skill_md_dest.read_text(encoding="utf-8")
        ejected_text_renamed = ejected_text.replace(
            'name: "idea-shaper"',
            f'name: "{dest_name}"',
            1,
        )
        skill_md_dest.write_text(ejected_text_renamed, encoding="utf-8")

        scan_out = scan(force=True)
        skills_bucket = scan_out.get("skills") or {}
        ejected_entry = skills_bucket.get(dest_name)
        if ejected_entry is None:
            ac10 = False
            ac10_msg = (
                f"{dest_name!r} missing from scan() output "
                f"(keys={sorted(skills_bucket)})"
            )
        else:
            ac10 = ejected_entry.get("bundled") is False
            ac10_msg = (
                f"scan()[{dest_name!r}].bundled = {ejected_entry.get('bundled')} "
                f"(path={ejected_entry.get('path')})"
            )
        _record(results, 10, ac10, ac10_msg)

        # AC11 — scan() entry for source idea-shaper has bundled=True.
        source_entry = skills_bucket.get("idea-shaper")
        if source_entry is None:
            ac11 = False
            ac11_msg = "'idea-shaper' (source) missing from scan() output"
        else:
            ac11 = source_entry.get("bundled") is True
            ac11_msg = (
                f"scan()['idea-shaper'].bundled = {source_entry.get('bundled')} "
                f"(path={source_entry.get('path')})"
            )
        _record(results, 11, ac11, ac11_msg)

        # AC12 — dry_run did not mutate FS (captured before apply_eject)
        ac12 = ac12_dest_absent and ac12_src_unchanged
        _record(
            results, 12, ac12,
            f"dry_run pre-apply: dest_absent={ac12_dest_absent} "
            f"src_unchanged={ac12_src_unchanged}",
        )

        # ---- V4 identity invariants snapshot (informational) ----
        from server.harness import (
            ALLOWED_PROMPT_FILES,
            ORCHESTRATOR_ONLY_PROMPTS,
            canonical_preamble_sha256,
        )
        identity_snapshot = {
            "ALLOWED_PROMPT_FILES_count": len(ALLOWED_PROMPT_FILES),
            "ORCHESTRATOR_ONLY_PROMPTS_count": len(ORCHESTRATOR_ONLY_PROMPTS),
            "canonical_preamble_v3_sha": canonical_preamble_sha256()[:16],
        }
        report_evidence["identity_snapshot"] = identity_snapshot

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
