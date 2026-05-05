# V4 Spike XII — Phase E Overall Code Review

**Date**: 2026-05-05
**Reviewer**: superpowers:code-reviewer (Phase E ship gate)
**Commit range**: `720c065..d70619a` (6 commits)
**Verdict**: **SHIP-READY**
**Codex retro decision**: skip (no atomic-rename / collision / metadata findings)

## Strengths

- **V4 identity invariants — every locked counter holds**. Independently verified on master `d70619a`:
  - `ALLOWED_PROMPT_FILES` count = 42
  - `_PROMPT_TO_STAGE` count = 42
  - `_BUNDLES` count = 10
  - `STAGE_CATEGORY_PRIORITY` count = 10 (debug/design/discover/execute/meta/plan/review/safety/ship/verify)
  - canonical preamble v3 sha = `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
  - V3 concierge §1-§7 default flow textually unchanged (Sub-commands inserted between §0 and §1, additive only)
- **V4 #9 IO exception scope honored end-to-end**. Zero new entries in `ALLOWED_PROMPT_FILES`, `_PROMPT_TO_STAGE`, `_BUNDLES`, `_BUNDLED_DIR_TO_STAGE`. eject lives in its own module, imported nowhere by harness/inventory. No facade re-export. Surgical scope = 9 files (8 NEW + 1 EDIT to SKILL.md), as planned.
- **Atomicity contract is sound under POSIX rename semantics**. Steps 1-2 build temp tree under `dest.parent` (same filesystem → atomic rename). Step 3-4 backup-then-rename. Step 5 single `os.rename`. Step 7 wipes temp on any failure. Empirical probe confirms `os.rename` on a non-empty dest dir raises `OSError(ENOTEMPTY)` rather than silently overwriting — the TOCTOU window between `dest.exists()` (step 3) and `os.rename(...)` (step 5) is bounded by kernel guarantees, so the single-user trust model holds.
- **Pure functions only, zero shell escape**. `shutil`/`pathlib`/`os.rename`/`secrets.token_hex` only. No `subprocess`, no `shell=True`, no Bash invocation. Lower threat surface than any ★ bundle. `validate_dest_name` regex `^[a-z][a-z0-9_-]{0,63}$` + reserved-name + path-traversal guards stack deny-by-default.
- **Test-quality polish from Phase B follow-up (4839891)**. The atomic-failure-with-overwrite test (`test_apply_eject_atomic_failure_with_overwrite_preserves_dest`) directly exercises the contract clause that copytree (step 2) runs BEFORE backup rename (step 4), so a copytree failure leaves dest + zero backup + zero temp leftovers. Backup-content sha equality is asserted (not just existence). The unreadable-file M2 carryforward test ships with a thoughtful chmod-parent-dir attack and graceful platform-skip.
- **B-17 dogfood is fast and faithful**. 0.018s wall-time vs 30s budget (1666× under). Real `bundled/idea-shaper` copied into tempdir-rooted `ASSEMBLE_HOME`; never mutates `~/.claude/skills/`. 12/12 AC PASS verified by independent re-run during this review. Identity-snapshot section captures `ALLOWED_PROMPT_FILES_count=42`, `ORCHESTRATOR_ONLY_PROMPTS_count=3`, canonical sha first-16 — re-readable evidence at the ship commit.
- **Cross-layer coherence**. Spec → plan → code → tests → flow doc → SKILL.md router all describe the same 9-symbol API, the same 7-step atomicity contract, the same 5-step user flow, the same 12 AC. No drift detected.
- **Doc-tone match**. `docs/eject-flow.md` mirrors the existing concierge-flow voice; SKILL.md Sub-commands table sits cleanly between §0 and §1; Limitations section explicitly enumerates harness-coupling caveats (`from server.harness import wrap_with_preamble`, `_shared/harness-preamble.md`, dispatch_and_record assumptions). User won't be surprised by post-eject reference breakage.

## Issues

### Critical
None.

### Important
None blocking ship.

### Minor (carryforward-worthy, non-blocking)

- **M-XII1 — Plan-vs-reality test count drift not yet reconciled**. Plan said `789 + 17 = 806` post-Phase-B and `806 → 807` after B-17. Actual final = **812 passed, 1 skipped**. Drift sources: (a) Phase B follow-up (4839891) added one test for the copytree-overwrite contract; (b) parametrize splits in `test_validate_dest_name_rejects_*` count as multiple collected items. B-17 itself stayed standalone (not pytest-discovered). Not blocking — counters all moved upward — but Phase F CHANGELOG entry currently quotes `789 → 807`; should be flipped to `789 → 812 (+ 1 skipped)` for accuracy. Same shape as Spike XI's `10e2810` reconciliation.
- **M-XII2 — B-17 dest-name deviation worth a one-liner amendment**. Spec sketches `dry_run_plan('idea-shaper', 'idea-shaper')` with matching dest; reality is `dest_name = 'idea-shaper-ejected'` to dodge `inventory.scan()`'s name-key collapse on USER_PRIORITY tie. The dogfood report (`docs/dogfood/spike-xii-b17.md` § "Implementation notes / deviations") already documents the why and references the post-eject `name:` rewrite trick. Optional: append a 2-line note to the spec § B-17 for future-spike readers, OR leave the dogfood-report disclosure as the single source of truth. Lean: leave as-is, it's already disclosed.
- **M-XII3 — `validate_dest_name` is intentionally ASCII-only; Unicode/NFC ambiguity is silently rejected**. Regex `^[a-z][a-z0-9_-]{0,63}$` rejects e.g., `한글` or `café` with the same generic "regex mismatch" message. Spec § "Destination name validation" says lowercase-by-design (cross-platform case-insensitive APFS / case-sensitive ext4 footgun avoidance). Not a defect — a deliberate reductive guard. Carryforward note for V5: if dogfood ever surfaces a user trying to eject under a Korean/Japanese name, decide whether to extend regex or improve the error to mention "ASCII lowercase only".
- **M-XII4 — Backup-name collision raises OSError, not EjectError**. Empirically reproduced: 2nd consecutive overwrite eject within the same wall-second yields `OSError: [Errno 66] Directory not empty`. Documented in `eject-flow.md` § Limitations as "acceptable failure mode (loud, not silent)". Loud but unwrapped — the orchestrator path in `eject-flow.md` Step 4 says "If exception raised: print error + suggest --dry-run to inspect first" so the user does see something, but the exception type drift (OSError vs EjectError) means a `try: ... except EjectError: ...` won't catch this case. Not blocking (raw OSError still propagates and is caught by orchestrator's bare except + print). Carryforward: V5 could wrap the backup-rename in `try: ... except OSError as e: raise EjectError(...) from e` for type symmetry, OR switch to `time.time_ns()` to make collisions effectively impossible.
- **M-XII5 — `apply_eject` doc references nonexistent "spec § 'Atomic apply'"**. The docstring on line 224 says "see spec § 'Atomic apply'". Spec actually titles the section `### Atomic apply (the only side-effect function)` — the prose match is loose. Trivial fix: update the docstring reference if anyone touches `eject.py` again, otherwise ignore.
- **M-XII6 — SKILL.md sub-command router UX is unambiguous on the assemble side, but main Claude inheritance behavior is documented narratively, not enforced**. The router says "if first token after `/assemble` is a sub-command keyword, read the flow doc and follow it line-by-line. Default concierge flow (§2 inventory refresh through §7 list) is bypassed." For a future maintainer reading `eject-flow.md`, there's no big-bold "DO NOT FALL THROUGH TO §2-§7" warning. Spike XIII (blank-Mac dogfood) is the natural catch-net per R4 in the plan's risk register; the spec also calls UX validation to Spike XIII explicitly. Not blocking, but consider adding one line at the top of `eject-flow.md`: "When this flow is invoked, default V3 concierge §2-§7 is bypassed; do not fall through after Step 5."
- **M-XII7 — `apply_eject` uses `BaseException` for cleanup catch**. Line 281's `except BaseException` is broad enough to catch `KeyboardInterrupt` / `SystemExit` (good — temp dir gets wiped). But it also re-raises, which is correct. Style nit only: many Python style guides prefer `except: ` + a comment explaining the intentional super-catch for cleanup. The current code's `except BaseException: ... raise` is functionally equivalent and arguably clearer about intent. No change needed.

## Carryforwards (Spike XIII inheritance candidates)

These map to the spec's existing carryforward register (F-XII1..F-XII5) and the new ones surfaced by this review (M-XII1..M-XII7). Spike XIII (V4 release-gate blank-Mac dogfood) inheritance candidates:

| ID | Description | Severity | Source |
|---|---|---|---|
| F-XII1 | Symlink mode (`--link <bundle>`) for live-track of bundle updates | low | spec |
| F-XII2 | Auto-rename on conflict (`--name auto`) | low | spec |
| F-XII3 | Frontmatter rewrite on copy (flip `name:` to dest dir name) | low | spec |
| F-XII4 | Trace ledger entry for eject events (keeper ★ visibility) | low | spec |
| F-XII5 | Pre-existing `.bak.<ts>` cleanup helper | low | spec |
| M-XII1 | Reconcile pytest count in CHANGELOG (`789 → 812 (+1 skipped)`, not `789 → 807`) | minor | review |
| M-XII2 | Optional spec amendment for B-17 dest-name deviation (already disclosed in dogfood report) | minor | review |
| M-XII3 | ASCII-only `validate_dest_name` — improve error message OR extend regex if dogfood demands | minor | review |
| M-XII4 | Wrap backup-rename `OSError` as `EjectError` for type symmetry, OR adopt `time.time_ns()` for unique backup names | minor | review |
| M-XII5 | Trivial docstring reference touch-up (`spec § 'Atomic apply'`) | trivial | review |
| M-XII6 | One-line "DO NOT fall through to §2-§7" guard at top of `eject-flow.md` | minor | review |
| M-XII7 | Style comment on `except BaseException` cleanup-catch | trivial | review |

None of these block ship. M-XII1 is the only one with a small case for closing in Phase F (3-line CHANGELOG flip during ship); the rest are inheritable to Spike XIII or V5.

## Codex retro decision

**Skip** — proceed directly to Phase F.

Per spec § "Codex retro skip", standard skip is the default. Promotion criteria: (a) atomic-rename TOCTOU race finding, (b) backup-name collision finding (significant, not just R5 already in spec), (c) shutil.copy2 metadata gap finding.

This review surfaced none of those:

- **TOCTOU race**: empirically bounded by POSIX `os.rename` semantics (non-empty dest = `OSError(ENOTEMPTY)`, no silent overwrite). Single-user CLI trust model holds.
- **Backup-name collision**: matches R5 in plan's risk register exactly; documented in `eject-flow.md` § Limitations as loud-not-silent failure; M-XII4 captures the optional V5 polish (wrap as EjectError or use `time.time_ns()`). Not significant beyond the already-disclosed risk.
- **shutil.copy2 metadata gap**: AC5 confirms mtime preserved within 1s on macOS APFS (delta = 0.000000s in B-17 run). Spec explicitly scopes out ACL/xattr; eject does not rely on either. No gap surfaced.

Bash surface = 0 in main code path. No SCOPE.md / ledger / streaming-cap / killpg / process-group complexity. Standard E1 review is sufficient.

## Assessment

**SHIP-READY**.

The implementation is exceptionally clean for a V4 spike — smaller than any prior spike (~150 LoC code, 17 + 1 unit tests, 1 dogfood probe, 1 flow doc, 1 SKILL.md router insertion), zero pressure on the dispatch/allowlist/identity surface, every locked invariant verified to hold. B-17 dogfood is fast (1666× under budget) and exercises the real bundle. All 6 phase-level reviews passed (A APPROVED-WITH-MINOR → B APPROVED-WITH-MINOR → C APPROVED → D APPROVED → E this review).

Phase F can proceed with one trivial CHANGELOG accuracy adjustment (`789 → 812 (+1 skipped)` instead of `789 → 807`); everything else inherits cleanly to Spike XIII (V4 release-gate blank-Mac dogfood) and V5.

## Source

- Spec: `docs/specs/2026-05-05-v4-spike-xii-design.md`
- Plan: `docs/plans/2026-05-05-v4-spike-xii.md`
- Phase D dogfood: `docs/dogfood/spike-xii-b17.md`
- Code: `server/eject.py`
- Tests: `tests/unit/test_eject.py`
- Flow doc: `docs/eject-flow.md`
- Router: `SKILL.md` § Sub-commands
- This review: `docs/dogfood/spike-xii-overall-review.md`
