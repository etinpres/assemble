---
name: "keeper"
description: "Meta-stage ★ bundle. Audits finished run artifacts (parsed_scope, dispatches.jsonl, REPORT.md) for 5-rule violations, summarizes via bounded LLM, appends to global learnings ledger with deterministic prune. Observational, not gating."
stages: ["meta"]
---

# keeper ★ — meta-stage audit + learning recall

## When to invoke

Use AFTER any other bundle's run terminates. keeper does not gate — it observes. Reads what other bundles already deposited in run_dir, runs 5 deterministic violation rules (R1-R5), summarizes detections via bounded LLM, appends to `~/.claude/channels/assemble/learnings.jsonl` with TTL/skiplist/dedup/FIFO prune. Future dispatches via `dispatch_and_record` automatically pick up top-K relevant prior learnings (Track B — Phase D wiring).

## Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<rid>/`
- `<run_dir>/parsed_scope.json` — REQUIRED for R2 (deny pattern check). Missing → audit-skipped.
- `<run_dir>/dispatches.jsonl` — optional; enables R5 (dispatch failure detection)
- `<run_dir>/*.json` — audit JSONs (preflight/version_bump/build_result/tag_result/verify_result/execution_result/extracted_completion). Each contributes evidence to relevant rules.
- `<run_dir>/*.md` — REPORT.md files (REVIEW/VERIFY/SHIP). Verdicts informational only.

## Artifacts

- `<run_dir>/audit_inventory.json` — Step 1 output
- `<run_dir>/learning_candidates.json` — Step 2 output (deterministic rule extractor)
- `<run_dir>/learnings_to_emit.json` — Step 3 output (LLM-summarized)
- `<run_dir>/KEEPER_REPORT.md` — Step 4 output (7 sections happy / 4 abort)
- `~/.claude/channels/assemble/learnings.jsonl` — global ledger (Step 4 append + prune)
- `~/.claude/channels/assemble/learnings.skip` — user-managed deny by evidence_hash (NOT keeper-written)

## Verdict logic (deterministic — 3 outcomes)

```python
verdict = "audit-clean" if (
    audit_inventory.verdict == "audit-ready"
    AND total_learnings_emitted == 0
) else "audit-flagged" if (
    audit_inventory.verdict == "audit-ready"
    AND total_learnings_emitted >= 1
) else "audit-skipped"  # parsed_scope missing or other precondition fail
```

Reason text:
- `audit-clean` → "ran 5 rules, 0 violations detected; ledger unchanged"
- `audit-flagged` → "<N> learning(s) emitted across <categories>; ledger appended"
- `audit-skipped` → "<reason>" (e.g. "parsed_scope.json missing in run_dir")

No pass/fail — keeper does not gate downstream. The verdict is observational.

## CRITICAL — orchestrator-only enforcement

Main Claude does NOT read intermediate JSONs and does NOT call Bash. Main only:
- Resolves run_dir from run_id
- Verifies parsed_scope.json exists (sanity check; full validation in Step 1)
- Dispatches sub-agents in sequence (Step 1 → 2 → 3 → 4) via `server.harness.dispatch_prompt`
- Records each dispatch via `server.harness.record_dispatch`

**Sub-agent prompt allowlist** (these MUST appear in `server.harness.ALLOWED_PROMPT_FILES`):

- `keeper_audit_step1.md` — Bash GRANTED for read-only git probes
- `keeper_extract_step2.md` — Bash GRANTED for canned `python3 .../extract_rules.py <run_dir>` invocation
- `keeper_summarize_step3.md` — NO Bash
- `keeper_ledger_step4.md` — Bash GRANTED for canned `python3 .../ledger_update.py <run_dir>` invocation

If any prompt is invoked outside this allowlist, harness raises and halts.

The orchestrator helper `keeper_iter_revisit.md` lives under `prompts/orchestrator/` and is NOT in the allowlist (it goes through `ORCHESTRATOR_ONLY_PROMPTS`).

## Step-by-step workflow

### Step 0 — orchestrator setup

Main resolves run_dir via `server.run_dir.run_dir_path(run_id)`. Confirms `parsed_scope.json` present. Missing → halts with "parsed_scope.json not found; run reviewer ★ Step 1 first".

### Step 1 — audit inventory

Dispatch `keeper_audit_step1.md` with `RUN_ID`. **Bash GRANTED** — read-only git probes (`git status --porcelain`, `git rev-parse HEAD`, `git rev-parse --abbrev-ref HEAD`, `git diff --name-only HEAD~..HEAD`). Sub-agent walks run_dir, enumerates artifacts, runs git probes, writes `audit_inventory.json` with verdict `audit-ready` or `audit-skipped` (skip reason: parsed_scope absent OR no other-bundle artifacts present).

### Step 2 — deterministic rule extraction

Dispatch `keeper_extract_step2.md` with `RUN_ID`. **Bash GRANTED** — single canned invocation of `python3 ~/.claude/skills/assemble/bundled/keeper/scripts/extract_rules.py <run_dir>`. The script (version-controlled, no LLM) reads audit_inventory + targeted artifacts, applies 5 rules, writes `learning_candidates.json`:

| Rule | Category | Detection |
|---|---|---|
| R1 | rule-violation | dispatch failures (proxy for 4-rule violations) |
| R2 | scope-deviation | parsed_scope.deny ∩ git diff files |
| R3 | ac-failure | verify_result.verdict == "fail" |
| R4 | todo-leakage | TODO/FIXME/XXX added in diff |
| R5 | dispatch-failure | dispatches.jsonl status: failed rows |

### Step 3 — bounded LLM summarization

Dispatch `keeper_summarize_step3.md` with `RUN_ID`. **NO Bash.** Sub-agent reads `learning_candidates.json`, writes ≤200-char single-line summary per candidate. Constraints: language match (Korean if parsed_scope.task_summary Korean), newline-strip, truncate at 197+"…". Fallback templates per rule_id if LLM step fails. Output: `learnings_to_emit.json` (preserves evidence + evidence_hash from Step 2 verbatim).

### Step 4 — ledger append + prune + report

Dispatch `keeper_ledger_step4.md` with `RUN_ID`. **Bash GRANTED** — single canned invocation of `python3 ~/.claude/skills/assemble/bundled/keeper/scripts/ledger_update.py <run_dir>`. The script imports `server.learnings` (`read_ledger`, `write_ledger`, `prune_ledger`, `read_skiplist`), appends new entries, applies 4-stage prune (TTL 30d → skiplist → dedup → FIFO cap 100), writes back to `learnings.jsonl` atomically. Also writes `KEEPER_REPORT.md` from happy or abort template.

### Step 5 — iteration (optional)

If user re-runs keeper after seeded fix, main loads `keeper_iter_revisit.md` (orchestrator-only helper, NOT subagent-dispatched). Re-runs Steps 1-4 in sequence.

## Iteration audit invariant

Every iteration → 4 rows in `dispatches.jsonl`: `step1.iter{N}.audit`, `step2.iter{N}.extract`, `step3.iter{N}.summarize`, `step4.iter{N}.ledger`. Audit-skipped iter (Step 1 verdict=audit-skipped) → 1 row only (`step1`).

## Sub-agent matrix

See § CRITICAL — orchestrator-only enforcement above. All 4 steps use `general-purpose` as default sub-agent type.

| Step | Prompt file | Sub-agent type | Tools granted |
|---|---|---|---|
| 1 | `keeper_audit_step1.md` | `general-purpose` | Read, Write, **Bash** (read-only git probes) |
| 2 | `keeper_extract_step2.md` | `general-purpose` | Read, Write, **Bash** (canned `extract_rules.py`) |
| 3 | `keeper_summarize_step3.md` | `general-purpose` | Read, Write (NO Bash) |
| 4 | `keeper_ledger_step4.md` | `general-purpose` | Read, Write, **Bash** (canned `ledger_update.py`) |

Iteration helper `keeper_iter_revisit.md` is loaded by main directly (NOT in subagent allowlist; lives under `prompts/orchestrator/` and is registered in `ORCHESTRATOR_ONLY_PROMPTS`).

## Hand-off

keeper has no downstream. After it runs, the user can:

- Inspect `learnings.jsonl` directly
- Edit `learnings.skip` to suppress false positives by evidence_hash
- Future dispatches via `dispatch_and_record` automatically include top-K relevant learnings as a body-prefix fence (Track B — Phase D)
