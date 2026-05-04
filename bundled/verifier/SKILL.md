---
name: "verifier"
description: "Verify-stage ★ bundle. Executes parsed_scope.json completion bash and emits deterministic exit-code verdict. Sub-agents own all reads/writes/Bash; main Claude orchestrates only."
stages: ["verify"]
---

# verifier ★ — completion criterion runner

## Status

This SKILL.md body is **scaffolding only** (Spike VIII A1). Full When-to-invoke / Inputs / Artifacts / Verdict logic / CRITICAL orchestrator-only / Step-by-step / Iteration audit invariant / Sub-agent matrix / Identity guards lands in Task A7.

Sub-agent prompts (Step 1 extract, Step 2 execute, Step 3 classify, Step 4 report) land in A2/A3/A5/A6. Security model lands in A4 (`SECURITY.md`). Contracts entries + Codex retro land in A8.

DO NOT dispatch this bundle yet — sub-agent prompts are missing until A2~A6.
