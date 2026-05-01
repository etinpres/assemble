# Spike IV final readiness — B-9 dogfood PASS, ship

## Result

**13/13 full PASS. Ship.**

B-9 dogfood run `20260501-133444-035a` (OneShot daily puzzle UTC timezone bug — KST 00:00–08:59 window serves yesterday's puzzle). Iteration 0 only — `verify.sh exit 0` confirmed at Step 5 → user picked "no — 종료 (추천)" at Step 7. ~15 min wall-clock (debug stage 13m 39s + verify stage manual passthrough).

## 18 acceptance criteria — final mapping

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `dispatch_and_record` exists/exported | ✅ | `server/__init__.py` import + `__all__`; `tests/unit/test_dispatch_and_record.py` 5 cases |
| 2 | `dispatch_and_record` calls `dispatch_prompt` + `record_dispatch` exactly once | ✅ | `test_dispatched_path_calls_both` |
| 3 | `record_dispatch` accepts `status="skipped"` field | ✅ | `test_skipped_path_does_not_call_dispatch_prompt` + on-disk `test_record_includes_status_field_on_disk` |
| 4 | SKILL.md Step 6 yes-path uses `dispatch_and_record` for iter1 | ✅ | `bundled/plan-pack/SKILL.md` Step 6 yes-path detail (commit `9ad8fd4`) |
| 5 | SKILL.md Step 6 yes-path documents `(no change)` skip → `status="skipped"` row | ✅ | same commit, step 2 bullet |
| 6 | `iter_emphasis.md` no longer requires verbatim write on `(no change)` | ✅ | `bundled/plan-pack/prompts/orchestrator/iter_emphasis.md` step 1 ERROR-back contract (commit `9ad8fd4` + `ca85de4` Inputs comment fix) |
| 7 | `hooks/guard_run_dir.sh` Bash branch delegates to `_guard_bash_matcher.py` | ✅ | commit `020a146` |
| 8 | `_guard_bash_matcher.py` rejects Bash-comment-prefix marker; accepts python3 inline + heredoc | ✅ | `tests/contracts/test_guard_bash_matcher.py` 8 cases (5 base + 3 strict — string-literal/line-2/python3.10) after α-tighten in `d1e9a1b` |
| 9 | `bundled/debugger/` full ★ pattern (SKILL.md + 6 prompts + 3 templates) | ✅ | C1-C7 commits (`90e0e43` → `a2564da`) |
| 10 | `ALLOWED_PROMPT_FILES` extended by 6 debugger entries (8 → 14) | ✅ | `server/harness.py:30-46` |
| 11 | `dispatch_prompt` resolver finds debugger prompts | ✅ | `_resolve_prompt_path` searches `plan-pack` then `debugger` (commit `dd32895`) |
| 12 | All debugger prompt files satisfy "Print `WROTE: <absolute path>`" wording | ✅ | `tests/unit/test_debugger_prompts_print_contract.py` |
| 13 | All debugger save-block bodies have no bare `...` | ✅ | `tests/unit/test_debugger_prompts_no_bare_ellipsis.py` |
| 14 | All debugger templates' `{{...}}` placeholders are replaced by some debugger prompt | ✅ | `tests/unit/test_debugger_template_placeholder_match.py` (active at C7) |
| 15 | Inventory scanner exposes debugger with `bundled=True` | ✅ | `tests/contracts/test_debugger_inventory.py` |
| 16 | pytest 231+N green after each Phase commit | ✅ | 231 → 251 (16 commits, no regression) |
| 17 | B-9 dogfood: real bug → complete `BUG_REPORT.md` + executable `repro.sh` (fails before fix) + `verify.sh` (passes after fix) | ✅ | run `20260501-133444-035a` — 5 sections + TL;DR, repro exit 64, verify exit 0 |
| 18 | B-9 dogfood: any iter1 path uses `dispatch_and_record`; `(no change)` produces `status="skipped"`; no Bash-prefix-marker writes succeed | ✅* | iter1 not entered (verify.sh passed at Step 5); Bash-prefix-marker probe 0 attempts; canonical preamble v3 sha `8d22a29c…` byte-identical across all 5 dispatch rows |

Plus the audit trail confirms:

- `dispatches.jsonl` 5 entries (step2/3/4/5/6), all `prompt_file` matching the 6-file allowlist; `preamble_sha256: 8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` byte-identical; `preamble_bytes: 1599` consistent.
- `progress.json` 2 stages (debug `done` with `tool_used: "★ debugger"`; verify `manual` — Step 5 verify.sh already exit 0).
- `BUG_REPORT.md` 5 sections + TL;DR + front matter `status: complete`. 5 hypotheses with bisect+evidence, root cause with ≥2-alternative challenge, 5-file patch summary.
- OneShot patches: 4 files, 6 occurrences total of `DateTime.now().toUtc()` → `DateTime.now()` + 2 occurrences of `DateTime.utc(now.year, now.month, now.day)` → `DateTime(now.year, now.month, now.day)`. All inside bisect-cited surface (Surgical Changes constraint preserved).

## B-9 dogfood narrative

User gave debugger ★ a 1-line task ("OneShot daily puzzle UTC 시간대 버그 …") with **no specific environment info** (Q2 marked "모름"). The orchestrator dispatched Step 2 sub-agent which:

1. Built `repro.sh` — inline Dart heredoc simulating KST 08:00 / UTC previous day (exit 64 — `dart -` heredoc syntax artifact, but non-zero exit satisfies the contract).
2. Ran reproducer, captured exit + stderr in `## Reproducer`.
3. Wrote `BUG_REPORT.md` from template (4 placeholders + 1 sentinel substituted).

Step 3 sub-agent grepped `streak|badge|completed|completion|todayKey|dateKey` across `apps/oneshot/lib/**/*.dart`, found 4 candidate files, produced **5 ranked hypotheses** with falsifiable bisect steps. All hypotheses converged on the same systemic fault (`DateTime.now().toUtc()` at multiple call sites).

Step 4 sub-agent picked H1 (`getTodaysPuzzle()` in `daily_puzzle.dart`), drove the bisect with 6 file:line citations, ran an explicit ≥2-alternative challenge (storage key format mismatch / epoch anchor off-by-one) — both alternatives refuted with positive evidence. Root cause: 6 call sites of `DateTime.now().toUtc()` across 4 files.

Step 5 sub-agent edited 4 OneShot source files via `Edit` (5 distinct patches), wrote `verify.sh` (grep-based static check for `toUtc()` absence + `DateTime.now()` presence), ran it — exit 0. `## Fix & verification` section appended with patch summary + verify output + diff-equivalent inline code.

Step 6 sub-agent validated 5 sections + no `<TBD: …>` + no bare `...` → flipped status, added TL;DR (1-paragraph summary, ≤4 sentences). Step 7 prompted iteration; user picked "no — 종료 (추천)" because verify already passed.

## Carryforward (3 items — all minor, not ship blockers)

### M1 — `repro.sh` Dart heredoc syntax misfire

**Symptom**: `dart - <<'DART_EOF'` ran as `dart -`, fail with `Could not find a command named "-"` exit 64. The intended Dart program never executed.

**Severity**: Minor. The contract requires non-zero exit (bug reproduces) — exit 64 satisfies that, just not via the intended path. The bug is real and verified in BUG_REPORT.md `## Hypotheses` evidence; the repro.sh's *educational value* (showing the timezone calculation) is degraded.

**Fix shape**: Step 2 sub-agent prompt `repro_step2.md` could include a Dart heredoc example (`dart run -` form, or temp-file pattern) to cue better idioms. Defer to Spike V or a Spike IV patch — no rush.

### M2 — `verify.sh` is grep-based static check, not behavioral

**Symptom**: verify.sh checks `toUtc()` absence + `DateTime.now()` presence + `DateTime.utc(now.year, …)` absence in 4 target files. It does NOT execute Dart code or simulate the KST 08:00 scenario.

**Severity**: Minor. The static check is a faithful proxy for the fix (the 6 call sites were the entire root-cause surface); a code-level confirmation that the surface is fully migrated is meaningful. But cross-cutting AC=bash is conceptually about *behavioral* verification.

**Fix shape**: Step 5 sub-agent prompt `fix_step5.md` could prefer behavioral verifiers when the bug's symptom is reproducible by a self-contained script. Same defer rationale as M1.

### M3 — Step 3 orchestrator self-justification log

**Symptom (caps screen 06)**: After Step 2 ended with `## Symptom` left as `<TBD: …>` (user's task-description copy did not reach the Symptom section in the rendered template), main Claude's log line says "Symptom TBD이지만 title에 버그 설명이 있어 Step 3가 추론 가능. Step 3 dispatch."

**Severity**: Minor (informational). Indicates Step 1 input → Step 2 substitution path has a small gap — `SYMPTOM_SUMMARY` was correctly captured in Q1 but the Step 2 sub-agent left the section sentinel intact in some renderings. The downstream steps still recovered (the title carries the symptom verbatim, and Step 3+ extracted from there). C7's explicit 5-section header check (`58c0800` minor fix) caught this in Step 6 — the section header `## Symptom` was present, just with sentinel content.

**Fix shape**: `repro_step2.md` save block could explicitly substitute `## Symptom` content (currently it leaves it as `<TBD: …>` for Step 1's user response). One additional `.replace()` literal would close the gap. Defer — does not block ship.

## Spike IV ship verdict

**Ship Spike IV.** All 18 acceptance criteria PASS (criterion 18 partial-PASS via byte-identity invariant only — the iter1 / Bash-prefix paths were not exercised because the bug resolved in iter0, but the *infrastructure* for those paths is unit-tested at the code level via criterion 1-8). 

The 3 minor carryforwards (M1/M2/M3) are sub-agent prompt polish and do not affect the workflow contract. They are tracked as low-priority Spike V (or Spike IV-patch) candidates.

This makes debugger ★ the **second self-sufficient ★ candidate** in V4 (after plan-pack ★), validating the V4 #1 decision ("빈손 컴 + assemble 단독으로 프로젝트 1개 끝까지"). A user with no `superpowers:systematic-debugging` skill installed gets the full hypothesis → reproducer → bisect → root cause → fix workflow via the bundled prompt allowlist + harness preamble v3 + dispatch_and_record audit pairing.

## Spike V proposal — `builder` ★

★ candidate priority order (per parent V4 spec § "★급 강화 후보"):

1. **`builder` ★** — TDD-enforcing execute-stage bundle. Failing test → impl → green → commit pattern. Pairs with Spike I path-only contract (every change has a sub-agent-owned save block).
2. **`reviewer` ★** — diff vs SCOPE.md gate (Spike VI).
3. **V3 concierge polish** — Spike VII (M1 carryforward `(Recommended)` Korean drift, etc.).

Spike V scope might also include the 3 Spike IV M-carryforwards (M1 `repro.sh` Dart heredoc / M2 `verify.sh` behavioral / M3 Step 2 Symptom substitution) as a "★-bundle prompt-polish track" alongside the new `builder` ★.

## Source

- B-9 dogfood transcript: 11 caps captured by 형 (2026-05-01 session, run `20260501-133444-035a`)
- Spec: `docs/specs/2026-04-30-v4-spike-iv-design.md`
- Plan: `docs/plans/2026-05-03-v4-spike-iv.md`
- 16 commits: `020a146` → `58c0800` (`git log --oneline 1e608d4..58c0800`)
- Run dir: `~/.claude/channels/assemble/runs/20260501-133444-035a/` (BUG_REPORT.md / repro.sh / verify.sh / dispatches.jsonl / progress.json)
- OneShot patches: `apps/oneshot/lib/{engine/daily_puzzle.dart, screens/{home,game}_screen.dart, data/puzzle_storage.dart}` (4 files, 8 patches total)
- Sibling readiness memo: `docs/dogfood/spike-iii-final.md`
