# Iteration emphasis dispatch guide (orchestrator-facing)

This file is loaded by the main Claude during Step 6 yes-path (per SKILL.md). It guides the orchestrator on how to fan-out emphasis into 4 parallel sub-agent dispatches.

## Inputs from emphasis AskUserQuestion

After yes-answer, fire one `AskUserQuestion` with 4 sub-questions:

- prd_emphasis: "PRD에서 어디가 어색해?"
- arch_emphasis: "ARCH에서 어디가 어색해?"
- adr_emphasis: "ADR에서 어디가 어색해?"
- ui_emphasis: "UI_GUIDE에서 어디가 어색해?"

Each answer can be "(no change)" or a specific concern.

## 4-way parallel dispatch (single message, 4 Agent calls)

Build 4 prompts by loading existing prompt files and *appending* an iteration-mode header per the iteration scope discipline rule (spec §3 / SKILL.md Step 6 verbatim):

```
[ITERATION MODE — iteration {{ITERATION_COUNT}}]
emphasis: {{EMPHASIS}}
existing PRD: {{PRD_TEXT}}
existing ARCH: {{ARCH_TEXT}}
existing ADR: {{ADR_TEXT}}
existing UI_GUIDE: {{UI_TEXT}}

Scope discipline: PRD `## Core features` is the authoritative scope. Do not introduce new features, modules, components, screens, or token sets that have no counterpart in the existing PRD `## Core features`. Items the ADR has explicitly deferred (`> **Future ADRs**`) MUST NOT be pre-emptively decided. Existing sections that are not the explicit target of the iteration emphasis MUST be returned verbatim — do not reword Reasoning/Tradeoffs/Rejected-alternatives blocks just because you are re-emitting the document. Pre-existing identifiers (variable names, token names, module names, component names) MUST NOT be renamed unless the rename IS the requested change.
```

Each of the 4 sub-agents (loading prd_step2 / arch_step8 / adr_step11 / ui_step13 per their existing pattern) writes its respective doc and returns `WROTE: <path>`.

After all 4 return, dispatch Step 9 cross-doc review (with `iteration_count` incremented).
