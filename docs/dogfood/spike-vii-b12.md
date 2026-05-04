# Spike VII B-12 dogfood

**Date**: 2026-05-04
**Run id**: 20260504-spikevii-b12
**Diff range**: `832dfdd^..832dfdd` (Spike V `list_runs` change — same input as Spike VI B-11 real-dispatch)
**Mode**: real-dispatch (6 Agent calls — Step 1+2 parallel, 3-6 sequential)
**Symlink**: removed before run (`~/.claude/skills/assemble/runs/20260504-011811-b11r` and the `runs/` parent dir)
**Wall time**: ~230s (parallel Step 1+2 ≈ 45s, then 26s + 22s + 68s + 69s sequential)
**Verdict**: merge-ready (matches Spike VI B-11)

## AC results

| # | AC | Result | Notes |
|---|---|---|---|
| 1 | SCOPE.md found by Step 1 sub-agent (no symlink) | PASS | parsed_scope.json: 2 allow, 6 deny entries |
| 2 | Step 2 captures git diff to absolute `{{RUN_DIR}}/diff_inventory.json` | PASS | file at canonical channels path |
| 3 | Step 3 classification non-empty | PASS | 2 files, summary `{allow_hit: 2, deny_violation: 0, unrelated: 0, allow_miss: 0}` |
| 4 | Step 4 Rule 3 audit | PASS | summary `{critical: 0, major: 0, minor: 2}` |
| 5 | Step 5 verdict deterministic | PASS | `merge-ready` |
| 6 | Step 6 REVIEW_REPORT 7 sections | PASS | `grep -c '^## '` returned 7 |
| 7 | All 6 `dispatches.jsonl` rows present (iter1) | PASS | `wc -l == 6` |
| 8 | Each dispatch row preamble sha matches ALLOW_LIST | PASS | `verify_dispatches` ok=True, mismatches=0 |
| 9 | Verdict matches Spike VI B-11 expectation | PASS | both merge-ready |
| 10a | Self-execute wall ≤ 300s | n/a | this run was real-dispatch |
| 10b | Real-dispatch wall ≤ 600s | PASS | ~230s (well under budget) |
| 11 | Zero `runs/{{RUN_ID}}/` patterns survive in prompts | PASS | regression test 2/2 PASS |
| 12 | `{{RUN_DIR}}` placeholder substituted in dispatched prompts (Inputs section only — body placeholders intentionally preserved for sub-agent resolution) | PASS | Inputs section has absolute `/Users/...` path, no `{{RUN_DIR}}` literal in Inputs; body `{{RUN_DIR}}/X` references preserved per `test_body_run_dir_placeholder_left_for_subagent` |

**12/12 PASS** — Spike VII ships.

## What B-12 validated that B-11 didn't

- **F6 fix end-to-end**: Sub-agents resolved SCOPE.md via the absolute `{{RUN_DIR}}` token without any `runs/<rid>` symlink at the SKILL package root. The `runs/` directory was deleted before the run; Step 1 still found SCOPE because the prompt body used `{{RUN_DIR}}/SCOPE.md` (= `/Users/.../channels/assemble/runs/<rid>/SCOPE.md`) instead of relative `runs/<rid>/SCOPE.md`.
- **B1 auto-derivation**: All 6 dispatches passed only `RUN_ID` to `substitute_inputs`; `RUN_DIR` was auto-injected. Zero orchestrator call-site changes from Spike VI.
- **AC10b real-dispatch budget realistic**: 230s well under the 600s revised budget (B-11 was 334s, just over the old 300s). Confirms the split was justified.
- **F7 no longer surfaces**: Step 3 emitted clean `WROTE:` (no prose-then-WROTE collision). The E1 `extract_wrote_paths` last-match parser is the safety net even if a future run regresses.

## Artifacts

```
~/.claude/channels/assemble/runs/20260504-spikevii-b12/
├── REVIEW_REPORT.md          (2.3 KB, 7 canonical sections)
├── SCOPE.md                  (1.5 KB, copied from B-11r run dir)
├── classification.json
├── diff_inventory.json
├── dispatches.jsonl          (6 rows, all preamble sha verified)
├── parsed_scope.json
├── raw.diff                  (2.8 KB, git diff 832dfdd^..832dfdd)
├── rule3_audit.json
└── severity_grid.json        (verdict: merge-ready)
```

## Carryforward

None. All Spike VI B-11 carryforwards (F6, F7, F8) addressed. F4 perf collapse, F1 한글 backtick, naming convention, verifier ★ / shipper ★ are Spike VIII candidates per spec.
