---
name: "reviewer"
description: "Review-stage ★ bundle. External SCOPE.md vs git diff gate. Sub-agents own all reads/writes; main Claude orchestrates only."
stages: ["review"]
---

# reviewer ★ — external diff vs SCOPE.md gate

## When to invoke

Use after a code change is complete (working tree dirty or commit range pushed) when an independent verification of scope conformance is needed. reviewer ★ is the external sibling of builder ★ Step 6 self-review — same diff/scope contract, different session, fresh context.

## Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<run_id>/`.
- `runs/<rid>/SCOPE.md` — must exist (built by builder ★ Step 2 or hand-authored).
- Optional `<base>..<tip>` git range — defaults to `HEAD` (working tree vs HEAD).

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. One primary artifact:

- `REVIEW_REPORT.md` — 7 canonical sections (Summary, Scope baseline, Diff inventory, Allow/Deny classification, Surgical Changes audit, Severity assessment, Recommendations) with verdict line in Section 1.

Plus 5 intermediate JSONs for audit trail: `parsed_scope.json`, `diff_inventory.json` (+ `raw.diff`), `classification.json`, `rule3_audit.json`, `severity_grid.json`.

## Verdict logic

```python
verdict = "merge-ready" if (
    classification.summary.deny_violation == 0
    AND classification.summary.allow_miss == 0
    AND rule3_audit.summary.critical == 0
) else "needs-fix"
```

`needs-fix` reasons surface in REVIEW_REPORT Section 7 (Recommendations) in priority order: deny-violations → critical Rule 3 → allow-misses → major Rule 3.

## CRITICAL — orchestrator-only enforcement

Main Claude does NOT read SCOPE.md content, raw.diff content, or classification.json content directly. Main only:
- Resolves run_dir from `run_id`.
- Captures `<base>..<tip>` range arg.
- Dispatches sub-agents in sequence.
- Records each dispatch via `record_dispatch` (writes to `dispatches.jsonl`).

All reads, parsing, and writes happen in sub-agents. The 6 sub-agent prompts are exactly:

- `parse_scope_step1.md`, `diff_collect_step2.md`,
  `classify_files_step3.md`, `rule3_check_step4.md`,
  `severity_assess_step5.md`, `reviewer_report_step6.md`

If any prompt is invoked outside this allowlist, harness raises and halts.

## Step-by-step workflow

### Step 0 — orchestrator setup

Main resolves `run_dir` via `server.run_dir.run_artifact_path(run_id, ".")`. Verifies SCOPE.md exists at `<run_dir>/SCOPE.md`. If missing, halts with the user-facing error "SCOPE.md not found in run_dir; create one first or use builder ★ Step 2".

### Step 1 — parse SCOPE.md

Dispatch `parse_scope_step1.md` with `RUN_ID`. Sub-agent writes `parsed_scope.json`.

### Step 2 — capture git diff

Dispatch `diff_collect_step2.md` with `RUN_ID` + `DIFF_RANGE` + `REPO_PATH`. Sub-agent writes `diff_inventory.json` + `raw.diff`.

(Steps 1 and 2 may run in parallel via single-message multi-Agent dispatch.)

### Step 3 — classify diff files

Dispatch `classify_files_step3.md`. Sub-agent reads parsed_scope.json + diff_inventory.json, writes `classification.json`.

### Step 4 — Rule 3 audit

Dispatch `rule3_check_step4.md`. Sub-agent reads raw.diff + classification.json + parsed_scope.json, writes `rule3_audit.json`.

### Step 5 — severity grid

Dispatch `severity_assess_step5.md`. Sub-agent reads classification.json + rule3_audit.json + parsed_scope.json, writes `severity_grid.json`.

### Step 6 — write REVIEW_REPORT.md

Dispatch `reviewer_report_step6.md`. Sub-agent reads all 5 prior JSONs + the template, writes `REVIEW_REPORT.md`.

### Step 7 — iteration round-trip (optional)

If user revises SCOPE.md or the diff and asks for re-review, load `reviewer_iter_revisit.md` (orchestrator helper) and re-run Steps 2~6 (Step 1 only re-runs if SCOPE.md changed). Each iteration appends `## Iteration N` to REVIEW_REPORT.md without overwriting prior trail.

## Iteration audit invariant

Every iteration produces exactly **6** rows in `dispatches.jsonl` with step names `step1.iter{N}.parse`, `step2.iter{N}.diff`, `step3.iter{N}.classify`, `step4.iter{N}.rule3`, `step5.iter{N}.severity`, `step6.iter{N}.report`. (Step 1 is skipped on subsequent iterations unless SCOPE.md changed; in that case the row count is 6, otherwise 5.)

## Sub-agent matrix

See `## CRITICAL — orchestrator-only enforcement` above for the canonical allowlist. Roles use `general-purpose` as the default sub-agent type for all six steps.

## Identity guards

- ✅ orchestrator-only: main Claude does NOT read scoped content.
- ✅ harness preamble v3 prepended on every dispatch.
- ✅ `record_dispatch` mandatory — minimum 6 rows in dispatches.jsonl per run.
