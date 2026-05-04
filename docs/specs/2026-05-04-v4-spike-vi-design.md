# V4 Spike VI Design — reviewer ★ bundle + YAML cleanup

**Date**: 2026-05-04
**Status**: approved
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_v.md`

---

## Scope

Two-track spike:

- **Phase A** — YAML strict-load frontmatter quote cleanup (Spike IV carryforward)
- **Phase B** — `reviewer` ★ bundle (review stage, SCOPE.md vs git diff gate)

Ship gate: B-11 dogfood, 10 AC PASS target.

---

## Phase A — YAML strict-load cleanup

### Problem

Spike IV carryforward (M-tier): SKILL.md frontmatter blocks across `bundled/*/SKILL.md` use mixed quote styles. Some fields unquoted, some single-quoted, some double-quoted. `yaml.safe_load` accepts them today, but strict-load harnesses (and downstream tooling that does `--strict`) flag inconsistencies.

Cosmetic, low-blast-radius patch. Bundled here so Spike VI ship sweeps it up.

### Files in scope

- `bundled/builder/SKILL.md` (frontmatter only)
- `bundled/debugger/SKILL.md` (frontmatter only)
- `bundled/plan-pack/SKILL.md` (frontmatter only)
- `bundled/hello-bundle/SKILL.md` if frontmatter exists
- New `bundled/reviewer/SKILL.md` (Phase B introduces — must be born clean)

### Fix

Normalize all SKILL.md frontmatter string values to double-quoted form. Preserve semantic content verbatim — only quote style changes.

### Test

`tests/unit/test_yaml_strict_load.py`:
- Walk `bundled/*/SKILL.md`.
- Extract frontmatter (between leading `---` markers).
- Assert `yaml.safe_load(text)` succeeds without `yaml.YAMLError` AND that for every string-typed value, the round-trip via `yaml.safe_dump(..., default_style='"')` is a no-op (i.e., already in normalized form).

### Phase A commit

Single commit: `fix(v4-spike-vi-A): normalize SKILL.md frontmatter quotes for yaml strict-load`.

Phase A goes first because Phase B will create new SKILL.md and we want the rule established.

---

## Phase B — reviewer ★ bundle

### Goal

Review-stage bundle providing **external** verification. Distinct from builder Step 6 self-review (in-session, same context). reviewer ★ runs as a separate bundle invoke against any `runs/<rid>/SCOPE.md` + the current repo's `git diff`. Can verify diffs authored by other sessions, other agents, hand-edited diffs — anywhere a SCOPE.md exists or can be hand-written.

Primary deliverable: 1 artifact under `runs/<rid>/`. Main Claude is orchestrator-only; sub-agents own all reads/classification/writes.

### Inputs

| Source | Description |
|---|---|
| `run_id` | resolves run_dir to `~/.claude/channels/assemble/runs/<run_id>/` |
| `runs/<rid>/SCOPE.md` | allow-list + deny-list + completion criterion (built by builder Step 2 or hand-authored) |
| `git diff` (collected at Step 2) | repo HEAD vs working tree, OR explicit `<base>..<tip>` range when invoking reviewer for a finished change set |

### Artifacts

| File | Written by | Content |
|---|---|---|
| `REVIEW_REPORT.md` | Step 6 | 7-section audit + verdict line |
| `dispatches.jsonl` | every step | append-only audit trail (step1.parse, step2.diff, step3.classify, step4.rule3, step5.severity, step6.report) |

### REVIEW_REPORT.md 7 sections (canonical order)

1. **Summary** — verdict (`merge-ready` or `needs-fix`) + 1-line rationale
2. **Scope baseline** — parsed allow-list + deny-list + completion criterion (verbatim from SCOPE.md)
3. **Diff inventory** — changed files + LOC summary (`+X / -Y`) + commit range
4. **Allow/Deny classification** — per-file verdict (allow-hit / deny-violation / unrelated)
5. **Surgical Changes audit (Rule 3)** — bullet per file: scope-related / cosmetic-drift / out-of-scope-refactor
6. **Severity assessment** — Critical / Major / Minor counts + descriptions
7. **Recommendations** — concrete next actions if `needs-fix`, else "ready to merge"

### Verdict logic (deterministic)

```
verdict = "merge-ready" if (
    all allow-list entries hit at least one diff file
    AND zero deny-list violations
    AND zero Critical Rule 3 violations
    AND completion criterion not flagged failed
) else "needs-fix"
```

`needs-fix` reasons listed in Section 7 in priority order: deny-violations first, then Critical Rule 3, then allow-misses, then Major Rule 3, then completion-criterion misses.

### Sub-agent matrix

| Step | Role | Prompt file | Type |
|---|---|---|---|
| 0 | run_dir resolve + git diff capture | (main, bash) | orchestrator |
| 1 | parse SCOPE.md → structured allow/deny + completion criterion | `parse_scope_step1.md` | subagent |
| 2 | git diff collection + per-file LOC summary | `diff_collect_step2.md` | subagent |
| 3 | classify each diff file by allow/deny lists | `classify_files_step3.md` | subagent |
| 4 | Rule 3 (Surgical Changes) audit per file | `rule3_check_step4.md` | subagent |
| 5 | severity assessment grid | `severity_assess_step5.md` | subagent |
| 6 | REVIEW_REPORT.md write (7 sections) | `report_step6.md` | subagent |
| 7 | iteration round-trip (re-run after SCOPE/diff revision) | `reviewer_iter_revisit.md` | orchestrator |

Steps 1 and 2 can run in parallel (single message, two Agent calls) — they have no inter-dependency. Steps 3, 4 depend on outputs of 1+2. Step 5 depends on 3+4. Step 6 depends on 1, 2, 3, 4, 5 outputs.

### Step responsibility detail

#### Step 1 — parse_scope (subagent)

Input: SCOPE.md text.
Output: JSON-ish structured block written to `runs/<rid>/parsed_scope.json`:
```json
{
  "allow": [{"path": "server/run_dir.py", "note": "list_runs added"}],
  "deny": [{"path": "bundled/_shared/", "note": "shared infra"}],
  "completion": "python3 -c 'from server.run_dir import list_runs; print(list_runs())' && echo OK"
}
```
Error mode: SCOPE.md missing → write `parsed_scope.json` with `error: "scope-missing"` + exit early. Step 6 will surface `verdict: needs-fix, reason: scope-missing`.

#### Step 2 — diff_collect (subagent)

Input: optional `<base>..<tip>` range (from main Step 0). Default `HEAD`.
Output: `runs/<rid>/diff_inventory.json`:
```json
{
  "range": "HEAD",
  "files": [
    {"path": "server/run_dir.py", "added": 12, "removed": 0, "status": "M"}
  ],
  "raw_diff_path": "runs/<rid>/raw.diff"
}
```
Plus `runs/<rid>/raw.diff` (full `git diff` output for downstream steps).

#### Step 3 — classify_files (subagent)

Input: parsed_scope.json + diff_inventory.json.
Output: `runs/<rid>/classification.json`:
```json
{
  "files": [
    {"path": "server/run_dir.py", "verdict": "allow-hit", "matched_rule": "server/run_dir.py — list_runs added"},
    {"path": "server/__init__.py", "verdict": "deny-violation", "matched_rule": "server/ outside run_dir.py"}
  ],
  "allow_misses": [],
  "summary": {"allow_hit": 1, "deny_violation": 1, "unrelated": 0}
}
```

#### Step 4 — rule3_check (subagent)

Input: raw.diff + classification.json.
Output: `runs/<rid>/rule3_audit.json`:
```json
{
  "files": [
    {
      "path": "server/run_dir.py",
      "verdict": "scope-related",
      "evidence": "All hunks add list_runs() function and tests for it.",
      "severity": "minor"
    }
  ]
}
```
Verdicts: `scope-related` | `cosmetic-drift` | `out-of-scope-refactor`. `out-of-scope-refactor` always severity `critical`. `cosmetic-drift` (formatting, comments, unrelated renames) → `major`.

#### Step 5 — severity_assess (subagent)

Input: classification.json + rule3_audit.json + parsed_scope.json.
Output: `runs/<rid>/severity_grid.json`:
```json
{
  "critical": [],
  "major": [],
  "minor": [{"path": "server/run_dir.py", "reason": "scope-related minor change"}],
  "verdict": "merge-ready",
  "verdict_reason": "all 1 allow-hit, 0 violations, 0 critical."
}
```
Computes the `verdict` field per the deterministic rule above. Step 6 reads this verdict directly into Section 1.

#### Step 6 — report_step6 (subagent)

Input: all four prior JSON artifacts (parsed_scope, diff_inventory, classification, rule3_audit, severity_grid).
Output: `runs/<rid>/REVIEW_REPORT.md` with 7 canonical sections, verdict line in Section 1.

Template at `bundled/reviewer/templates/REVIEW_REPORT.md.template` with `{{PLACEHOLDERS}}` for each section.

#### Step 7 — reviewer_iter_revisit (orchestrator)

Optional. Invoked only when user requests re-review after SCOPE/diff revision. Pattern:
1. Read prior `REVIEW_REPORT.md` if exists.
2. Re-capture diff (Step 2 only).
3. Re-run Steps 3, 4, 5, 6 (in that order).
4. Append `## Iteration N` section to REVIEW_REPORT.md (does not overwrite prior verdict trail).

### Identity guards

- ✅ orchestrator-only enforcement: main Claude does NOT read SCOPE.md or git diff content directly (Step 0 only resolves the run_dir path; Step 2 sub-agent runs `git diff`). Main may pass `run_id` and optional `<base>..<tip>` range as inputs.
- ✅ harness preamble v3 prepended to every sub-agent prompt
- ✅ `record_dispatch` mandatory for each step (6 rows minimum in dispatches.jsonl)
- ✅ ALLOWED_PROMPT_FILES gate on every prompt resolution

### Iteration audit invariant

Every iteration produces exactly **6** rows in `dispatches.jsonl` for `step{N}.iter{M}.<phase>` where N=1..6, phase ∈ {parse, diff, classify, rule3, severity, report}.

### contracts.json additions

| ID | Contract |
|---|---|
| `spike-vi-reviewer-allowlist` | 6-file subagent allowlist contract (`parse_scope_step1.md`, ..., `report_step6.md`) named in SKILL.md `## CRITICAL — orchestrator-only enforcement` |
| `spike-vi-reviewer-artifact-invariant` | REVIEW_REPORT.md 7-section ordered list named verbatim in SKILL.md `## Artifacts` |
| `spike-vi-reviewer-verdict-invariant` | Verdict logic (4-clause AND for merge-ready) named verbatim in SKILL.md `## Verdict logic` |

### harness.py changes

```python
# _resolve_prompt_path bundles tuple
_BUNDLES = ("plan-pack", "builder", "debugger", "reviewer")  # add "reviewer"

# ALLOWED_PROMPT_FILES additions (7 entries)
"parse_scope_step1.md",
"diff_collect_step2.md",
"classify_files_step3.md",
"rule3_check_step4.md",
"severity_assess_step5.md",
"report_step6.md",
"reviewer_iter_revisit.md",
```

---

## Phase B — file map

### New files (Phase B)

```
bundled/reviewer/SKILL.md
bundled/reviewer/prompts/orchestrator/reviewer_iter_revisit.md
bundled/reviewer/prompts/subagent/parse_scope_step1.md
bundled/reviewer/prompts/subagent/diff_collect_step2.md
bundled/reviewer/prompts/subagent/classify_files_step3.md
bundled/reviewer/prompts/subagent/rule3_check_step4.md
bundled/reviewer/prompts/subagent/severity_assess_step5.md
bundled/reviewer/prompts/subagent/report_step6.md
bundled/reviewer/templates/REVIEW_REPORT.md.template
```

### Modified files (Phase B)

```
server/harness.py             — _BUNDLES + ALLOWED_PROMPT_FILES
tests/contracts/contracts.json — 3 new entries
```

### New test files (Phase B)

```
tests/contracts/test_reviewer_inventory.py
tests/unit/test_reviewer_template_placeholder_match.py
tests/unit/test_reviewer_prompts_print_contract.py
tests/unit/test_reviewer_step_guards.py
tests/unit/test_reviewer_skill_md.py
```

Mirrors builder ★ test shape (Spike V).

---

## Dogfood — B-11

### Target

Re-verify Spike V's `list_runs()` change against its own SCOPE.md.

- `run_id`: `20260503-145104-a531`
- SCOPE.md: existing on disk, 5 task breakdown, allow `server/run_dir.py` + `tests/unit/test_run_dir.py`
- `git diff` range: commit `832dfdd^..8d79573` (the 9 builder commits B1~B8 plus B-10 dogfood)
  - Actually narrower for B-11: just `832dfdd^..832dfdd` (the single `feat(server): add list_runs()`) since SCOPE was for that one change.

### Expected verdict

**merge-ready**

list_runs() shipped clean. SCOPE allows `server/run_dir.py` + `tests/unit/test_run_dir.py`. The shipped diff touched exactly those. Completion criterion (`python3 -c "from server.run_dir import list_runs; print(list_runs())" && echo OK`) passes.

### B-11 AC (10 gates)

1. SCOPE.md parsed — `parsed_scope.json` exists with non-empty `allow` array
2. git diff captured — `diff_inventory.json` + `raw.diff` exist, file count > 0
3. Each diff file classified — `classification.json` covers every file in diff_inventory
4. Rule 3 audit complete — `rule3_audit.json` has bullet per file with severity
5. Severity grid computed — `severity_grid.json` has counts + verdict + verdict_reason
6. REVIEW_REPORT.md exists with all 7 canonical section headers
7. Section 1 contains verdict line matching `severity_grid.json` verdict
8. dispatches.jsonl has ≥6 rows (one per step1..step6)
9. Verdict = `merge-ready` (matches expected for clean list_runs change)
10. Wall time < 5min

### Stretch dogfood — adversarial run

If time permits after B-11 passes, run reviewer ★ on a deliberately-broken SCOPE (e.g., remove `tests/unit/test_run_dir.py` from allow). Expected: `needs-fix` with `allow_misses` flagged.

---

## Spike V vs Spike VI comparison

| Concept | Spike V (builder) | Spike VI (reviewer) |
|---|---|---|
| Stage | execute | review |
| Context | in-session author | external verifier |
| Inputs | task description (interview) | SCOPE.md + git diff |
| Outputs | 4 artifacts | 1 artifact + 5 intermediate JSONs |
| Sub-agents | 6 step + 1 orchestrator | 6 step + 1 orchestrator |
| Step 6 self-review | yes (in-bundle) | n/a — reviewer IS the external review |
| Iteration | builder_iter_revisit | reviewer_iter_revisit |

Architectural symmetry intentional — reviewer ★ is the **gate** that builder ★ Step 6 self-review approximates internally. Together they form a two-tier review (in-session + external).

---

## Identity preservation

- ✅ Spike I~V core contracts unchanged
- ✅ builder ★ Steps 0~7 unchanged (Phase A only normalizes its frontmatter quote style — semantic content unchanged)
- ✅ debugger ★ Steps 0~7 unchanged (Phase A only normalizes frontmatter)
- ✅ canonical preamble v3 sha unchanged
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged
- ✅ V3 concierge menu layer unchanged
- ✅ orchestrator-only V4 decision #9 preserved (main does NOT read diff/scope content)

---

## Spike VII candidates

- V3 concierge `(Recommended)` Korean drift cleanup
- `verifier` ★ bundle (orthogonal to reviewer ★ — verifier runs AC=bash; reviewer audits diff scope)
- `shipper` ★ bundle
- reviewer ↔ builder feedback loop (auto-invoke reviewer on every builder commit)

---

## Source

- Parent: `project_assemble_v4_spec.md`
- Sibling: `project_assemble_v4_spike_v.md` (Spike V — builder ★)
- Carryforward: `project_assemble_v4_spike_iv.md` Item M-tier (YAML quote)
