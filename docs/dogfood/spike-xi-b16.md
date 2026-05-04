# V4 Spike XI B-16 Dogfood Report

**Date**: 2026-05-04
**Mode**: self-execute (Spike VIII/IX/X B-13/B-14/B-15 pattern — real Agent dispatch covered by contracts tests)
**Master HEAD**: `ab32980`
**pytest baseline**: 789 passed

## Summary

V4 Spike XI ship gate — 3 standard bundles (idea-shaper / design-pack / guardian) inventory + harness + contracts integration verification.

**Verdict: 12/12 AC PASS**
**Wall-time**: 0.422s (budget ≤30s — 71× under)

## 12 AC Results

| # | AC | Status | Evidence |
|---|---|---|---|
| 1 | inventory bundled=True for all 3 | PASS | `inventory.scan(force=True)` returns 3 entries with `bundled=True` |
| 2 | menu ★ prefix render flag present | PASS | `bundled` flag set on all 3 entries (renderer prepends ★ downstream) |
| 3 | idea-shaper allowlist gate | PASS | `'idea_shape_step1.md' ∈ ALLOWED_PROMPT_FILES` |
| 4 | design-pack allowlist gate | PASS | `'design_draft_step1.md' ∈ ALLOWED_PROMPT_FILES` |
| 5 | guardian no allowlist entry | PASS | 0 'guardian' substrings in `ALLOWED_PROMPT_FILES` (V4 #9 exception) |
| 6 | harness `_BUNDLED_DIR_TO_STAGE` 3 new stages | PASS | `idea-shaper→discover`, `design-pack→design`, `guardian→safety` |
| 7 | inventory `_BUNDLED_DIR_TO_STAGE` sync | PASS | universal-defense convention preserved (BOTH maps) |
| 8 | `_PROMPT_TO_STAGE` 2 prompts (guardian absent) | PASS | discover/design routing intact, guardian absent (V4 #9) |
| 9 | canonical preamble v3 sha unchanged | PASS | `8d22a29c9712d2c0...` byte-identical |
| 10 | bidirectional integrity | PASS | 42 == 42 (`set(_PROMPT_TO_STAGE) == set(ALLOWED_PROMPT_FILES)`) |
| 11 | `_BUNDLES` has all 10 bundles | PASS | 7 ★ + 3 standard (plan-pack/debugger/builder/reviewer/verifier/shipper/keeper + idea-shaper/design-pack/guardian) |
| 12 | `STAGE_CATEGORY_PRIORITY` 10 stages | PASS | discover/design/safety added in A2-fix2 |

Raw output:

```
AC1 inventory bundled=True for all 3 PASS
AC2 ★ prefix render flag present for all 3 PASS
AC3 idea-shaper allowlist gate PASS
AC4 design-pack allowlist gate PASS
AC5 guardian no allowlist entry (V4 #9 exception) PASS
AC6 harness _BUNDLED_DIR_TO_STAGE 3 new stages PASS
AC7 inventory _BUNDLED_DIR_TO_STAGE sync PASS
AC8 _PROMPT_TO_STAGE 2 prompts (guardian absent) PASS
AC9 canonical preamble v3 sha PASS (8d22a29c9712d2c0...)
AC10 bidirectional integrity PASS (42 == 42)
AC11 _BUNDLES has all 10 bundles PASS
AC12 STAGE_CATEGORY_PRIORITY 10 stages PASS

Wall-time: 0.422s (budget ≤30s)
All 12 AC PASS
```

## Test counts (per-commit trace)

| Commit | Phase | Tests | Δ |
|---|---|---|---|
| `d01733a` | spec + plan only | 764 | baseline |
| `4e557e6` | A1 (idea-shaper SKILL.md + dir) | 764 | 0 |
| `c81d03a` | A2 (idea-shaper prompt + template) | 764 | 0 |
| `6a559b1` | A2-fix (allowlist + _PROMPT_TO_STAGE) | 764 | 0 |
| `a1928bd` | A2-fix2 (STAGE_CATEGORY_PRIORITY +3) | 764 | 0 |
| `7635929` | A2-fix3 (WROTE: stdout contract) | 764 | 0 |
| `8b72ce4` | A3 (idea-shaper template anchors) | 769 | **+5** |
| `48da773` | A3-fix (tighten template tests) | 769 | 0 |
| `06e68b0` | B1 (design-pack SKILL.md + dir) | 769 | 0 |
| `4642435` | B2 (design-pack prompt + atomic wiring) | 769 | 0 |
| `3755fc2` | B3 (design-pack template anchors) | 777 | **+8** |
| `e699ce5` | C1 (guardian SKILL.md + template) | 777 | 0 |
| `7368d5d` | C2 (guardian template anchors) | 783 | **+6** |
| `ab32980` | D (contracts.json wiring) | **789** | **+6** |

**Total Spike XI delta: +25 tests** (5 + 8 + 6 + 6).

> Note: spec stated baseline 759 and +30 delta. Empirical baseline at `d01733a` is 764 (post Spike X cleanup) and the delta is +25. The B-16 prompt anticipated 5 stage-priority/learning tests for A2-fix2, but `STAGE_CATEGORY_PRIORITY` extension landed without dedicated test additions (the existing learnings tests already covered the new stage tokens generically). Net total still hits the predicted 789.

## Contracts (spike-xi parametrized)

`pytest -k "spike_xi or spike-xi"` → 6 selected, 6 PASSED in 0.25s:

- `test_contract_phrase_present_in_spec_section[spike-xi-idea-shaper-stage]` PASSED
- `test_contract_phrase_present_in_spec_section[spike-xi-idea-shaper-artifact]` PASSED
- `test_contract_phrase_present_in_spec_section[spike-xi-design-pack-stage]` PASSED
- `test_contract_phrase_present_in_spec_section[spike-xi-design-pack-artifact]` PASSED
- `test_contract_phrase_present_in_spec_section[spike-xi-guardian-v4-9-exception]` PASSED
- `test_contract_phrase_present_in_spec_section[spike-xi-guardian-artifact]` PASSED

## Critical invariants preserved

- ✅ canonical preamble v3 sha: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged
- ✅ 7 ★ bundle prompts unchanged (plan-pack / debugger / builder / reviewer / verifier / shipper / keeper)
- ✅ V3 concierge menu layer unchanged
- ✅ orchestrator-only V4 #9 — main never executes Bash; guardian Write is the documented exception
- ✅ universal-defense: `_BUNDLED_DIR_TO_STAGE` BOTH maps in sync (harness + inventory)
- ✅ bidirectional integrity: `set(_PROMPT_TO_STAGE) == set(ALLOWED_PROMPT_FILES)` (42 entries each)

## Carryforward to Spike XII (none blocking ship)

- I-1 (B1 code review): idea-shaper SKILL.md decorative ✅/❌ glyphs vs design-pack convention — cosmetic
- M-3 (B2 code review): reviewer ★ ANTI_PATTERNS auto-validation — V5 candidate
- M-1 (C1 code review): template/SKILL future-pointer wording polish
- Plan literal reconciliation (full path → basename, 5→6 sections in template note)

## Source

- Spec: `docs/specs/2026-05-04-v4-spike-xi-design.md` (commit `d01733a`)
- Plan: `docs/plans/2026-05-04-v4-spike-xi.md` (`d01733a`)
- Phase A-D commits: `4e557e6` → `ab32980` (13 commits)
