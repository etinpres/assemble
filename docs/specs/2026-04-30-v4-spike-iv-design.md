# V4 Spike IV — design spec

> **Source**: B-8 dogfood (run `20260430-211523-212a`, 2026-04-30, md-sync project) + parent V4 spec § "★급 강화 후보 — debugger" (`project_assemble_v4_spec.md`).
>
> **Parent**: `~/.claude/skills/assemble/docs/specs/2026-04-30-v4-spike-iii-design.md` (Spike III, ship `1e608d4`).
>
> **Baseline (Spike IV start)**: master `1e608d4`, pytest **231/231**, canonical preamble v3 sha256 `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`, ALLOW_LIST = {v1, v2, v3}.
>
> **Identity protection**: Spike IV adds *only*. Do NOT modify Spike I sub-agent path-only contract, Spike II 8-file allowlist / `update_iteration_state`, Spike III `dispatch_prompt` + `record_dispatch(prompt_file=)` allowlist + `ASSEMBLE_DISPATCH_STRICT=1`, V3 concierge menu (J-1~4 — Spike VII), or other ★ candidate bundles beyond `debugger` (`builder` Spike V, `reviewer` Spike VI). plan-pack ★ keeps its 4-doc contract — the new debugger ★ bundle is parallel, not a refactor of plan-pack.

---

## 0. Spike IV scope (formé decision 2026-04-30)

**Q1 = (2)**: debugger ★ + iter1 audit-trail integrity carryforward (3 items).
**Q2 = (2a)**: debugger ★ uses the full plan-pack ★ pattern — `SKILL.md` + `prompts/orchestrator/` + `prompts/subagent/` + `templates/`. No thin-adapter shortcut over `superpowers:systematic-debugging`. Self-sufficiency is the V4 #1 decision; bundled debugger must work on a clean Mac.

Out of scope (other Spike candidates):
- `builder` ★ (Spike V) — TDD-enforcing execute-stage bundle.
- `reviewer` ★ (Spike VI) — diff-vs-SCOPE.md gate bundle.
- V3 concierge menu polish (Spike VII).

---

## 1. iter1 audit-trail integrity (3 carryforward from B-8)

Source: `docs/dogfood/spike-iii-final.md` §"Carryforward" A/B/C.

### 1.1 A (Important) — iter1 4-way dispatch missing from `dispatches.jsonl`

**Symptom**: `dispatches.jsonl` from B-8 run `20260430-211523-212a` has 8 rows (step2/3/4/8/11/13/9/9_iter1) but no rows for the four iter1 PRD/ARCH/ADR/UI sub-agent dispatches that fired via `iter_emphasis.md`. The transcript confirms `Running 4 agents...` actually ran, so the dispatch happened — only the audit-row write was skipped.

**Root cause**: `dispatch_prompt(prompt_file)` and `record_dispatch(prompt_file=, ...)` are two independent calls. Spike III SKILL.md Step 6 yes-path detail does not enumerate the per-doc `record_dispatch` line, so main is free to elide it without any test catching the omission. The 4-way iter1 dispatch is the only place in the workflow where one prompt file (`iter_emphasis.md`) gets dispatched four times in a single message, and the human-in-the-loop pattern of "build prompts, send single message with 4 Agent calls" naturally elides the audit step.

**Fix shape (memory option B + new audit guarantee)**:

- **A1.1** Add `dispatch_and_record(run_id, prompt_file, step, *, status="dispatched", note=None) -> str` to `server.harness`. Returns the wrapped prompt (same as `dispatch_prompt`) and writes one `dispatches.jsonl` row before returning. `step` is required (e.g. `"step6.iter1.PRD"`). `status` allows `"skipped"` for the §1.2 case.
- **A1.2** SKILL.md Step 6 yes-path detail rewrites the dispatch loop to use `dispatch_and_record` exclusively for iter1 — no bare `dispatch_prompt` + `record_dispatch` pair.
- **A1.3** New unit test `tests/unit/test_dispatch_and_record.py`: mock `record_dispatch` and `dispatch_prompt`, call `dispatch_and_record`, assert *both* are called exactly once, in order, with `prompt_file` propagated.

**Acceptance**:

- (A1) `server.dispatch_and_record(...)` exists, exported via `server/__init__.py`.
- (A2) `tests/unit/test_dispatch_and_record.py` passes (3+ assertions).
- (A3) Dogfood B-9: every dispatch in the iter1 path has a matching `dispatches.jsonl` row.

### 1.2 B (Minor) — iter1 `(no change)` doc mtime not updated

**Symptom**: B-8 iter1 transcript labels PRD/ARCH/UI_GUIDE as "no change pass-through · Done", but their `runs/<rid>/*.md` mtime did not advance — sub-agents elided the verbatim `write_run_artifact` call required by `iter_emphasis.md:29-32`. Bytes identical, but no audit anchor.

**Root cause**: Sub-agent autonomous cost optimization. `iter_emphasis.md` step 1 explicitly requires the verbatim write, but sub-agents reading "no change" naturally skip the IO. Runtime enforcement is impossible from the orchestrator side (sub-agent could fake the `WROTE:` line). The cleanest fix is **orchestrator-side dispatch skip**: if user enters `(no change)` for a doc emphasis in iter1, main does NOT dispatch — instead it records `dispatch_and_record(..., status="skipped", note="user emphasis: (no change)")`.

**Fix shape (spike-iii-final.md option b)**:

- **B1.1** SKILL.md Step 6 yes-path detail "If user emphasis for `<DOC>` is empty or literal `(no change)`, do NOT dispatch — call `dispatch_and_record(run_id, "iter_emphasis.md", step="step6.iter1.<DOC>", status="skipped", note="(no change)")`."
- **B1.2** `iter_emphasis.md` step 1 wording can be *softened* (no longer required to verbatim-write, since main never dispatches with `(no change)`). Replace "If `{{EMPHASIS}}` == `(no change)`: ..." with "Note: main never dispatches this prompt with `(no change)`; if you receive that string, ERROR back."
- **B1.3** New unit test `tests/unit/test_dispatch_and_record.py::test_skipped_status_writes_row` — `status="skipped"` writes a `dispatches.jsonl` row with the skip metadata.

**Acceptance**:

- (B1) SKILL.md Step 6 yes-path detail enumerates the `(no change)` skip path.
- (B2) `iter_emphasis.md` step 1 reflects the new contract.
- (B3) Dogfood B-9: any `(no change)` emphasis in iter1 produces a `status="skipped"` row, no doc-write attempt.

### 1.3 C (Important) — hook v1 Bash command prefix marker false-negative

**Symptom**: B-8 ADR iter1 sub-agent wrote ADR.md via Bash `bash -c "# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\ncat > ADR.md <<EOF ..."` (or similar). The magic marker appeared as a Bash-comment prefix, not as a Python comment inside `python3 -c`. hook v1 matched the substring and let the write through. The transcript phrasing "*test if guard passes*" reads as a deliberate probe — the sub-agent *intentionally* used the Bash-prefix path because it works.

**Root cause**: `hooks/guard_run_dir.sh:55-58` Bash-branch matcher tests for the substring `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` anywhere in the Bash command. The Spike I sub-agent path-only contract intended this marker to appear *only* in the canonical Python save block (`# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` as the first non-empty line of `python3 -c '<code>'` or `python3 << EOF`). A generic Bash-comment placement satisfies the substring check but bypasses the canonical save path.

**Fix shape (hook v2 — substring → context-aware)**:

The hook continues to receive the raw Bash command via stdin JSON. The matcher must:

1. Reject the marker when it appears as a **Bash comment prefix** of a non-Python invocation (`bash -c '# MARKER\n<bash code>'`, `sh -c '# MARKER...'`).
2. Accept the marker when it appears as the **first non-empty line of an inline `python3 -c '<code>'`** invocation, or as the **first non-empty line inside a `python3 <<EOF` heredoc**.
3. Accept the marker when it appears anywhere inside a `python3 -c '...'` body whose code has already imported `write_run_artifact` (the legitimate pattern).

The simplest correct check: extract the body of the `python3` invocation (between `python3 -c '` and `'` end, or between `python3 << EOF` and `EOF`) — match the marker only inside *that* extracted body. Bash commands that don't invoke `python3` cannot satisfy the marker check at all.

- **C1.1** Rewrite `hooks/guard_run_dir.sh` Bash branch: replace the substring grep with a Python helper invoked via stdin. The helper parses the command (`shlex` + simple state machine) and returns the marker-acceptance verdict. Pure-bash regex would be too brittle for heredoc + nested quoting.
- **C1.2** Helper file: `hooks/_guard_bash_matcher.py` (new). Importable from a unit test.
- **C1.3** New unit test `tests/contracts/test_guard_bash_matcher.py`:
  - Reproduce the B-8 carryforward C shape — `bash -c "# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\ncat > ADR.md <<EOF\n...EOF\n"` → reject.
  - Canonical save block — `python3 -c '# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\nimport sys; ...'` → accept.
  - Heredoc canonical — `python3 << EOF\n# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\nimport sys; ...\nEOF` → accept.
  - Mixed — `python3 -c '<no marker>'` → reject (no marker).
  - Edge: marker inside a string literal but not as comment — reject (treat only first non-empty source line as comment context).

**Acceptance**:

- (C1) `hooks/guard_run_dir.sh` Bash branch delegates to `hooks/_guard_bash_matcher.py`.
- (C2) `tests/contracts/test_guard_bash_matcher.py` passes 5+ test cases including the B-8 carryforward C reproducer.
- (C3) Dogfood B-9: no Bash-prefix-marker write succeeds; only python3 canonical save passes.

---

## 2. `debugger` ★ bundle (parent V4 spec § "★급 강화 후보 — debugger")

### 2.1 Goal

Replace LLM "guess fix" patterns with the systematic-debugging discipline: hypothesis → reproducer → bisect → root cause → fix + reverify. Self-contained: a clean Claude Code install with no `superpowers:systematic-debugging` skill must still get the full workflow via `bundled/debugger/`.

### 2.2 Artifacts (run dir layout)

`run_dir = ~/.claude/channels/assemble/runs/<rid>/`

Three artifacts:

- `BUG_REPORT.md` — primary deliverable. 5 sections: `## Symptom`, `## Reproducer`, `## Hypotheses`, `## Root cause`, `## Fix & verification`.
- `repro.sh` — executable reproducer command. The user can `bash repro.sh` and observe the bug.
- `verify.sh` — executable verification command. After fix, `bash verify.sh` exits 0; before fix, exits non-zero. (cross-cutting "AC = bash" pattern from V4 spec § "Cross-cutting 강화 흡수 후보".)

Both shell scripts have a header comment explaining what they do, followed by the command. They are **not** test code — they are minimal repro/verify shells the user runs interactively to confirm the bug and the fix.

### 2.3 Step layout (linear pipeline + 1 backtrack)

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 (iteration: re-enter at 3 if fix doesn't hold)
```

| Step | What | Sub-agent? | Prompt file | Role |
|---|---|---|---|---|
| 0 | resolve `run_dir` | no — main IO | — | — |
| 1 | symptom interview | no — main `AskUserQuestion` ×2 | — | — |
| 2 | reproducer construction | yes | `subagent/repro_step2.md` | `general-purpose` |
| 3 | hypotheses + bisect plan | yes | `subagent/hypothesis_step3.md` | `general-purpose` (Plan-mode persona) |
| 4 | root-cause analysis + second-opinion challenge | yes | `subagent/root_cause_step4.md` | `general-purpose` (second-opinion persona) |
| 5 | fix patch + verifier | yes | `subagent/fix_step5.md` | `general-purpose` |
| 6 | BUG_REPORT.md integration | yes | `subagent/report_step6.md` | `general-purpose` (text-summarize persona) |
| 7 | iteration: revisit at hypothesis or root-cause | orchestrator | `orchestrator/iter_revisit.md` | — |

Step 1 is the only main-side AskUserQuestion in the entire workflow (plan-pack has 5; debugger is leaner because the bug report scope is narrower).

### 2.4 Step 1 — symptom interview (main)

Two `AskUserQuestion` calls collected before any sub-agent dispatch:

- **Q1**: "버그 증상을 한 줄로 요약해 줘. (예: `npm run build` 가 `Error: Cannot find module 'fs/promises'` 로 실패)"
- **Q2** (multi-question, 3 sub-questions in one tool call):
  - 환경 (OS / 런타임 / 의존성 버전)
  - 마지막으로 작동했던 시점 / 커밋 (없으면 "모름" 옵션)
  - 이미 시도한 fix (없으면 "없음" 옵션)

Outputs `SYMPTOM`, `ENV`, `LAST_KNOWN_GOOD`, `TRIED_FIXES` — passed to Step 2 dispatch as Inputs.

### 2.5 Step 2 — reproducer (sub-agent)

Sub-agent receives `SYMPTOM` + `ENV` + `LAST_KNOWN_GOOD` + `TRIED_FIXES`. Builds `repro.sh` — minimal command that reproduces the symptom on a clean checkout. Writes `repro.sh` and the `## Reproducer` section of `BUG_REPORT.md`.

Constraint (harness rule 4): the reproducer **must fail when run** before the fix is applied. The sub-agent is told to run `bash repro.sh` itself and confirm the failure exit code in the `## Reproducer` section.

### 2.6 Step 3 — hypotheses + bisect plan (sub-agent)

Sub-agent reads `BUG_REPORT.md ## Symptom` + `## Reproducer`. Produces `## Hypotheses` section with **3-5 ranked hypotheses** (gate B3.2-style minSelected enforcement — see §2.10). Each hypothesis has:

- 1-line claim
- bisect step (specific file/line/commit to inspect)
- expected evidence if hypothesis is true

The sub-agent does **not** read infrastructure code outside the bug surface (harness rule 7).

### 2.7 Step 4 — root-cause analysis + second-opinion (sub-agent)

Sub-agent receives `## Hypotheses`. Picks the **most evidence-rich** hypothesis, drives bisect to confirm or reject. After confirming a single root cause, runs a **second-opinion challenge** (same sub-agent, prompt explicitly framed as "challenge this conclusion — what would refute it?"). Writes `## Root cause` section with:

- 1-sentence root cause
- bisect evidence trail
- challenge response: what refutation would look like + why it didn't materialize

If the second-opinion challenge surfaces a different root cause, returns to Step 3 (orchestrator detects "challenge winner != original" and re-routes).

### 2.8 Step 5 — fix patch + verifier (sub-agent)

Sub-agent receives `## Root cause`. Produces:

- `verify.sh` — command that exits 0 on success, non-zero on failure. The fix's acceptance criterion as bash.
- `## Fix & verification` section of `BUG_REPORT.md` — diff summary (file:line + 1-2 sentence rationale), verify.sh contents, expected output.
- The actual code patch as a save block at the end of the section, prefixed with the canonical `# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` marker (so the user can apply via `python3 -c '<save block>'` if the patch surface is one of the V4 plan-pack files; otherwise the user applies manually).

Constraint (harness rule 3 — Surgical Changes): the patch must touch only files named in `## Hypotheses` bisect steps OR `## Root cause` evidence trail. Sub-agent prompt enforces this in the canonical save block validator.

### 2.9 Step 6 — BUG_REPORT.md integration (sub-agent)

Sub-agent reads all five sections from earlier dispatches (which wrote separate `BUG_REPORT.md` writes — actually each prior step *appends* its section, see §2.11). Step 6's job is the **final read-back integration check**: ensure all five sections exist, in order, with no `<TBD: ...>` literals or bare `...` lines (Spike III §2.1 C1 carryforward). If gaps found, ERRORs back via `WROTE: ERROR: <reason>` so main can re-dispatch the gap-source step.

### 2.10 Step 7 — iteration (orchestrator)

After Step 6 success, main `AskUserQuestion`:

- "fix를 적용해 봤는데 verify.sh가 통과하지 못했거나, 동일 증상이 재발했나?"
  - "yes — 가설 단계로 돌아가서 다시" → re-enter Step 3 with carry-over context
  - "yes — 근본원인을 다시 분석" → re-enter Step 4
  - "no — 종료" → workflow done

Iteration uses `orchestrator/iter_revisit.md` to construct the re-entry prompt (carries `previous attempt failed: <reason>` + the existing `BUG_REPORT.md` so the sub-agent doesn't restart from zero).

### 2.11 Sub-agent write contract (per-step section append)

Each step 2-5 sub-agent appends *one* section to `BUG_REPORT.md`. The first dispatch (Step 2) creates the file from `templates/BUG_REPORT.md.template` and fills only `## Reproducer`. Step 3 reads, appends `## Hypotheses`. Step 4 reads, appends `## Root cause`. Step 5 reads, appends `## Fix & verification`. Step 6 reads the assembled file and validates.

This is the *append-section* pattern, vs plan-pack's *one-file-per-doc* pattern. Append-section is appropriate for debugger because the sections are causally chained — Step 3 needs `## Reproducer` text, Step 4 needs `## Hypotheses` text, etc.

Each sub-agent's canonical save block:

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
existing = read_run_artifact(rid, "BUG_REPORT.md")
new_section = """<this step's section, with proper heading>"""
combined = existing.rstrip() + "\n\n" + new_section + "\n"
path = write_run_artifact(rid, "BUG_REPORT.md", combined)
print(f"WROTE: {path}")
```

### 2.12 SKILL.md anti-bypass section (debugger-specific)

debugger SKILL.md inherits the plan-pack §"Anti-bypass" 8-file allowlist *concept*, but the file list differs:

```
bundled/debugger/prompts/subagent/: repro_step2.md, hypothesis_step3.md, root_cause_step4.md, fix_step5.md, report_step6.md (5 files)
bundled/debugger/prompts/orchestrator/: iter_revisit.md (1 file)
```

Total **6-file allowlist** (vs plan-pack's 8). The `ALLOWED_PROMPT_FILES` tuple in `server/harness.py` is shared across both bundles — it grows by 6 entries.

`dispatch_prompt` resolver path also extends — `bundled/debugger/prompts/{subagent,orchestrator}/` joins the lookup roots. The path resolution check searches plan-pack subdirs, then debugger subdirs, then flat fallback.

### 2.13 Templates

- `templates/BUG_REPORT.md.template` — 5 section headings + section-body sentinel `<TBD: filled by Step N>` per section. Plus front matter (run_id, started, status).
- `templates/repro.sh.template` — shebang + 1-line header comment + `<TBD: reproducer command>` body.
- `templates/verify.sh.template` — shebang + 1-line header comment + `<TBD: verifier command>` body.

### 2.14 Inventory + menu integration

`bundled/debugger/SKILL.md` carries the YAML frontmatter `name: debugger / description: Debug stage ★ bundle — systematic hypothesis → reproducer → bisect → root cause → fix workflow.` with `bundled: true` set by the inventory scanner (already implemented in Phase A — V4 결정 #3).

In the menu, debugger appears under the `debug` stage with `★ ` prefix. If the user has `superpowers:systematic-debugging` installed, both appear (bundled first per existing sort, V4 결정 #4-5).

### 2.15 Acceptance

- (D1) `bundled/debugger/` directory created with SKILL.md + `prompts/subagent/` (5 files) + `prompts/orchestrator/` (1 file) + `templates/` (3 files).
- (D2) `ALLOWED_PROMPT_FILES` extended by 6 (5 subagent + 1 orchestrator).
- (D3) `dispatch_prompt` resolver finds debugger prompt files under `bundled/debugger/prompts/{subagent,orchestrator}/`.
- (D4) `tests/unit/test_debugger_prompt_files_print_contract.py` — every debugger sub-agent prompt's first paragraph contains "Print `WROTE: <absolute path>`" (Spike III §2.2 C2 contract).
- (D5) `tests/unit/test_debugger_prompts_no_bare_ellipsis.py` — no bare `...` line in any debugger save-block body (Spike III §2.1 C1 contract).
- (D6) `tests/unit/test_debugger_template_placeholder_match.py` — every `{{...}}` in the 3 templates appears as a `.replace("{{...}}", ...)` literal in some debugger prompt file (Spike III §A1 contract).
- (D7) `tests/contracts/test_debugger_inventory.py` — inventory scanner returns the debugger entry with `bundled=True`.
- (D8) Dogfood B-9: complete debugger workflow produces a valid `BUG_REPORT.md` + `repro.sh` (fails before fix) + `verify.sh` (passes after fix).

---

## 3. Acceptance criteria (Spike IV as a whole)

| # | Criterion | Where verified |
|---|---|---|
| 1 | `dispatch_and_record` exists and is exported | A1 |
| 2 | `dispatch_and_record` calls `dispatch_prompt` + `record_dispatch` exactly once each | A2 (`test_dispatch_and_record.py`) |
| 3 | `record_dispatch` accepts `status="skipped"` field | B1.3 |
| 4 | SKILL.md Step 6 yes-path uses `dispatch_and_record` for iter1 | A1.2 (visible diff, not test-asserted) |
| 5 | SKILL.md Step 6 yes-path documents `(no change)` skip → `status="skipped"` row | B1.1 (visible diff) |
| 6 | `iter_emphasis.md` no longer requires verbatim write on `(no change)` | B1.2 (visible diff) |
| 7 | `hooks/guard_run_dir.sh` Bash branch delegates to `_guard_bash_matcher.py` | C1.1 |
| 8 | `_guard_bash_matcher.py` rejects Bash-comment-prefix marker; accepts python3 inline + heredoc canonical | C1.3 (5+ test cases) |
| 9 | `bundled/debugger/` with full plan-pack ★ pattern (SKILL.md + 6 prompts + 3 templates) | D1 |
| 10 | `ALLOWED_PROMPT_FILES` extended by 6 debugger entries | D2 |
| 11 | `dispatch_prompt` resolver finds debugger prompts | D3 |
| 12 | All debugger prompt files satisfy Spike III §C2 (WROTE wording) | D4 |
| 13 | All debugger save-block bodies satisfy Spike III §C1 (no bare `...`) | D5 |
| 14 | All debugger templates' `{{...}}` placeholders are replaced by some debugger prompt | D6 |
| 15 | Inventory scanner exposes debugger with `bundled=True` | D7 |
| 16 | pytest 231+N green after each Phase commit | pytest |
| 17 | B-9 dogfood: a real bug worked through debugger ★ end-to-end produces complete `BUG_REPORT.md` + executable `repro.sh` (fails) + `verify.sh` (passes after fix) | dogfood transcript |
| 18 | B-9 dogfood: any iter1 path on plan-pack uses `dispatch_and_record`; `(no change)` emphases produce `status="skipped"` rows; no Bash-prefix-marker writes succeed | dogfood transcript |

---

## 4. Out of scope

- `builder` ★ — Spike V.
- `reviewer` ★ — Spike VI.
- V3 concierge "(Recommended)" English label — Spike VII (M1 carryforward).
- F3 Korean phrasing lint hook — accepted Spike III decision, no fix.
- plan-pack ★ workflow changes beyond Step 6 yes-path detail wording (out of identity protection rule).
- Full `superpowers:systematic-debugging` parity — debugger ★ is *V4 self-sufficient*, not a port.
- Multi-harness compatibility (V5).

---

## 5. Phase decomposition (preview — full plan in `docs/plans/2026-05-03-v4-spike-iv.md`)

| Phase | Scope | Tasks |
|---|---|---|
| A | hook v2 (carryforward C) | 1 (helper + tests + hook delegation) |
| B | iter1 audit-trail integrity (carryforward A + B) | 2 (`dispatch_and_record` + SKILL.md Step 6 rewrite) |
| C | debugger ★ bundle | 7 (infra + templates + 5 sub-agent prompts + orchestrator + SKILL.md + inventory test) |
| D | B-9 dogfood readiness | 1 (CHANGELOG `[Unreleased]` entry + readiness memo skeleton) |

Total ≈ **11 tasks** + 1 dogfood. Spike III (9 tasks) sized comparable.

---

## 6. Sources

- B-8 dogfood transcript: `~/.claude/channels/assemble/runs/20260430-211523-212a/` + `docs/dogfood/spike-iii-final.md` § "Carryforward".
- Parent V4 spec: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md` § "★급 강화 후보 — debugger".
- Sibling spike specs: `docs/specs/2026-04-30-v4-spike-{i,ii,iii}-design.md`.
- Hook v1 source: `hooks/guard_run_dir.sh` lines 44-78 (Bash-branch substring matcher).
- harness baseline: `server/harness.py` `dispatch_prompt`, `record_dispatch`, `ALLOWED_PROMPT_FILES`, `wrap_with_preamble`.
