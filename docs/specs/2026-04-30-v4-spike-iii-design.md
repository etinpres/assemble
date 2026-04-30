# V4 Spike III — design spec

> **Source**: B-7 dogfood (run `20260430-151140-4945`, 2026-04-30) + Spike I final review carryforward (`docs/dogfood/spike-i-readiness.md` lines 44–55).
>
> **Parent**: `~/.claude/skills/assemble/docs/specs/2026-04-30-v4-spike-ii-design.md` (Spike II, `1c3c0a1`).
>
> **Baseline (Spike III start)**: master `23fa6c6`, pytest 220/220, canonical preamble v3 sha256 `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`, ALLOW_LIST = {v1, v2, v3}.
>
> **Identity protection**: Spike III adds *only*. Do not modify Spike I sub-agent path-only contract, Spike II 8-file allowlist / hook v1 / `update_iteration_state`, V3 concierge menu (J-1~4 — Spike V), or other ★ candidate bundles (Spike IV).

---

## 1. B-7 surface (4 carryforward)

### 1.1 N1 (Critical) — `PRD.md.template` ↔ `prd_step2.md` schema mismatch

**Root cause**:

- `bundled/plan-pack/templates/PRD.md.template` declares 8 placeholders: `{{TASK}}`, `{{GOAL}}`, `{{USERS}}`, `{{CORE_FEATURES}}`, `{{MVP_EXCLUDED}}`, `{{AC_BASH}}`, `{{DESIGN_DIRECTION}}`, `{{RISKS}}`.
- `bundled/plan-pack/prompts/prd_step2.md:53` only replaces `{{TASK}}` and `{{PRD_BODY}}`, but `{{PRD_BODY}}` is **not** in the template. Result: 6 placeholders ship to `PRD.md` raw (`{{GOAL}}`, `{{USERS}}`, etc.).
- Sibling step prompts are correct: `arch_step8.md` (6 sections + TASK = 7 replace), `ui_step13.md` (TASK + DESIGN_DIRECTION + UI_BODY = 3 replace), `adr_step11.md` (TASK + DECISIONS_BLOCK = 2 replace). Only `prd_step2.md` is broken.

**Symptom (B-7 transcript)**: After Step 2, `PRD.md` showed `{{GOAL}}`, `{{USERS}}`, `{{CORE_FEATURES}}`, `{{MVP_EXCLUDED}}`, `{{DESIGN_DIRECTION}}`, `{{RISKS}}` literally. Main Claude reacted by *informally* dispatching a "PRD fix" sub-agent to fill the placeholders → that sub-agent ran outside the 8-file allowlist → §CRITICAL rule 7 (no infrastructure read) was not in its prompt → **F12 regression** (sub-agent grep+read on `server/run_dir.py` + `hooks/guard_run_dir.sh`).

**Fix decision (Spike III memory option B)**: prd_step2 emits 6 section variables and replaces 7 placeholders (TASK + 6 sections), with `{{AC_BASH}}` substituted to a sentinel `{{AC_BASH_PLACEHOLDER}}` that Step 3 fills. This mirrors `arch_step8.md`.

**Companion change (not in memory, surfaced during this spec)**: `prd_step3.md` currently wraps the AC bash command in its own ` ```bash ... ``` ` fence before substituting `{{AC_BASH_PLACEHOLDER}}`. After N1 fix, `PRD.md.template` already provides the fence around `{{AC_BASH}}`, so Step 3 must substitute the **raw** command — otherwise the rendered PRD has nested fences (` ```bash\n```bash\n<cmd>\n```\n``` `). Fix `prd_step3.md` to emit raw bash and Step 2 to substitute `{{AC_BASH}}` → `{{AC_BASH_PLACEHOLDER}}`.

**Acceptance**:

- (A1) New `tests/unit/test_prd_template_placeholder_match.py`: scan `PRD.md.template` for every `{{...}}` token, verify each appears as a `.replace("{{...}}", ...)` literal in either `prd_step2.md` or `prd_step3.md`.
- (A2) End-to-end test: render `PRD.md` with stubbed sub-agent outputs, assert no `{{` substring remains and the AC fence is **not** doubled.

### 1.2 F12 regression (Critical) — informal sub-agent dispatch bypasses §CRITICAL

**Root cause**: §CRITICAL rule 7 ("다른 스킬 인프라 코드 read·grep 금지") is enforced via the harness preamble that `wrap_with_preamble` prepends. Main can construct a dispatch prompt that *skips* `wrap_with_preamble` (e.g. a quick "fix this" hand-rolled Agent call), in which case the sub-agent never sees rule 7.

**Two-layer fix (memory option A+B)**:

- **B1 (allowlist enforcement)**: `record_dispatch` rejects `subagent_type` arguments outside the 8-prompt allowlist via `ValueError` *unless* an explicit override flag is passed. The `subagent_type` kwarg today carries the Agent tool's `general-purpose` constant (per SKILL.md line 132), so we reuse a *new* kwarg `prompt_file: str` (e.g. `"prd_step2.md"`) and check that against `ALLOWED_PROMPT_FILES = {"prd_step2.md", "prd_step3.md", "prd_step4.md", "arch_step8.md", "adr_step11.md", "ui_step13.md", "cross_doc_step9.md", "iter_emphasis.md"}`. Existing callers must be updated to pass `prompt_file=...`. ValueError message points to SKILL.md §CRITICAL.
- **B2 (forced prefix on every dispatch)**: `wrap_with_preamble` already prepends the harness preamble; that preamble already carries rule 7 in v3. The remaining gap is dispatches that *don't* go through `wrap_with_preamble`. Add a wrapper `dispatch_prompt(prompt_file: str) -> str` in `server.harness` that (a) validates `prompt_file` against the allowlist, (b) loads the file from `bundled/plan-pack/prompts/<prompt_file>` (resolver checks `subagent/` + `orchestrator/` then flat path), (c) returns `wrap_with_preamble(text)`. Placeholder substitution stays the caller's responsibility — the orchestrator already knows which `{{KEY}}` tokens belong to its Inputs section vs. the sub-agent's own `.replace("{{KEY}}", var)` instructions inside the canonical save block. A naive global `.replace` would corrupt the latter (B1 review C1 — option B chosen). SKILL.md Step dispatch contract is updated to recommend `dispatch_prompt`. The function lives next to `record_dispatch` so any caller using the public `server` import surface naturally pairs them.

**Acceptance**:

- (B1.1) `tests/unit/test_harness_dispatches.py` — new tests: `record_dispatch(prompt_file="evil.md", ...)` raises `ValueError` containing the SKILL.md §CRITICAL reference. Existing tests updated to pass `prompt_file="prd_step2.md"` etc.
- (B1.2) Backward compat: omitting `prompt_file` falls back to a soft warning printed to stderr, **not** an error (so Spike I/II callers don't crash mid-spike); add a `record_dispatch_strict()` overload (or env flag `ASSEMBLE_DISPATCH_STRICT=1`) for the strict mode used in tests.
- (B2.1) `server.dispatch_prompt("prd_step2.md")` returns the wrapped prompt with the harness preamble prepended and all `{{KEY}}` tokens preserved verbatim (caller-side substitution).
- (B2.2) Test that an unknown `prompt_file` raises `ValueError`.

**Caller-side under-substitution gap (option B trade-off)**: Because `dispatch_prompt` no longer substitutes placeholders, an orchestrator could load a prompt and forget to `.replace("{{KEY}}", ...)` for one of the tokens declared in the file's Inputs section. The leaked `{{KEY}}` would reach the sub-agent at dispatch time. We accept this gap at the unit level — the integration-time catch is `(13)` (B-8 dogfood: rendered artifacts under `runs/<rid>/` have zero `{{...}}` literals). Adding a unit guard that scans each prompt's Inputs section against the SKILL.md Step dispatch example would re-introduce coupling between the safety net and Spike-I sub-agent contract, which violates the §"Identity protection" rule. Phase A1's `test_prd_template_placeholder_match.py` already covers prompt-file ↔ template alignment, which is the larger-blast-radius case.

### 1.3 F3 (Important) — Korean phrasing drift in sub-agent output

**Decision**: **accept** (Spike III memory option C). 9 known terms ("도구파 경량", "리시완 DB", "미니멀 평수", etc.) are sub-agent inference artifacts, not template bugs. Adding more prompt examples (Spike II already tried) hits diminishing returns; a post-hoc Korean lint hook is high-cost low-ROI for a 1-person dogfood. Document the decision in `docs/dogfood/spike-iii-readiness.md` after Phase E.

**No code changes** for F3.

### 1.4 M1 (cosmetic) — V3 concierge "(Recommended)"

Out of Spike III scope. V3 concierge layer (Spike V).

---

## 2. Spike I final review carryforward (6, Spike II uncovered)

Source: `docs/dogfood/spike-i-readiness.md` lines 44–55.

### 2.1 C1 — Bare `...` Ellipsis literals in prompt body templates

**Risk**: Sub-agent fills the body but forgets one `...` sentinel; the literal ships to `PRD.md`/`ARCHITECTURE.md`/`ADR.md`/`UI_GUIDE.md` and looks intentional.

**Locations** (grepped 2026-04-30):

- `prd_step2.md:36-46` — Step 2 body section sentinels (Goal/Users/.../Risks).
- `prd_step4.md:36-38` — Review notes bullet sentinels.
- `arch_step8.md:32-37` — 6 ARCH section sentinels.
- `adr_step11.md:53-63` — Decision body sentinels.
- `ui_step13.md:65-73` — UI body 5-section sentinels.

**Fix**: Replace bare `...` with explicit `<TBD: 1-line description of expected content>` sentinels. Add a guard test that scans rendered artifacts for `"\n...\n"` and `<TBD:` substrings — fail if either remains in the final write.

**Acceptance**:

- (C1.1) Each prompt file uses `<TBD: ...>` form.
- (C1.2) New test: scan all canonical save blocks (the `body = """..."""` strings) for bare `...` lines — fail if found.
- (C1.3) Document in SKILL.md §"Step dispatch contract" that sub-agents must replace every `<TBD: ...>` before printing `WROTE:`.

### 2.2 C2 — "Return only file path" wording vs `print(f"WROTE: {path}")` mechanism

**Risk**: First sentence of every sub-agent prompt says "Return only the file path" / "Return file path", but the actual contract is `print(f"WROTE: {path}")` which the orchestrator parses with regex `^WROTE: (.+)$`. Mismatched wording invites sub-agents to print bare paths.

**Fix**: Standardize first-sentence wording to "Print `WROTE: <absolute path>` on stdout — main parses with regex `^WROTE: (.+)$`. No other prose."

**Files**: All 7 sub-agent prompts (`prd_step2.md`, `prd_step3.md`, `prd_step4.md`, `arch_step8.md`, `adr_step11.md`, `ui_step13.md`, `cross_doc_step9.md`).

**Acceptance**:

- (C2.1) Each prompt file's first paragraph contains the exact phrase "Print `WROTE: <absolute path>`".
- (C2.2) Test: `tests/unit/test_prompts_print_contract.py` greps each file for the canonical phrase; missing → fail.

### 2.3 C3 — `iter_emphasis.md` mixed-language tokens

**Locations** (SKILL.md, not prompt itself):

- SKILL.md:273 entry option: `"yes — 강조점 인터뷰 + 4-doc 재작성 + cross-doc 재검증"`.
- SKILL.md:369 exit option: same.
- `iter_emphasis.md` body: line 4 (`{{DOC_NAME}}` parameter), Step 6 detail uses `4-doc redraft`.

**Fix**: SKILL.md and `iter_emphasis.md` Korean-facing strings replace `4-doc` → `네 문서`, `cross-doc` → `문서 간`. Code-facing identifiers (`{{DOC_NAME}}`, `4-way parallel dispatch` in step descriptions, `cross_doc_step9`) stay as-is — those are file/variable names, not user-facing labels.

**Acceptance**:

- (C3.1) Step 6 entry + exit option strings use 한국어 only.
- (C3.2) Test: regex scan of SKILL.md `AskUserQuestion` option blocks for `\b(4-doc|cross-doc)\b` → fail.

### 2.4 C4 — Step 6 entry vs § User exit override asymmetry

**Risk**: SKILL.md:268 ("After the FIRST Step 9 cross-doc review only") and SKILL.md:363 ("After every iteration") describe two different prompts firing on different conditions. The selector is implicit (`iteration_count == 0` vs `≥ 1`). A future contributor could read either block and mis-fire.

**Fix**: Add an explicit selector block at the top of "Step 6 — iteration round-trip" that names both prompts and the boolean condition that picks each. Example:

```markdown
### Step 6 prompt selector

| iteration_count | prompt | options |
|---|---|---|
| 0 | "네 문서 작성 완료 — ... 한 차례 반복 진행할까?" | yes — 강조점 인터뷰 + 네 문서 재작성 + 문서 간 재검증 / no — 종료 |
| ≥1 | "반복을 계속할까?" | yes — 한 라운드 더 / no — 여기서 종료 |

The two prompts never both fire on the same iteration boundary.
```

**Acceptance**:

- (C4.1) SKILL.md "Step 6 — iteration round-trip" begins with the selector table.
- (C4.2) Existing entry + exit blocks reference the selector ("Per the prompt selector above ...") rather than redeclaring the condition prose.

### 2.5 C5 — `ui_step13.md` antipattern keyword false-positive

**Risk**: `ui_step13.md:34` lists `gradient-text`, `glass morphism`, `backdrop-blur`, `all-purple` as forbidden. A legitimate paint/photo app could need real `gradient` vocabulary; a brand-purple app legitimately uses purple. Hard ban → false positive.

**Fix**: Reframe as "antipattern *signals*, not an exclusion list":

- Keep the keyword list, but reword the sentence: "DO NOT emit *as design directives* the following antipattern keywords unless the PRD `## Core features` explicitly requires them: `gradient-text` (UI text gradients as decoration), `glass morphism` (backdrop-blur with translucent panels), `all-purple` (single-hue palette without rationale), emoji-as-decoration, "Lorem ipsum", "TODO/FIXME", marketing adjectives like "innovative" / "seamless"."
- Add: "If the PRD explicitly requires gradients (e.g. paint app, photo editor), the keyword may appear — annotate with `(domain-required by PRD § Core features)`."

**Files**: `ui_step13.md`, plus `templates/UI_GUIDE.md.template` if it carries the same list.

**Acceptance**:

- (C5.1) `ui_step13.md` carries the reframed sentence.
- (C5.2) Test: render UI_GUIDE.md with a stub paint-app PRD that mentions gradients; assert sub-agent prompt allows the keyword conditionally.

### 2.6 C6 — `prompts/` subdirectory split

**Risk**: `prompts/iter_emphasis.md` is **orchestrator-facing** (main constructs the prompt and substitutes per-doc placeholders before dispatching to 4 sub-agents). The other 7 prompts are **sub-agent-facing** (loaded once, substituted, dispatched). Mixing them invites confusion.

**Fix**: Split into:

- `bundled/plan-pack/prompts/subagent/<name>.md` (7 files: prd_step2/3/4, arch_step8, adr_step11, ui_step13, cross_doc_step9)
- `bundled/plan-pack/prompts/orchestrator/iter_emphasis.md` (1 file)

Update `dispatch_prompt(prompt_file=...)` allowlist resolution to look in both directories. Update SKILL.md Step references and the §"Anti-bypass" 8-file allowlist.

**Acceptance**:

- (C6.1) Files moved; old paths gone.
- (C6.2) `dispatch_prompt` resolves `"prd_step2.md"` to `subagent/prd_step2.md` and `"iter_emphasis.md"` to `orchestrator/iter_emphasis.md`.
- (C6.3) `record_dispatch(prompt_file=...)` allowlist updated to match.
- (C6.4) SKILL.md §CRITICAL "8-file allowlist" prose updated to reference the two subdirs.
- (C6.5) Existing tests still pass.

---

## 3. Acceptance criteria (Spike III as a whole)

| # | Criterion | Where verified |
|---|---|---|
| 1 | `PRD.md` rendered from a fresh dogfood run has zero `{{...}}` literal placeholders | A2 + B-8 |
| 2 | `PRD.md` AC bash block has exactly one ` ``` ` fence pair (no nested) | A2 + B-8 |
| 3 | Informal `record_dispatch(prompt_file="evil.md")` raises ValueError (strict mode) | B1.1 |
| 4 | `dispatch_prompt` rejects unknown prompt file with ValueError | B2.2 |
| 5 | `dispatch_prompt` for known file returns wrapped prompt with all `{{KEY}}` tokens preserved verbatim (caller-side substitution) | B2.1 |
| 6 | No bare `...` line in any prompt save-block template | C1.2 |
| 7 | Every sub-agent prompt's first paragraph carries "Print `WROTE: <absolute path>`" | C2.2 |
| 8 | SKILL.md `AskUserQuestion` Korean options contain no `4-doc` / `cross-doc` tokens | C3.2 |
| 9 | SKILL.md Step 6 begins with prompt-selector table | C4.1 |
| 10 | `ui_step13.md` antipattern list reframed as conditional signals | C5.1 |
| 11 | `prompts/` split into `subagent/` + `orchestrator/`; allowlist updated | C6.1–C6.4 |
| 12 | All 220+N tests pass after each Phase commit | pytest |
| 13 | B-8 dogfood: 0 informal sub-agent dispatch, 0 placeholder leak, 0 nested fence | dogfood transcript |

---

## 4. Out of scope

- F3 Korean phrasing lint hook (accepted, no fix).
- V3 concierge labels (M1, Spike V).
- Other ★ candidate bundles (Spike IV).
- Multi-harness compatibility (V5).
- Spike II revisit of any criterion (those PASS-state stays frozen unless a new regression appears in B-8).

---

## 5. Sources

- B-7 dogfood transcript: 형 직접 캡처 9 화면 (run `20260430-151140-4945`).
- Spike I final review: `docs/dogfood/spike-i-readiness.md` lines 44–55.
- Memory: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_iii.md`.
- Sibling spike specs: `docs/specs/2026-04-30-v4-spike-i-design.md`, `docs/specs/2026-04-30-v4-spike-ii-design.md`.
