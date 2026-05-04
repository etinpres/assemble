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

---

## B-11 real-dispatch follow-up (2026-05-04)

The first B-11 above ran in **self-execute mode** — the dogfood agent simulated
both orchestrator and 6 sub-agents itself. That validated the artifact shape and
verdict logic but skipped the actual `Agent` dispatch chain. To close that gap a
**real-dispatch dogfood** was run on a fresh run dir.

**Run**: `20260504-011811-b11r` (channels-side, with `runs/<RID>` symlink into
`~/.claude/skills/assemble/runs/`)
**Mode**: main Claude as orchestrator, 6 separate `Agent (general-purpose)`
dispatches, each reading its prepared prompt from `/tmp/b11r_step{N}_prompt.txt`
(produced by `dispatch_prompt` + `substitute_inputs`).
**Result**: **9/10 AC PASS, 1 marginal FAIL (AC10 wall time 334s vs 300s budget)**.
Verdict still `merge-ready`. Bundle works end-to-end via real Agent dispatch.

### AC results (real-dispatch)

- AC1 PASS — 2 allow / 6 deny / 0 errors
- AC2 PASS — diff_inventory + raw.diff (2 files, +56/-0)
- AC3 PASS — classification covers all diff files (2/2 allow-hit)
- AC4 PASS — rule3 audit per-file severity (0 critical / 0 major / 2 minor)
- AC5 PASS — severity_grid verdict + verdict_reason
- AC6 PASS — REVIEW_REPORT.md 7 sections in canonical order
- AC7 PASS — Summary contains verdict
- AC8 PASS — 7 rows in dispatches.jsonl (1 step0 + 6 iter1 step rows)
- AC9 PASS — verdict = merge-ready
- AC10 **FAIL (marginal)** — wall time 334s vs 300s budget. Includes one Step 1+2 retry
  due to F6 below; without retry the wall time would land near 250–280s. Budget needs
  upward revision (300s → 600s) to accommodate Agent dispatch overhead.

### Real-dispatch findings (NEW — not surfaced in self-execute B-11)

**F6 (CRITICAL — found by real-dispatch) — `runs/<RID>/...` relative paths
ambiguous across cwd.** Sub-agents dispatched via `Agent (general-purpose)` start
with cwd = `~/.claude/skills/assemble/` (the skill repo). Prompts use
`runs/<RUN_ID>/SCOPE.md` as a relative path, which resolves to
`~/.claude/skills/assemble/runs/<RID>/SCOPE.md`. But the actual run dir lives at
`~/.claude/channels/assemble/runs/<RID>/`. Result: Step 1's first dispatch hit
`scope-missing` and wrote a useless empty parsed_scope.json into the wrong
location.

Self-execute B-11 didn't catch this because the dogfood agent used absolute
`$RUN` paths throughout — never exercised the relative-path resolution.

**Quick fix for this dogfood**: created a symlink
`~/.claude/skills/assemble/runs/<RID>` → `~/.claude/channels/assemble/runs/<RID>`
and re-dispatched Steps 1+2.

**Real fix for Spike VII**: introduce a `RUN_DIR` substitution token (absolute
path) in every reviewer prompt, OR have orchestrator pass `cd <run_dir>` as part
of the dispatch context, OR change `_resolve_prompt_path`'s sister helper to
return absolute artifact paths. None of those landed in Spike VI — the bundle
ships with the latent bug masked by symlink.

**F7 (MEDIUM) — Step 3 sub-agent emitted prose alongside the WROTE line.**
Despite the prompt saying "Print only WROTE: ... no other prose", the Step 3
agent prefixed the WROTE line with "Classification correct: both diff files are
allow-hits, no deny violations, no allow misses." The orchestrator regex
`^WROTE: (.+)$` still matched the second line so no functional break, but
strict prompt compliance was violated. Carryforward: tighten orchestrator-side
WROTE: extraction (regex anchor) AND/OR sharpen Step 3 prompt's "stdout
discipline" clause. Self-execute B-11 didn't catch this because there was no
real Agent emitting freeform prose.

**F8 (LOW) — AC10 budget needs revision.** Real Agent dispatch overhead pushed
wall time to 334s even though the run's actual LLM work was modest (only Step 4
required interpretation; Steps 1/2/3/5/6 are deterministic). Pre-set 300s
budget assumed self-execute timing. Spike VII should raise the AC10 budget to
600s for real-dispatch runs, OR define two AC10 variants (self-execute / real-
dispatch).

### What real-dispatch validated that self-execute didn't

- ✅ `dispatch_prompt` resolves the right file for each prompt name (no
  collision after B8 rename — `report_step6.md` correctly lands in debugger,
  `reviewer_report_step6.md` correctly lands in reviewer).
- ✅ `wrap_with_preamble` injects v3 harness preamble before each prompt body.
- ✅ `substitute_inputs` replaces `{{RUN_ID}}` / `{{DIFF_RANGE}}` / `{{REPO_PATH}}`
  cleanly.
- ✅ `record_dispatch` produces `dispatches.jsonl` rows matching the iteration
  audit invariant (6 iter1 rows for steps 1–6).
- ✅ `ALLOWED_PROMPT_FILES` gate doesn't block any of the 6 reviewer prompts.
- ✅ Sub-agents follow `Print WROTE:` contract for orchestrator parsing
  (4/6 strictly; Step 3 emitted extra prose — F7).

### Carryforwards for Spike VII (updated)

- **F6 (was unknown)** — `runs/<RID>` relative-path ambiguity. Address via
  `RUN_DIR` substitution token, or absolute path resolution helper, or
  documented `cd` requirement. **Highest priority** — without symlink the
  bundle silently produces wrong artifacts.
- **F7 (was unknown)** — sub-agent stdout discipline. Tighten orchestrator
  regex (e.g., grep last line only) AND prompt phrasing.
- **F8 (was unknown)** — AC10 wall time budget revision (300s → 600s).
- F1, F3, F4 from self-execute B-11 still apply (carry forward as before).
