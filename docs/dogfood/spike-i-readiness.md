# Spike I post-implementation readiness (B-6 dogfood prep)

Spike I implementation complete (2026-04-30). Ready for B-6 dogfood execution.

## What changed

- plan-pack SKILL.md: sub-agent path-only return contract (732→323 lines)
- 8 new prompts/ files (7 sub-agent + 1 orchestrator-facing)
- harness-preamble v2 (rules 5 한국어 quality + 6 anti-downscale)
- hook v1 Bash matcher (magic marker `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE`)
- Step 6 yes-path label J-6 fix (`강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증`)
- record_dispatch wrote_path optional + verify_dispatches v1/v2 ALLOW_LIST
- Test suite: 192 passed (added 13 new tests, re-anchored 31 stale)

## What did NOT change (deferred)

- J-1/J-2/J-3/J-4 menu layer (Spike II)
- Item A multi-iter stop condition algorithm (Spike II)
- Items C/D/E/F (quality + hygiene passes)
- Other ★ candidate bundles (separate spikes)

## B-6 acceptance criteria (run 1 plan-pack end-to-end)

1. **0 main direct-write**: `runs/<rid>/dispatches.jsonl` shows wrote_path on every Step 2/3/8/11/13/9 dispatch row; no main-side `Edit|Write|NotebookEdit|Bash` write to runs/.
2. **0 hook block on legitimate path**: sub-agent canonical save block invocations all pass; only main bypass attempts trigger exit 2 (which should be 0 in a clean run).
3. **New label workflow alignment**: Step 6 entry shows "강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증" + actual yes-path executes interview → 4-way redraft → Step 9 review.
4. **Korean quality**: Sub-agent-emitted option labels are natural Korean (no 좌히기/PRD emp shapes).
5. **Anti-downscale**: No main suggestion of doc skip / iteration downscale, even if the user task statement is small.

## Run command (proposal)

```
/assemble  # in a fresh dir; pick a "1-page idea" task
# expected sequence: choose plan-pack ★ → run full bundle → 1 iteration
```

## Failure modes to watch

- Sub-agent fails import (Q2 regression): plan §11 Open question. Recovery: per CRITICAL anti-fallback rule, AskUserQuestion retry/abort, never main fallback.
- Hook v1 false positive (sub-agent prompt without marker, e.g. external dispatch): expected 0 in plan-pack scope; if other bundles use sub-agent-write later, marker convention must propagate (Spike II memo).
- Hook v1 false positive (read-only python3 invocation against runs/ paths): noted in Task 9 review, low practical impact (main has Read tool); not a B-6 blocker. If observed, tighten regex in v2.
- COUNTS line missing/malformed: SKILL.md Step 9 says treat as Step 9 dispatch failure per §CRITICAL — surface to user, do not advance to Step 6. Watch for this if cross_doc_step9 sub-agent leaves Ellipsis literals unfilled.

## Code review carryforward (plan-revision tracker)

Items reviewers flagged but were inherited from plan source / out of Spike I scope. Address in post-B-6 polish or Spike II:

1. Bare `...` Ellipsis literals in prompt body templates (could ship literally if sub-agent doesn't fill)
2. "Return only file path" wording vs `print(f"WROTE: {path}")` actual mechanism — clarify in plan revision
3. Mixed-language tokens in iter_emphasis Korean sub-questions ("4-doc", "cross-doc") vs harness rule 5
4. Step 6 entry vs §"User exit override" condition asymmetry — consider explicit selector
5. ui_step13 antipattern keyword list false-positive on legitimate domain vocabulary (e.g. paint app with gradients)
6. prompts/ directory mixes orchestrator-facing (iter_emphasis) and sub-agent-facing (others) — consider subdirectory split

None of these block B-6.
