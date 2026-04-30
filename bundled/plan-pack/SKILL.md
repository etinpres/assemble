---
name: plan-pack
description: Plan stage ★ bundle — produce PRD + ARCH + ADR + UI_GUIDE with iteration. Spec, requirements, plan, architecture doc, decision record, UI guide — bundled plan tool. (V4 Spike I: sub-agent path-only return contract.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
5. 사용자에게 표시되는 한국어 라벨·옵션은 자연스러운 한국어로 정제. 영문 기술용어 한글화 시 정확한 외래어 표기 사용 (architecture→아키텍처, family→패밀리, top-level→최상위, recommended→추천, directory→디렉토리). 자작 변형 금지.
6. task scope은 seed이지 contract가 아니다 — 풀번들 4개 doc 모두 작성
7. 다른 스킬 인프라 코드 read·grep 금지 — 자기 task 무관 분석은 우회 시도 신호

## CRITICAL — orchestrator-only enforcement

This skill is **orchestrator-only**. The main Claude (you) dispatches sub-agents
and parses their `WROTE: <path>` stdout. You MUST NOT fall back to
Bash/Edit/Write/python3 to write artifacts directly under `runs/<rid>/`.
The hook `guard_run_dir.sh` blocks such bypass attempts.

If a sub-agent dispatch fails (no `WROTE:` line, `ERROR:` line, timeout, or
empty stdout):
1. Surface the failure to the user via `AskUserQuestion`:
   "Step N failed. Retry / abort / report?"
2. Wait for user choice. Do not auto-recover.
3. NEVER attempt to write the artifact yourself, even "just to unblock the
   user". Sub-agent ownership is the contract.

If retry is chosen, re-dispatch the same sub-agent with the failure context
(`previous attempt failed: <reason>`) appended to the original prompt.

**Anti-bypass (Spike II F9 + F11):**

- `~/.claude/settings.json` 편집해서 `ASSEMBLE_GUARD` 환경 변수 무력화 시도 금지. hook 자체를 비활성화/우회 시도는 사용자 confirm 이 떠도 거절.
- hook 이 차단하면 즉시 `AskUserQuestion` 으로 사용자 결정 위임 (retry / abort / report). hook 차단을 회피하기 위한 sub-agent dispatch (예: "iteration_state.json 업데이트 해 달라" 라는 task로 sub-agent 호출) 금지.
- sub-agent dispatch 는 `bundled/plan-pack/prompts/` 디렉토리의 *8개 파일* (`prd_step2`, `prd_step3`, `prd_step4`, `arch_step8`, `adr_step11`, `ui_step13`, `cross_doc_step9`, `iter_emphasis`) 에 한정. orchestrator 메타데이터 (`iteration_state.json`, `dispatches.jsonl`, `progress.json` 등) 는 sub-agent 에 위임 금지 — `server.run_dir.update_iteration_state` 같은 server 함수 사용 (Phase D 에서 추가).

## Korean label policy (Spike II F4)

When `ASSEMBLE_LOCALE=ko` (or user message language is Korean), AskUserQuestion
options that historically carry English `(Recommended)` suffix MUST use the
unified Korean form `(추천)`. Do not improvise alternatives like `(승인)` —
those drift from the platform-wide V4 한국어 라벨 정책.

Example:
- `"yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증 (추천)"` ✓
- `"yes — ... (Recommended)"` ✗ (혼합 영어)
- `"yes — ... (승인)"` ✗ (자작 변형)

`(추천)` 만 사용. Other label languages keep their native suffix (English →
`(Recommended)`).

# plan-pack — PRD + ARCH + ADR + UI_GUIDE generator

Produces four planning docs from one orchestrated workflow. Main Claude
runs `AskUserQuestion` interviews; sub-agents (wrapped via
`server.harness.wrap_with_preamble`) own all template filling and
`write_run_artifact` calls and return `WROTE: <path>` on stdout.

## Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. Four artifacts under
run_dir, each from a matching template under `bundled/plan-pack/templates/`:
`PRD.md`, `ARCHITECTURE.md`, `ADR.md`, `UI_GUIDE.md`.

## Sub-agent role mapping (Phase B-4 + Spike I)

All dispatches use `general-purpose` (preferred + fallback). Role and
prompt file vary per step. (*Role* = prompt persona shaping the
sub-agent's behavior; Agent tool type is always `general-purpose`.)

| Step | Role | Prompt file |
|---|---|---|
| 2 | `plan-implementation` | `prompts/prd_step2.md` |
| 3 | `plan-implementation` | `prompts/prd_step3.md` |
| 4 | `second-opinion` | `prompts/prd_step4.md` |
| 8 | `plan-implementation` | `prompts/arch_step8.md` |
| 9 | `second-opinion` | `prompts/cross_doc_step9.md` |
| 11 | `plan-implementation` | `prompts/adr_step11.md` |
| 13 | `plan-implementation` | `prompts/ui_step13.md` |

Steps 0/1/7/10/12 are user-facing `AskUserQuestion` interviews. Steps 2+3
fire as a single parallel message (B-1 surface). Steps 8/11/13 are
single-dispatch first-pass; Step 6 yes-path promotes 8/11/13 + 2/3 to
4-way parallel (B-5).

## Workflow execution sequence

```
0 → 1 → (2 + 3 in parallel) → 4 → 7 → 8 → 10 → 11 → 12 → 13 → 9 → 6
```

Step numbers reflect historical addition order, not execution order. Step 4
(PRD second-opinion) sub-agent writes the updated `PRD.md` itself, so no
separate main-write step is needed (the prior Step 5 has been deleted in
Spike I). Step 9 runs after all four docs are written. Step 6 (iteration) is
final. Do NOT run steps in numeric order.

## Steps

### Step 0 — resolve run_dir

Read `<rid>` from the active assemble run. The artifact path is
`~/.claude/channels/assemble/runs/<rid>/PRD.md`. If the file already
exists, treat the workflow as iteration mode (Step 6 yes-path entry).

### Step dispatch contract (Steps 2/3/4/8/11/13/9)

For each dispatch step:

1. `prompt_text = server.dispatch_prompt("<file>.md")` — loads the prompt
   under `bundled/plan-pack/prompts/{subagent,orchestrator}/` (resolver
   checks both subdirs + flat fallback) and prepends the harness preamble
   via `server.harness.wrap_with_preamble` (byte-identity contract
   surface). Unknown `<file>.md` raises `ValueError` (anti-bypass guard,
   Spike III §1.2). The function does **not** substitute placeholders —
   `{{KEY}}` tokens come back intact.
2. Substitute placeholders against `prompt_text` yourself, e.g.
   `prompt_text = prompt_text.replace("{{TASK}}", task)`. The orchestrator
   owns which `{{KEY}}` tokens are caller-substituted (Inputs section)
   vs. preserved for the sub-agent's own `.replace` instructions inside
   the canonical save block. A naive global `.replace` over both classes
   would corrupt the latter — Spike III §1.2 rationale.
3. call
   `server.harness.record_dispatch` for the on-disk evidence trail
   (`runs/<rid>/dispatches.jsonl`) — invoke as
   `server.record_dispatch(run_id, step, prompt_text, subagent_type="general-purpose", prompt_file="<file>.md", description="...", wrote_path=...)`
   to append the hash-only audit row. The `prompt_file=` kwarg matches
   the allowlist (Spike III §1.2).
4. Dispatch to `general-purpose` via the Agent tool with `prompt_text`.
5. Sub-agent prints `WROTE: <path>` on stdout — parse with regex
   `^WROTE: (.+)$`. On `ERROR:` or missing `WROTE:`, follow §CRITICAL.

Sub-agents MUST replace every `<TBD: ...>` sentinel inside their
canonical save-block triple-quoted strings with concrete content before
printing `WROTE:`. A literal `<TBD: ...>` (or bare `...`) reaching
`write_run_artifact` is a contract violation — surface as `ERROR:` and
follow §CRITICAL. Spike III §2.1 + `tests/unit/test_prompts_no_bare_ellipsis.py`.

`record_dispatch` 시그니처 (verbatim — `from server import record_dispatch`):

```python
record_dispatch(
    run_id: str,
    step: str,
    prompt_text: str,
    *,
    subagent_type: str = "",
    description: str = "",
    wrote_path: Optional[str] = None,
    prompt_file: Optional[str] = None,
) -> Path
```

`role` kwarg 없음. 위 표 (Step → Role) 의 *Role* 은 prompt 본문에 자연어로 박히는 페르소나 라벨이고 `subagent_type` 은 항상 `"general-purpose"` 다. `record_dispatch(..., role=...)` 로 호출하면 `TypeError`. `prompt_file` 은 `ALLOWED_PROMPT_FILES` 외 값이면 stderr 경고 (default) 또는 `ValueError` (`ASSEMBLE_DISPATCH_STRICT=1`).

### Step 1 — PRD interview (main Claude, AskUserQuestion)

8 questions across **two `AskUserQuestion` calls of 4 questions each**
(platform `maxItems: 4`). Treat as single batch. Call 1 (Q1–Q4): (1) What
building? (2) Who uses it? (3) Three core features? (4) Three exclusions
from MVP (harness #2). Call 2 (Q5–Q8): (5) One-line success criterion?
(6) One AC bash command for external verification? (7) One-line design
direction? (UI_GUIDE seed) (8) One risk / open question?

### Step 2 — PRD body draft (parallel with Step 3)

Prompt: `prompts/prd_step2.md`. Placeholders: `{{TASK}}`,
`{{INTERVIEW_ANSWERS}}`, `{{RUN_ID}}`. Fired in the same parallel message
as Step 3 (true 2-way parallel — see
`docs/research/2026-04-29-platform-limit.md`). Sub-agent partially
populates `PRD.md`; Step 3 fills the AC bash placeholder.

### Step 3 — AC bash draft (parallel with Step 2)

Prompt: `prompts/prd_step3.md`. Placeholders: `{{RUN_ID}}`,
`{{SUCCESS_CRITERION}}`, `{{AC_REQUEST}}`.

### Step 4 — PRD consistency review (second-opinion)

Prompt: `prompts/prd_step4.md`. Placeholders: `{{RUN_ID}}`.
Single Agent call as `second-opinion` (preferred `general-purpose` per v4
swap commit `85366f1`). Sub-agent reads `PRD.md`, triages each critique
bullet via the Step 4b verify-before-appending protocol (1-shot Bash for
runtime claims; drop speculation), prepends an audit header, appends
`## Review notes`, rewrites via `write_run_artifact`. Step 4 is skipped on
the iteration yes-path — Step 9 provides second-opinion coverage there.

### Step 7 — ARCH interview (main Claude, AskUserQuestion)

After Step 4 returns, 6 questions across **two `AskUserQuestion` calls of
3 questions each**. Call 3 (A1–A3): (1) Primary tech stack? (2) Top-level
directory structure? (3) Architectural patterns (MVC, microservices,
event-driven, monolith, CQRS — name + rationale)? Call 4 (A4–A6):
(4) Main data flow ≤3 steps? (5) External services / third-party APIs?
("none" valid) (6) Main modules + boundaries?

### Step 8 — ARCH dispatch

Prompt: `prompts/arch_step8.md`. Placeholders: `{{TASK}}`,
`{{INTERVIEW_ANSWERS}}`, `{{RUN_ID}}`. Sub-agent reads PRD, builds the 6
ARCH sections (Stack, Directory tree, Architectural patterns, Data flow,
External dependencies, Module boundaries), fills
`templates/ARCHITECTURE.md.template`, writes. Proceed to Step 10.

### Step 10 — ADR interview (main Claude, AskUserQuestion)

After Step 8 returns, **two phases** of `AskUserQuestion`:

**Call 5** — *single* `AskUserQuestion` call with **3 sub-questions** (D1, D2, D3 — title only). Each sub-question shape: PRD Q1–Q4 batch shape (multi-select: choose top decisions). multi-select schema MUST include `minSelected: 3, maxSelected: 5` (gate B3.2 minimum). After response, main MUST verify the user selected ≥ 3 decisions; if fewer, re-prompt the same Call 5 with the message "최소 3개 결정이 필요합니다" — do NOT proceed with 2 decisions even if AskUserQuestion returns successfully.

**Call 6** — *3 separate* `AskUserQuestion` calls, **one per decision** chosen in Call 5, each with **3 sub-questions**: (a) strongest rejected alternative, (b) main tradeoff, (c) decision-specific risks/unknowns. The three sub-questions are numbered 1/2/3 within each call. Three calls in sequence, NOT parallel — each subsequent call's wording references the prior decision title for user context.

Three decisions = minimum (gate B3.2); volunteer more → N ≥ 3, accept up to 5.

(Spike II F5/F6: spec 모호함 차단 — "1-question multi-select" 또는 single 6-question call 자유 재해석 금지.)

### Step 11 — ADR dispatch

Prompt: `prompts/adr_step11.md`. Placeholders: `{{TASK}}`,
`{{INTERVIEW_ANSWERS}}`, `{{RUN_ID}}`. Sub-agent reads ARCH + PRD,
synthesizes `### Context` and `### Reasoning` per decision (these two
sub-headings are the sub-agent's job, never the user's), emits
`## Decision N:` blocks with all five sub-headings, fills
`templates/ADR.md.template`, writes. Proceed to Step 12.

### Step 12 — UI_GUIDE interview (main Claude, AskUserQuestion)

After Step 11 returns, 6 questions across **two `AskUserQuestion` calls of
3 questions each**.

**Call 7 (U1–U3):** (1) visual identity / aesthetic, (2) 3 priority flows, (3) 3 required component patterns. Sub-questions U2 and U3 are multi-select with `minSelected: 3, maxSelected: 3` — exactly 3 items each. Main MUST verify the count after response; if user supplied 4+ items via free text or the schema returned fewer than 3, re-prompt that single sub-question only (don't restart Call 7). Spike II F7: B-6 dogfood received 4 answers for U2/U3 — schema 강제 + main 검증으로 차단.

**Call 8 (U4–U6):** (4) ≤5 brand color tokens (hex/named with role; "no preference" valid), (5) primary + 1 supporting font family ("no preference" valid), (6) project-specific antipattern emphasis beyond template baseline ("none" valid). Q6 surfaces project-specific antipattern signal for gate B4.3.

### Step 13 — UI_GUIDE dispatch

Prompt: `prompts/ui_step13.md`. Placeholders: `{{TASK}}`,
`{{INTERVIEW_ANSWERS}}`, `{{RUN_ID}}`. Sub-agent reads PRD `## Design
direction` + `## Core features`, builds the 5-section UI body (Visual
identity, Color tokens, Typography, Component patterns ≥3, Priority
screens ≥3), respects the template's antipattern keyword exclusion list
(gate B4.3), fills `templates/UI_GUIDE.md.template`, writes. Proceed to
Step 9.

### Step 9 — 4-way cross-doc second-opinion

Prompt: `prompts/cross_doc_step9.md`. Placeholders: `{{RUN_ID}}`,
`{{ITERATION_COUNT}}` (read from `runs/<rid>/iteration_state.json`; 0 for
first-pass). Single Agent call as `second-opinion` role.

Sub-agent reads all four artifacts, produces verified findings under 7
categories (PRD↔ARCH gap, ARCH↔ADR decision integrity, PRD↔ADR motivation
traceability, PRD↔UI_GUIDE design audit, ARCH↔UI_GUIDE component coverage,
ADR↔UI_GUIDE UX integrity, numerical/unit consistency), applies the
Step 4b triage, picks heading (`## Cross-doc review` for first-pass,
`## Cross-doc review (iteration N)` for iterations), runs the precondition
assert `heading not in adr_text`, and rewrites `ADR.md`.

Sub-agent prints **two** stdout lines — `WROTE: <path>` and
`COUNTS: resolved=<N> unresolved=<N> new=<N>`. Main parses the second
stdout line with regex `^COUNTS: resolved=\d+ unresolved=\d+ new=\d+$`
(Spike II F10). 매칭 실패 시 (다른 키, 키 누락, 비정수, 추가 토큰)
Step 9 dispatch failure 처리 — §CRITICAL 분기 (retry/abort/report).
Parse both. To update
`runs/<rid>/iteration_state.json` (drives the multi-iteration stop
condition), call `server.update_iteration_state` directly — *do not*
dispatch a sub-agent for this:

```python
from server import update_iteration_state
update_iteration_state(rid, {
    "resolved_pct": resolved / max(resolved + unresolved + new, 1),
    "new_count": new,
    "stopped": False,
    "reason": "",
})
```

orchestrator metadata 는 §CRITICAL 룰 (Spike II F11) 에 의해 sub-agent 위임 금지. hook 화이트리스트 (Spike II F8) 가 main 직접 write 를 허용한다. If the `COUNTS:` line is missing or unparseable (non-integer values, missing key), treat as Step 9 dispatch failure per §CRITICAL — surface to user, do NOT advance to Step 6.

If the precondition assert fires (heading already in ADR.md from a failed
prior iteration overwrite), the sub-agent prints
`ERROR: contract violation: heading ... already in ADR.md`. Surface to the
user via `AskUserQuestion` ("Step 9 contract violation — retry / abort?")
— do NOT auto-recover or edit ADR.md directly. On any other `ERROR:` or
missing `WROTE:`, follow §CRITICAL. After Step 9 returns, proceed to Step 6.

## Step 6 — iteration round-trip

**After the FIRST Step 9 cross-doc review only** (`iteration_count == 0`),
ask the user via `AskUserQuestion`:

> "네 문서 작성 완료 — PRD.md, ARCHITECTURE.md, ADR.md, UI_GUIDE.md.
> 한 차례 반복 진행할까?"
> options: ["yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증", "no — 종료"]

For `iteration_count ≥ 1`, the entry prompt is replaced by §"User exit
override" below (`"반복을 계속할까?"`). The two prompts never both fire on
the same iteration boundary.

- **no → done**: exits the workflow. The user is never forced into a
  second pass (V4 identity rule).
- **yes → emphasis interview + 4-way parallel re-dispatch + cross-doc
  re-review**.

### Step 6 yes-path detail

1. **Emphasis interview** (main Claude, AskUserQuestion). Per
   `prompts/iter_emphasis.md`, fire one `AskUserQuestion` with 4
   sub-questions (PRD/ARCH/ADR/UI). Each answer can be "(no change)" or a
   specific concern.

2. **Per-doc emphasis substitution (Spike II F14):** main constructs ONE
   prompt per doc — 4 prompts total, each based on `iter_emphasis.md` —
   with placeholders: `{{ITERATION_COUNT}}`, `{{RUN_ID}}`, `{{DOC_NAME}}`
   (one of `PRD.md`/`ARCHITECTURE.md`/`ADR.md`/`UI_GUIDE.md`),
   `{{EMPHASIS}}` (per-doc answer from emphasis interview),
   `{{EMPHASIS_SECTION_TITLE}}` (canonical heading, e.g. `## Core features`),
   `{{EMPHASIS_SECTION_BODY}}` (current text of that one section, read by
   main from the live doc). 4-doc 전체 placeholder substitute 금지 — sub-agent
   가 자기 doc 만 보면 충분 (B-6 iter1 redraft cost 109k tokens 의 주요 원인).
   The emphasis header embeds the iteration scope discipline rule verbatim
   — do not paraphrase:

   > Scope discipline: PRD `## Core features` is the authoritative scope.
   > Do not introduce new features, modules, components, screens, or
   > token sets that have no counterpart in the existing PRD `## Core
   > features`. Items the ADR has explicitly deferred
   > (`> **Future ADRs**`) MUST NOT be pre-emptively decided. Existing
   > sections that are not the explicit target of the iteration emphasis
   > MUST be returned verbatim — do not reword Reasoning/Tradeoffs/
   > Rejected-alternatives blocks. Pre-existing identifiers (variable,
   > token, module, component names) MUST NOT be renamed unless the
   > rename IS the requested change.

3. **4-way parallel dispatch** (single message, 4 Agent calls):
   `prd_step2.md`+`prd_step3.md` (combined PRD pair = 1 of 4),
   `arch_step8.md`, `adr_step11.md`, `ui_step13.md`, each prepended with
   the substituted emphasis header. `docs/research/2026-04-29-platform-limit.md`
   confirms 4-way + 5-way works. Sequential fallback only on documented
   input dependency or detected retry-after.

4. **Each sub-agent overwrites its doc** via `write_run_artifact` and
   returns `WROTE: <path>`. Step 11's overwrite is from-scratch, so the
   prior `## Cross-doc review` section vanishes naturally.

5. **Re-run Step 9** with `{{ITERATION_COUNT}}` incremented. Sub-agent
   appends the iteration-suffixed heading. Step 4 is skipped on the
   iteration yes-path — Step 9 provides coverage.

UI_GUIDE.md is always re-run alongside PRD, ARCH, ADR — produced as a
quadruple, must stay consistent.

## Multi-iteration loop with stop conditions

Phase B-5 replaced the 1-iteration cap with an explicit stop-condition loop
(B-2/B-3/B-4 each showed iteration resolving findings but introducing NEW
ones at the cap).

**Stop condition (verbatim — do not paraphrase in implementations):**

> The orchestrator continues iterating while either condition holds:
> (a) Step 9 review reports `NEW ≥ 1` for the just-completed iteration,
> OR (b) the most recent two iterations have not both satisfied
> `RESOLVED ≥ 80% AND NEW ≤ 0`. Iteration stops when two consecutive
> iterations both satisfy `RESOLVED ≥ 80% AND NEW ≤ 0`, or when the
> iteration counter reaches 7, whichever comes first.

**Iteration state tracking (verbatim):**

> The orchestrator maintains a per-run state file at
> `runs/<rid>/iteration_state.json` with shape
> `{"iterations": [{"index": N, "resolved_pct": F, "new_count": N,
> "stopped": bool, "reason": "..."}, ...]}`. The file is updated after
> each Step 9 cross-doc review. Termination reason is one of
> `stop-condition-met`, `cap-reached`, `user-requested-stop`.

After each Step 9 review the main Claude parses the
`COUNTS: resolved=N unresolved=N new=N` second-stdout line, computes
`resolved_pct = resolved / (resolved + unresolved + new)`, calls
`update_iteration_state(rid, {...})` (server function, see Step 9), and
decides whether to continue. The function appends to `iterations[]` with
auto-assigned `index`.

### User exit override

After every iteration (including iterations 1 and 2 before the stop
condition can have fired), ask via `AskUserQuestion`:

> "반복을 계속할까?"
> options: ["yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증 한 라운드 더", "no — 여기서 종료"]

"no" terminates the loop and records `reason: "user-requested-stop"`. The
user is never forced through additional iterations (V4 identity rule).

### Iteration cap exceeded

If the iteration counter reaches 7 without the stop condition firing and
without a user no-answer, emit a one-line warning to the user citing the
cap and the unresolved count (e.g. "iteration cap (7) reached with 2
unresolved findings; exiting"), record `reason: "cap-reached"`, and stop.

## Sources

- V4 Spike I spec: `docs/specs/2026-04-30-v4-spike-i-design.md` (commit `eeb6c96`) — §3.4 anti-fallback verbatim, §4.3 Step body templates
- Phase B-5 loop: `docs/dogfood/phase-b-5.md` (run `20260429-135600-3b6d`)
- Harness preamble v2: `bundled/_shared/harness-preamble.md` (rules 5/6, commit `6598788`)
- Prompts: `bundled/plan-pack/prompts/{prd_step2,prd_step3,prd_step4,arch_step8,adr_step11,ui_step13,cross_doc_step9,iter_emphasis}.md`
