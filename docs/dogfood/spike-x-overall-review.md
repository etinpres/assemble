# V4 Spike X — Overall Code Review (Phase E1)

**Scope**: Full diff `d1179ea..30fb360` (11 commits, 39 files, +5778/-5).
**Test status**: 745 pass, 0 fail (verified locally).
**Preamble integrity**: `bundled/_shared/harness-preamble.md` byte-unchanged (verified: empty diff).
**Reviewer model**: claude-opus-4-7

---

## Executive verdict

**SHIP-READY with two carryforwards.** The Spike X cross-bundle learning recall infrastructure is well-architected, has thorough test coverage (+182 tests in this spike alone), and preserves all V4 invariants (preamble sha ALLOW_LIST, allowlist roundtrip, audit-trail integrity). Track B's `wrap_with_preamble_and_learnings` carefully threads a fence into the body region without disturbing the canonical preamble bytes — the design is principled and the tests exhaustive on this point.

Two real findings (one Important, one Minor); the rest are confirmed-non-findings.

---

## Findings by severity

### Important — F-X1: R4 false-positive on TODO-comment relocation

**File**: `bundled/keeper/scripts/extract_rules.py` (rule_r4_todo_leakage)

**Behavior**: `git diff --unified=0 HEAD~..HEAD` on a refactor that *moves* a pre-existing TODO/FIXME/XXX line emits `-# TODO: …` (deletion) plus `+# TODO: …` (addition). The script only inspects `+`-prefixed lines and emits an R4 candidate for each — even though the marker count in the working tree is unchanged.

**Test status**: `test_R4_unchanged_TODO_no_candidate` covers in-place modify; does NOT cover the move case (TODO line literally deleted from line N, re-added at line M).

**Impact**: Generates spurious `todo-leakage` learnings on every refactor that moves a TODO comment. Pollutes ledger and dilutes signal. Won't crash anything (TTL + cap absorb).

**Recommendation (carryforward)**: Spike XI keeper polish. Possible mitigation: subtract deleted markers from added markers to compute net delta. 1-line workaround inside `rule_r4_todo_leakage` catches >90% of cases.

### Minor — F-X2: STAGE_CATEGORY_PRIORITY remains mutable list-of-list

**File**: `server/learnings.py` (line 44-52)

**Behavior**: `STAGE_CATEGORY_PRIORITY: dict[str, list[str]]`. Concern raised in A1 review S2 carryforward; still not applied.

**Impact**: Theoretically a misbehaving caller could mutate the priority list and pollute global state. In practice, no caller does. Pure code-hygiene concern.

**Recommendation (carryforward)**: Tuple-ize values. 5-line change, no behavior impact. Spike XI fold-in.

### Minor — F-X3: `_PROMPT_TO_STAGE` lookup miss falls through silently

**Status**: Not actually a finding. CI test `test_prompt_to_stage_covers_all_allowed` catches missing keys at PR review. Runtime fallback to no-fence is graceful.

---

## Confirmed non-findings (concerns evaluated and cleared)

### Concern #1 — Track B preamble sha invariant under nested `\n[TASK]\n` body
SAFE. Three layers of defense: preamble file has zero `[TASK]` literals; `wrap_with_preamble` always prepends preamble first; `replace(..., 1)` matches first occurrence only. Test `test_only_first_task_delim_replaced` covers this.

### Concern #2 — Other unbounded-iteration sites
SAFE. Audit covered server/learnings.py, server/harness.py, both keeper scripts. Only `Iterable` parameter is `write_ledger` which materializes via `list(entries)` (A3-fix).

### Concern #4 — `prune_ledger` rule order edge cases
SAFE. Pathological case (100 stale at cap, all skiplisted) plays out correctly. Tests `test_prune_rule_order_ttl_drops_before_dedup_can_save` + `test_prune_fifo_cap_drops_oldest_first` cover ordering.

### Concern #5 — T5 multi-process race window honesty
ACCURATE documentation. SECURITY.md states "the second's write clobbers the first's appends" — exactly the lost-update interleaving.

### Concern #6 — V4 identity preservation
VERIFIED. `git diff d1179ea..HEAD -- bundled/_shared/harness-preamble.md` returns empty.

### Concern #7 — `_PROMPT_TO_STAGE` completeness
VERIFIED. 39 entries in ALLOWED_PROMPT_FILES, 39 entries in _PROMPT_TO_STAGE. Test asserts bidirectional equality.

### Concern #9 — `ledger_update.py` 533-line cohesion
ACCEPTABLE for V4. Functions are single-purpose. Splitting would create import overhead. Revisit if Spike XI adds helpers.

### Concern #10 — B4 keeper_summarize "LLM-future" framing honest?
HONEST. Lines 27-31 explicitly state the LLM-future framing. Exemplary documentation.

---

## B-15 dogfood readiness

**Recommend SHIP**. Track B core wiring mathematically sound. F-X1 + F-X2 are minor polish for Spike XI without blocking V4 stage-cover completion.

Suggested B-15 dogfood AC additions:
- AC: keeper end-to-end on real run_dir → `learnings.jsonl` contains expected entries with non-empty `evidence_hash`
- AC: subsequent dispatch via `dispatch_and_record` includes `[PRIOR LEARNINGS — 우선 회피]` fence in body, `verify_dispatches.ok=True`
- AC (regression for F-X1): TODO-move refactor produces ≤1 R4 candidate, not 2

---

## Files cited

server/harness.py, server/learnings.py, server/git_helpers.py, server/inventory.py, bundled/keeper/SKILL.md, bundled/keeper/SECURITY.md, bundled/keeper/scripts/extract_rules.py, bundled/keeper/scripts/ledger_update.py, bundled/keeper/prompts/subagent/keeper_summarize_step3.md, tests/contracts/contracts.json, tests/unit/test_wrap_with_preamble_and_learnings.py, tests/unit/test_learnings_ledger.py, tests/unit/test_keeper_extract_rules.py, tests/unit/test_keeper_inventory_scan.py
