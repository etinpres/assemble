# Platform-limit experiment — single-message parallel Agent dispatch

**Date:** 2026-04-29
**Context:** Phase B-5 prep. Three consecutive phases (B-3, B-4) had fallen back to sequential Agent dispatch out of orchestrator caution about a hypothetical platform Agent-call budget per assistant turn. Before formalizing 4-way parallel as the canonical iteration write surface, the assumption needed empirical verification.

## Hypothesis

When the main Claude orchestrator emits multiple `Agent` tool_use blocks within a single response message, at what N does the platform reject, rate-limit, or silently degrade the dispatch?

## Method

Four trials. Each trial = one assistant response with N parallel `Agent` tool_use blocks, all targeting `general-purpose`. Each agent received the identical minimal prompt:

> 정확히 다음 한 줄만 출력하고 종료해라:
>
> SENTINEL_T<N>_<idx>
>
> 다른 어떤 텍스트도 출력하지 마라. 파일을 읽지 마라. 다른 도구를 호출하지 마라. 토론하지 마라. 위 sentinel 한 줄이 전부다.

The sentinel design isolates the dispatch acceptance + return integrity signal from any agent-side variance.

| Trial | N | agentType |
|---|---|---|
| T2 | 2 | `general-purpose` |
| T3 | 3 | `general-purpose` |
| T4 | 4 | `general-purpose` |
| T5 | 5 | `general-purpose` |

Measured per trial:
1. **Dispatch acceptance** — were all N tool_use blocks accepted by the platform (no immediate validation error)?
2. **Return integrity** — did all N agents return their expected `SENTINEL_T<N>_<idx>` line?
3. **Timing pattern** — overlapping durations (parallel) vs cumulative (serialized)?

## Results

| Trial | N | Dispatch acceptance | Return integrity | Per-agent durations (ms) | Timing pattern |
|---|---|---|---|---|---|
| T2 | 2 | ✓ 2/2 | ✓ 2/2 | 2078, 2801 | overlap (parallel) |
| T3 | 3 | ✓ 3/3 | ✓ 3/3 | 2096, 2153, 1989 | overlap (parallel) |
| T4 | 4 | ✓ 4/4 | ✓ 4/4 | 1880, 2828, 3101, 2074 | overlap (parallel) |
| T5 | 5 | ✓ 5/5 | ✓ 5/5 | 2170, 2226, 1641, 1818, 2434 | overlap (parallel) |

Zero rejects. Zero rate-limits. Zero silent degrades. No trial showed cumulative timing (the signature of secret serialization).

## Verdict

**The platform tolerates at least 5-way parallel Agent dispatch in a single assistant response.** The 4-way case (B-5 spike target) is well within the observed headroom. The orchestrator caution that drove B-3 / B-4 sequential fallback was not evidence-based.

## Decision (B-5)

1. **plan-pack `bundled/plan-pack/SKILL.md` stays.** No sequential canonical rewrite. Steps 2/3 and Step 6 step 4 retain "single message, parallel dispatch" as the canonical invocation.
2. **Caveat language tightens.** The prior caveat ("sequential dispatch remains acceptable per the same B-3 dogfood Finding #4 caveat — single-message Agent-call budget concerns") is replaced by a citation block pointing to this document. Sequential fallback is now restricted to two specific cases: documented input dependency, or orchestrator-detected retry-after on a previous attempt. General "caution" is no longer sufficient grounds.
3. **`wrap_with_preamble` discipline reframes.** Separate Item B-2 fix: the byte-identity guarantee is decoupled from the function-call discipline. Orchestrator may inline the preamble literal as long as every dispatched prompt's preamble block hashes to the canonical preamble file's sha256. Verified at dogfood time via gate B5.7.

## Limitations / future verification

- The trial dispatched dummy 1-line tasks. Realistic 4-way iteration dispatches send ~2-5KB prompts each (PRD body + emphases + scope discipline block). Not tested whether prompt size influences acceptance — but the platform-side validation happens on tool_use schema, not prompt content.
- The trial used a single agentType (`general-purpose`). Mixed agentTypes (e.g. `superpowers:code-reviewer` + `general-purpose` in one turn) are not separately verified.
- Trial run from a single session, so any hypothetical "rate limit per N seconds" higher than 14 calls per ~60 seconds was not stressed.

These limitations don't change the B-5 decision (4-way is achievable). They are noted so future contributors don't over-claim "infinite parallel" from this evidence.

## Replication

The experiment can be replicated from any /assemble session:

1. Issue four trials in sequence, each in its own assistant response.
2. For trial N, dispatch N `general-purpose` agents in a single response with the minimal prompt above.
3. Confirm all N return their distinct sentinels and durations overlap.

If a future trial fails (e.g. platform changes), the SKILL.md prose changes accordingly — sequential fallback returns as canonical.
