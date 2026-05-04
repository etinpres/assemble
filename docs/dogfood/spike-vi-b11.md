# Spike VI B-11 dogfood

**Date**: 2026-05-04
**Run**: `20260503-145104-a531`
**Diff range**: `832dfdd^..832dfdd` (single commit `feat(server): add list_runs()`)
**Result**: 10/10 AC PASS — merge-ready verdict matched expected.

## AC checklist

- AC1 PASS — parsed_scope.json with 2 allow / 6 deny entries
- AC2 PASS — diff_inventory.json + raw.diff captured (2 files, +56 / -0)
- AC3 PASS — classification.json covers all 2 diff files
- AC4 PASS — rule3_audit.json has severity per file (critical=0, major=0, minor=2)
- AC5 PASS — severity_grid.json has verdict='merge-ready' + verdict_reason
- AC6 PASS — REVIEW_REPORT.md has all 7 canonical sections
- AC7 PASS — Summary section verdict matches severity_grid ('merge-ready')
- AC8 PASS — dispatches.jsonl has 6/6 iter1 step rows (13 total rows including step0 marker)
- AC9 PASS — verdict = merge-ready (matches expected)
- AC10 PASS — wall time = 100s (< 300s budget)

## Verdict

merge-ready

list_runs() change:
- 2 files in diff: `server/run_dir.py` (+13/-0) + `tests/unit/test_run_dir.py` (+43/-0)
- both classified as **allow-hit** (matched_rule = SCOPE allow entry verbatim)
- 0 deny-violations, 0 critical Rule 3 issues, 0 cosmetic-drift, 0 allow-misses
- Rule 3 audit: both files `scope-related` minor — server hunk adds `list_runs()` exactly per SCOPE allow entry; test hunk adds 5 list_runs test cases (a–e per SCOPE breakdown) plus the import line.

## Findings & carryforwards

**F1 — Deny-list parsing of inline backtick paths (cosmetic).** SCOPE.md uses bullets like
`- \`server/\` 내 \`run_dir.py\` 외 모든 파일 (\`__init__.py\`, ...)`. Step 1's "split on FIRST ` — `"
plus "strip outer backticks" works for the simple allow entries, but for these complex deny
bullets the path captures everything up to the first em-dash — which here is the trailing
note text inside the bullet itself. Result: deny entries store paths like
`` server/` 내 `run_dir.py` 외 모든 파일 (`__init__.py`, ...) `` and the rendered REVIEW_REPORT
shows trailing backticks dangling on the deny list bullets. No correctness impact for B-11
(no diff file matches those malformed entries either way, so deny logic still returns 0),
but it's a real prompt-side robustness gap when SCOPE authors use freeform Korean prose
in deny entries. Carryforward to Spike VII: tighten parse_scope_step1 spec — either require
a stricter deny grammar (single backtick-wrapped path token), or document the freeform
fallback explicitly.

**F2 — Korean SCOPE.md round-trips cleanly through every step.** All 6 prompts use
`ensure_ascii=False` correctly; final REVIEW_REPORT.md preserves Hangul without escape
sequences. Spike III's F3 finding (Korean handling) appears resolved at the prompt level.

**F3 — Step 4 evidence quality.** The Rule 3 audit's `evidence` strings are clean and
within the ≤200-char budget. The single-hunk `server/run_dir.py` change made it trivial
to write specific line-range evidence (`@@ -110,6 +110,19`). For more complex multi-hunk
diffs Spike VII should validate that the prompt instruction "≤ 200 chars summarizing the
rationale, citing line ranges" still produces coherent evidence rather than truncated salad.

**F4 — Wall time 100s is dominated by orchestrator JSON shuffle, not LLM judgment.**
Five of the six steps were pure deterministic Python (parse, diff, classify, severity-grid,
report-render); only Step 4 required real interpretation. Future builder→reviewer ★ pipeline
optimization candidate: collapse Steps 1+2+3+5+6 into a single "deterministic shell" sub-agent
and keep Step 4 as the only LLM-bearing step. Ship-blocker? No. Spike VII nice-to-have.

**F5 — Reviewer ★ second self-sufficient bundle confirmed.** No external skill/plugin
references in any of the 6 prompts; all stdlib Python, all artifacts written under
`runs/<RUN_ID>/`. Bundle is shippable as-is.

## Spike VI ship status

**SHIP**. Reviewer ★ bundle verified end-to-end on a real builder Spike V artifact.
Verdict matches expected. All 10 AC PASS.
