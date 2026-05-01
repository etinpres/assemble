# V4 Spike V Design — builder ★ + M1/M2/M3 debugger polish

**Date**: 2026-05-01  
**Status**: approved  
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_iv.md`

---

## Scope

Two-phase spike:

- **Phase A** — debugger bundle prompt polish (M1/M2/M3 carryforward from Spike IV)
- **Phase B** — `builder` ★ bundle (execute stage, TDD-first + AC=bash)

Ship gate: B-10 dogfood, 13 AC PASS target.

---

## Phase A — M1/M2/M3 debugger polish

Three single-file prompt patches closing Spike IV carryforwards. Each is its own commit.

### A1 — M1: Dart heredoc anti-pattern (repro_step2.md)

**Problem**: B-9 dogfood, sub-agent wrote `dart - <<EOF` → exit 64 (heredoc stdin piping non-zero on Dart even on success).

**Fix**: Add to `## Anti-patterns` in `repro_step2.md`:

```
- Non-bash runtimes (dart, python, node) with heredoc syntax.
  Use `dart run <file>` or write a temp file instead of `dart - <<EOF`.
  Heredoc stdin piping exits non-zero on many runtimes even on success.
```

**Test**: assert the phrase `dart run` or `dart - <<EOF` appears in anti-patterns section.

### A2 — M2: behavioral verifier cue (fix_step5.md)

**Problem**: B-9 dogfood verify.sh used grep-based static check (absence of `toUtc`) rather than running the program. Partial AC=bash spirit.

**Fix**: Add to `## Constraints` in `fix_step5.md`:

```
- Prefer behavioral verifiers (run the program, check exit/output) over
  static checks (grep for absence of a string). Static checks are valid
  only when no runnable entry point exists.
```

**Test**: assert `behavioral` keyword present in fix_step5.md constraints section.

### A3 — M3: symptom sentinel substitution (repro_step2.md)

**Problem**: B-9 dogfood Step 2 sub-agent left `## Symptom` sentinel header intact in some renders. C7 5-section check caught it, but the sentinel itself passed.

**Fix**: In `repro_step2.md` save block, after `.replace("{{SYMPTOM_SUMMARY}}", symptom)` add:

```python
.replace("## Symptom\n<TBD: filled by Step 2 sub-agent — 1-line symptom summary>", f"## Symptom\n{symptom}")
```

**Test**: assert the explicit sentinel substitution pattern exists in the save block.

---

## Phase B — builder ★ bundle

### Goal

Execute-stage bundle enforcing a verifiable red→green TDD cycle. Primary deliverable: 4 artifacts under `runs/<rid>/`. Main Claude is orchestrator-only; sub-agents own all writes.

### Artifacts

| File | Written by | Content |
|---|---|---|
| `SCOPE.md` | Step 2 | allow-list of files/functions + deny-list + completion criterion |
| `test_first.sh` | Step 3 | exits non-zero before impl (red) |
| `verify.sh` | Step 5 | exits 0 after impl (green) |
| `IMPL_REPORT.md` | Steps 2→7 | skeleton (Step 2), red exit (Step 3), patch summary (Step 5), self-review (Step 6), commit message (Step 7) |

### Sub-agent allowlist (7 files)

`bundled/builder/prompts/subagent/` (6 files):
- `scope_step2.md`
- `test_step3.md`
- `impl_step4.md`
- `verify_step5.md`
- `review_step6.md`
- `report_step7.md`

`bundled/builder/prompts/orchestrator/` (1 file):
- `iter_revisit.md`

### Sub-agent role mapping

| Step | Role persona | Prompt file | Agent |
|---|---|---|---|
| 0 | run_dir resolve | — | (main) |
| 1 | task interview | — | (main, AskUserQuestion ×2) |
| 2 | SCOPE + task decomposition | `plan-implementation` | general-purpose |
| 3 | test_first.sh (red phase) | `general-purpose` | general-purpose |
| 4 | implementation (Edit/Write) | `general-purpose` | general-purpose |
| 5 | verify.sh + IMPL_REPORT draft | `general-purpose` | general-purpose |
| 6 | self-review (diff vs SCOPE) | `second-opinion` | general-purpose |
| 7 | commit message + IMPL_REPORT finish | `text-summarize` | general-purpose |
| 8 | iteration round-trip | orchestrator helper | `iter_revisit.md` |

### Workflow

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (loop back to 2 or 4)
```

Linear pipeline + 1 backtrack point at Step 8. Steps fire in numeric order.

### Step 1 — task interview (main)

**Q1** (single question):
> "구현할 작업을 한 줄로 요약해 줘. (예: 'POST /api/items 엔드포인트 추가', 'Flutter 홈 위젯 리팩토링')"

**Q2** (multi, 3 sub-questions):
- "변경 대상 파일·모듈을 알고 있으면 알려줘 (모르면 '모름')"
- "테스트 실행 커맨드가 있어? (예: pytest tests/, flutter test, bash smoke.sh — 없으면 '없음')"
- "완료 기준 (AC)을 bash 커맨드로 표현할 수 있어? (예: curl ... | grep -q ok — 없으면 '모름')"

Outputs: `TASK_SUMMARY`, `KNOWN_FILES`, `TEST_CMD`, `AC_CMD` → passed to Step 2 dispatch.

### Step 2 — SCOPE.md + task decomposition (sub-agent)

`prompt_file="scope_step2.md"`. Inputs: `RUN_ID`, `TASK_SUMMARY`, `KNOWN_FILES`, `TEST_CMD`, `AC_CMD`.

Sub-agent writes two artifacts:

**SCOPE.md**:
- `## Allow list` — files/functions permitted to change
- `## Deny list` — files/patterns explicitly off-limits
- `## Completion criterion` — one bash command or verifiable condition
- `## Task breakdown` — ordered sub-tasks (numbered, each ≤ 1 function/file scope)

**IMPL_REPORT.md skeleton** (from template, all body sections as `<TBD: filled by Step N>`):
front-matter + `## Task` (filled from TASK_SUMMARY) + 6 body section stubs.

### Step 3 — test_first.sh red phase (sub-agent)

`prompt_file="test_step3.md"`. Inputs: `RUN_ID`, `SCOPE_CONTENT` (SCOPE.md text).

Sub-agent writes `test_first.sh` (from template), runs it, confirms **non-zero exit** (the feature is not yet implemented). Records exit code in IMPL_REPORT.md `## Test (red)` section.

**Failure path**: if test_first.sh exits 0 (already passing), sub-agent prints
`ERROR: test already passes — feature may already be implemented`.
Main surfaces via AskUserQuestion: "테스트가 이미 통과해. test_first.sh를 수정할래, 아니면 task가 이미 완료된 건지 확인할래?"

### Step 4 — implementation (sub-agent)

`prompt_file="impl_step4.md"`. Inputs: `RUN_ID`, `SCOPE_CONTENT`, `EXISTING_REPORT`.

Sub-agent edits source files (Edit/Write) within SCOPE.md allow-list only. Any edit outside allow-list triggers:
`ERROR: scope creep — patch touches <file> not in allow-list`.

Does NOT run tests (Step 5 owns verification).

### Step 5 — verify.sh green phase + IMPL_REPORT draft (sub-agent)

`prompt_file="verify_step5.md"`. Inputs: `RUN_ID`, `EXISTING_REPORT`.

Sub-agent:
1. Writes `verify.sh` (behavioral: runs the program, checks exit/output — not static grep).
2. Runs `bash verify.sh` → confirms exit 0.
3. Appends `## Verify (green)` + patch summary to IMPL_REPORT.md.

**Failure path**: verify.sh exits non-zero → `ERROR: verifier failed after implementation`.
Main surfaces: AskUserQuestion "verify.sh가 실패했어. Step 4 재시도 / abort / report?"

### Step 6 — self-review diff vs SCOPE (sub-agent)

`prompt_file="review_step6.md"`. Inputs: `RUN_ID`, `SCOPE_CONTENT`, `EXISTING_REPORT`.

Sub-agent runs `git diff` (or equivalent), compares against SCOPE.md allow/deny lists, appends `## Self-review` section:
- scope deviation count (0 = clean)
- any harness rule 3 (Surgical Changes) violations
- recommendation: merge-ready / needs fix

### Step 7 — commit message + IMPL_REPORT finish (sub-agent)

`prompt_file="report_step7.md"`. Inputs: `RUN_ID`.

Sub-agent reads full IMPL_REPORT.md, validates no `<TBD: …>` remain in any section, adds `## Commit message` (conventional commit format) + flips `status: complete`.

If unfilled sections found: `ERROR: IMPL_REPORT has unfilled sections — <section name>`.
Main re-dispatches the gap-source step.

### Step 8 — iteration round-trip

After Step 7 success, AskUserQuestion:

> "verify.sh가 통과했어. 추가 작업이 남아 있어?"

Options:
- `"yes — 새 task로 Step 2부터 다시 (추천)"` → SCOPE.md 초기화, Step 2 재진입
- `"yes — 같은 SCOPE에서 구현만 다시"` → Step 4 재진입 (SCOPE.md 유지)
- `"no — 완료"` → workflow 종료

Iteration audit: `dispatch_and_record(..., step="step8.iter{N}.step2")` or `step8.iter{N}.step4`.

### TDD tier rules

| Situation | test_first.sh content |
|---|---|
| Unit test framework available | `pytest tests/test_foo.py` or equivalent — exits non-zero (test not yet written or failing) |
| No unit test but runnable entry point | AC=bash smoke: `curl .../endpoint \| grep -q ok` — exits non-zero |
| Neither available | SCOPE.md `## Completion criterion` + grep/stat check acceptable |

All tiers use the same shell contract. The distinction is documented in SCOPE.md `## Completion criterion`, not in SKILL.md branching logic.

### IMPL_REPORT.md sections

Front matter: `run_id`, `started`, `status: in_progress → complete`.

Sections (7):
1. `## Task` — 1-line summary (from Step 1)
2. `## Test (red)` — test_first.sh exit code (Step 3)
3. `## Implementation` — task breakdown + patch summary (Steps 4/5)
4. `## Verify (green)` — verify.sh exit code + output snippet (Step 5)
5. `## Self-review` — scope deviation count + recommendation (Step 6)
6. `## Commit message` — conventional commit format (Step 7)
7. `## TL;DR` — 2-line summary (Step 7)

---

## Test plan (+20 tests, 251 → ~271)

| Track | Tests | Count |
|---|---|---|
| Phase A | repro_step2 Dart anti-pattern, fix_step5 behavioral cue, repro_step2 symptom sentinel pattern | 3 |
| Phase B inventory | builder 7-file allowlist scan | 1 |
| Phase B templates | IMPL_REPORT/SCOPE/test_first/verify placeholder match | 4 |
| Phase B steps | scope_step2 WROTE, test_step3 exit-nonzero guard, verify_step5 exit-0 guard, review_step6 SCOPE-diff mention, report_step7 5-section check | 5 |
| Phase B contracts | 4-artifact invariant, 7-file allowlist in contracts.json | 2 |
| Phase B e2e | SKILL.md allowlist size = 7 | 1 |
| Phase B misc | iter_revisit shape, IMPL_REPORT front-matter | 2 |
| B-10 dogfood buffer | discovered during dogfood | 2 |

**contracts.json additions**:
- `builder_allowlist`: `{"scope_step2", "test_step3", "impl_step4", "verify_step5", "review_step6", "report_step7", "iter_revisit"}` (7 files)
- `builder_artifact_invariant`: on workflow complete, `SCOPE.md` + `test_first.sh` + `verify.sh` + `IMPL_REPORT.md` all exist

---

## B-10 dogfood task candidate

Add `list_runs()` to `server/run_dir.py` (returns sorted run_id list from `~/.claude/channels/assemble/runs/`) — small, self-contained, has a natural AC=bash (`ls ~/.claude/channels/assemble/runs/ | sort`), pytest-testable. Exercises full builder ★ pipeline with a real unit test.

---

## V4 identity protection

- ✅ Spike I~IV core contracts unchanged
- ✅ plan-pack ★ 4-doc workflow unchanged
- ✅ debugger ★ Steps 0~7 workflow unchanged (Phase A is prompt-text-only patch)
- ✅ canonical preamble v3 sha unchanged
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged
- ✅ V3 concierge menu layer unchanged

---

## Commit series pattern

```
fix(v4-spike-v-A1): repro_step2 Dart heredoc anti-pattern (M1)
fix(v4-spike-v-A2): fix_step5 behavioral verifier cue (M2)
fix(v4-spike-v-A3): repro_step2 symptom sentinel substitution (M3)
feat(v4-spike-v-B1): builder ★ bundle skeleton + inventory test
feat(v4-spike-v-B2): builder templates (IMPL_REPORT/SCOPE/test_first/verify)
feat(v4-spike-v-B3): builder Step 2 (SCOPE + task decomposition)
feat(v4-spike-v-B4): builder Step 3 (test_first.sh red phase)
feat(v4-spike-v-B5): builder Step 4 (implementation)
feat(v4-spike-v-B6): builder Step 5 (verify.sh green phase)
feat(v4-spike-v-B7): builder Step 6 (self-review diff vs SCOPE)
feat(v4-spike-v-B8): builder Step 7 + Step 8 + SKILL.md completion
docs(v4-spike-v): ship — B-10 dogfood 13/13 PASS, Spike VI carryforward
```

---

## Spike VI candidates (not in scope)

- `reviewer` ★ — diff vs SCOPE.md gate (SCOPE.md now available from builder)
- V3 concierge `(Recommended)` Korean drift cleanup (Spike VII)
- YAML strict-load frontmatter quote cleanup (deferred from Spike IV)
