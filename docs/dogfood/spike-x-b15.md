# Spike X B-15 Dogfood — keeper ★ ship gate

**Mode**: self-execute (subprocess invocation of bundled keeper scripts —
the real `dispatch_and_record` Agent path is exercised in sub-run 4 only,
matching Spike VIII/IX self-execute conventions).

**Run date**: 2026-05-04
**Master HEAD at start**: `e212e11` (Phase E — Codex F1 R2 deny shape fix
+ E1/E2 review docs saved)

This is the ship gate evidence document for V4 Spike X (keeper ★ — the
fifth self-sufficient bundle, 6th meta-stage cover after plan / execute /
debug / review / verify / ship). Each of the 4 sub-runs seeds a
`tmp_path` run_dir with the inputs that earlier-stage bundles would
have produced, then drives the 4-step keeper pipeline:

  1. `audit_inventory.json`      (Step 1 logic — replayed in-process)
  2. `learning_candidates.json`  (Step 2 — `extract_rules.py` subprocess)
  3. `learnings_to_emit.json`    (Step 3 — deterministic templates,
                                  replayed in-process)
  4. `KEEPER_REPORT.md` +
     ledger append                (Step 4 — `ledger_update.py` subprocess)

Sub-run 4 additionally exercises the Track B body-prefix splice path
through `server.dispatch_and_record` to confirm the `[PRIOR LEARNINGS]`
fence reaches the wrapped prompt.

## Sub-run 1 — happy / clean (audit-skipped)

**Seed**:
- `parsed_scope.json` only (no other bundle artifacts).
- `audit_inventory.json` with `verdict = "audit-skipped"`,
  `skip_reason = "no bundle artifacts present in run_dir"`.

**Pipeline**: extract_rules → no candidates → ledger_update writes the
ABORT variant of KEEPER_REPORT.md.

**Result**:

| Metric | Value |
|---|---|
| extract_rules rc | 0 |
| ledger_update rc | 0 |
| Wall time (total) | 0.085 s |
| Ledger byte_count_delta | **0** (file never created) |
| Ledger row count | 0 |
| KEEPER_REPORT H2 sections | **4** (ABORT variant) |
| Report contains "ABORTED" | yes |
| Report contains "audit-skipped" | yes |

**Verdict**: `audit-skipped` — happy clean path. Ledger untouched.

## Sub-run 2 — abort / scope-deviation seeded (R2)

**Seed**:
- `parsed_scope.deny = [{"path": "src/auth.py", "note": "test"}]`
  (production parser object-form — Codex F1 fix path).
- `audit_inventory.git_diff_files = ["src/auth.py"]`.
- `audit_inventory.verdict = "audit-ready"`,
  `bundles_observed = ["reviewer"]`.

**Pipeline**: extract_rules detects R2 (deny ∩ diff overlap) → 1
candidate → Step 3 templates → ledger_update appends 1 row.

**Result**:

| Metric | Value |
|---|---|
| extract_rules rc | 0 |
| ledger_update rc | 0 |
| Wall time (total) | 0.084 s |
| Ledger byte_count_delta | **+375 bytes** (1 row) |
| Ledger row count | 1 |
| Rule_ids in ledger | `["R2"]` |
| Categories | `["scope-deviation"]` |
| KEEPER_REPORT H2 sections | **7** (happy variant) |
| Report contains "audit-flagged" | yes |

**Verdict**: `audit-flagged` — R2 fired exactly once, ledger +1.

## Sub-run 3 — build-fail / verify_result.fail seeded (R3)

**Seed**:
- `parsed_scope.deny = []`.
- `verify_result.json` with `verdict = "fail"`,
  `command_executed = "pytest"`, `reason = "exit 1"`.
- `audit_inventory.verdict = "audit-ready"`,
  `bundles_observed = ["verifier"]`.

**Pipeline**: extract_rules detects R3 (verify_result fail) → 1
candidate → Step 3 templates → ledger_update appends 1 row.

**Result**:

| Metric | Value |
|---|---|
| extract_rules rc | 0 |
| ledger_update rc | 0 |
| Wall time (total) | 0.086 s |
| Ledger byte_count_delta | **+311 bytes** (1 row) |
| Ledger row count | 1 |
| Rule_ids in ledger | `["R3"]` |
| Categories | `["ac-failure"]` |
| KEEPER_REPORT H2 sections | **7** (happy variant) |
| Report contains "audit-flagged" | yes |

**Verdict**: `audit-flagged` — R3 fired exactly once, ledger +1.

## Sub-run 4 — recall / iter-N learnings injection

**Seed**:
- `learnings.jsonl` populated with the two entries that runs 2+3 would
  have produced (R2 scope-deviation + R3 ac-failure).
- Dispatch a plan-stage prompt (`iter_emphasis.md`) via
  `server.dispatch_and_record`.

**Pipeline**: `dispatch_and_record` → `wrap_with_preamble_and_learnings`
→ Track B body-prefix splice → wrapped prompt body now contains the
`[PRIOR LEARNINGS — 우선 회피]` fence with both R2 and R3 entries.

**Result**:

| Metric | Value |
|---|---|
| dispatch elapsed | 0.0009 s |
| Wrapped prompt contains `[PRIOR LEARNINGS — 우선 회피]` | yes |
| Fence contains R2 entry (src/auth.py) | yes |
| Fence contains R3 entry (pytest) | yes |
| `verify_dispatches(rid).ok` | **True** |
| `verify_dispatches(rid).total` | 1 |
| `verify_dispatches(rid).mismatches` | `[]` |

**Verdict**: recall round-trip green — runs 2+3 learnings successfully
re-injected into the next plan-stage dispatch via Track B.

## 12 AC matrix

| AC | Description | Result |
|---|---|---|
| AC1 | keeper bundle assets (SKILL.md + 4 subagent prompts + 1 orch helper + 2 scripts + 2 templates) | **PASS** — `bundled/keeper/{SKILL.md, SECURITY.md, prompts/{orchestrator/keeper_iter_revisit.md, subagent/keeper_{audit_step1,extract_step2,summarize_step3,ledger_step4}.md}, scripts/{extract_rules.py, ledger_update.py}, templates/{KEEPER_REPORT.md.template, KEEPER_REPORT_ABORT.md.template}}` all present |
| AC2 | ALLOWED_PROMPT_FILES has 4 keeper entries; ORCHESTRATOR_ONLY_PROMPTS has keeper_iter_revisit | **PASS** — `[keeper_audit_step1.md, keeper_extract_step2.md, keeper_summarize_step3.md, keeper_ledger_step4.md]` allowlisted; `keeper_iter_revisit.md ∈ ORCHESTRATOR_ONLY_PROMPTS` |
| AC3 | inventory.py + harness.py `_BUNDLED_DIR_TO_STAGE` both contain keeper:meta | **PASS** — both maps return `"meta"` for `"keeper"` |
| AC4 | Sub-run 1 (clean): audit_inventory.verdict=audit-skipped, KEEPER_REPORT_ABORT written, ledger unchanged | **PASS** — byte_delta=0, 4 H2 sections, ABORTED in report |
| AC5 | Sub-run 2 (scope-deviation seeded): ledger +1 R2 entry | **PASS** — 1 row, rule_id=R2, category=scope-deviation |
| AC6 | Sub-run 3 (verify-fail seeded): ledger +1 R3 entry | **PASS** — 1 row, rule_id=R3, category=ac-failure |
| AC7 | Sub-run 4 (recall): wrapped prompt contains `[PRIOR LEARNINGS]` fence with entries from runs 2+3 | **PASS** — fence present, both (R2) src/auth.py and (R3) pytest entries present |
| AC8 | KEEPER_REPORT.md happy variant has 7 H2 sections; ABORT variant has 4 | **PASS** — sub-runs 2/3 = 7, sub-run 1 = 4 |
| AC9 | `verify_dispatches(rid).ok=True` for all sub-runs (preamble sha invariant preserved) | **PASS** — sub-run 4 dispatches via `dispatch_and_record` and verify_dispatches.ok=True with mismatches=[]. Sub-runs 1-3 do not dispatch through the harness (self-execute via subprocess), so verify_dispatches is vacuously satisfied (no records to audit) |
| AC10 | Wall time: self-execute mode ≤ 60s total across all 4 sub-runs | **PASS** — total = 0.085 + 0.084 + 0.086 + 0.0009 ≈ **0.26 s** (well under 60 s budget by ~230×) |
| AC11 | Codex retro applied amendments documented in spike-x-codex-retro.md | **PASS** — `docs/dogfood/spike-x-codex-retro.md` exists; Finding 1 (R2 deny object-form fix) applied via `_load_deny_patterns` in `extract_rules.py` (lines 115-138, commit `e212e11`) |
| AC12 | Pytest count: ≥ baseline 745 (now 750+) + Phase F integration tests; 0 failures | **PASS** — 750 baseline → **759 passed, 0 failed** (+9: 6 keeper E2E + 3 verify_dispatches regression) |

**Overall**: **12/12 PASS**.

## Wall-time summary

| Sub-run | extract_rules | step3 (in-proc) | ledger_update | total |
|---|---|---|---|---|
| 1 (clean) | ~0.04 s | ~0.0 s | ~0.04 s | **0.085 s** |
| 2 (R2)    | ~0.04 s | ~0.0 s | ~0.04 s | **0.084 s** |
| 3 (R3)    | ~0.04 s | ~0.0 s | ~0.04 s | **0.086 s** |
| 4 (recall)| n/a     | n/a    | n/a           | **0.001 s** |
| **TOTAL** |         |        |               | **~0.26 s** |

Self-execute mode keeps the keeper pipeline well under the 60-second
budget. Each subprocess invocation adds Python interpreter startup
(~0.04 s on this machine) — that dominates the wall time. The actual
script logic (rule extraction + ledger I/O) is sub-millisecond.

## Ledger byte-count deltas

| Sub-run | bytes before | bytes after | delta |
|---|---|---|---|
| 1 (clean / audit-skipped) | 0 | 0 | **0** |
| 2 (R2 scope-deviation) | 0 | 375 | **+375** |
| 3 (R3 ac-failure) | 0 | 311 | **+311** |

Each sub-run starts with a fresh `tmp_path` ASSEMBLE_HOME so the deltas
above are absolute (not cumulative). In sub-run 4, the seeded
`learnings.jsonl` is pre-populated; the ledger is read for fence
rendering but not modified by the dispatch.

## Notes

- All 4 sub-runs ran against fresh `tmp_path` sandboxes so the global
  `~/.claude/channels/assemble/learnings.jsonl` was never touched.
- Self-execute mode replaces the real Agent dispatch chain for
  steps 1-3 (subprocess invocation of the bundled scripts). This is a
  faithful test of the deterministic logic — Steps 1, 2, 4 are all
  pure file IO + subprocess + git probes, and Step 3 in V4 uses
  deterministic template substitution as the primary path
  (LLM-future).
- Sub-run 4 exercises the full `dispatch_and_record` → Track B splice
  → `verify_dispatches` round-trip with a non-empty seeded ledger,
  proving the recall path is wired end-to-end.
- The Codex retro Finding 1 fix (`_load_deny_patterns` accepting
  object-form `{"path": str, "note": str}`) is exercised by sub-run 2
  — its seed uses the production parser's object-form schema verbatim.
