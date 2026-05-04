# V4 Spike VIII Design — verifier ★ bundle + F1 한글 backtick fix

**Date**: 2026-05-04
**Status**: approved
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_vii.md`

---

## Scope

Two-track spike landing the fourth self-sufficient ★ bundle (orthogonal — verify stage)
plus the long-deferred F1 carryforward from Spike VI.

- **Track A — verifier ★ bundle (orthogonal)** — first ★ bundle that *actually executes*
  the AC bash one-liner from `parsed_scope.json` and emits a deterministic verdict from
  the exit code. cross-cutting B (AC = bash 실제 실행) self-mechanized.
- **Track B — F1 한글 backtick mangling fix (cosmetic but parser-side regression risk)** —
  `parse_scope_step1.md` sub-agent emits malformed paths when SCOPE.md deny entries are
  Korean freeform prose with embedded backticks. Carryforward from Spike VI B-11 dogfood.

Ship gate: **B-13 dogfood** — fresh run_id, SCOPE.md exercises Korean+backtick deny entries
(F1 fix validation) + completion = `python3 -c "from server.run_dir import list_runs, run_dir_path; assert callable(list_runs); print('OK')"`. verifier ★ 4 dispatches, intentional-fail companion run with `exit 1` completion. 12 AC PASS target.

### Out of scope

- ❌ shipper ★ bundle — Spike IX candidate
- ❌ F4 perf collapse (Step 1/2/3/5/6 deterministic shell) — separate spike
- ❌ naming convention `<bundle>_<step>.md` prefix migration — case-by-case
- ❌ cross-cutting C trace self-audit + learning recall (keeper ★) — separate spike
- ❌ subagent-driven-development skill internal hardening (Spike VII follow-up surfaces)
- ❌ Codex CLI / Gemini CLI compat — V4 비범위

---

## Track B — F1 한글 backtick fix (executed FIRST)

### Problem (B-11 dogfood evidence)

`parse_scope_step1.md` instructs sub-agent: "split each bullet on the FIRST ` — `
(em-dash with surrounding spaces). Path is everything before; note is everything after."

Allow-list bullets in B-11 were single-backtick-wrapped paths
(`` - `server/run_dir.py` — F1 fix ``) which round-tripped fine. Deny-list bullets were
**Korean freeform prose with multiple embedded backticks**:

```
- `server/` 내 `run_dir.py` 외 모든 파일 (`__init__.py`, `harness.py`, ...) — 변경 금지
```

The naive parser captured the entire prose as `path` (correctly per the FIRST em-dash rule),
then a downstream "strip outer backticks" pass found that `path` started with `` ` `` but
did NOT end with `` ` `` (it ended with `)`), so backticks dangled in the rendered
REVIEW_REPORT.

The carryforward report recommended: "tighten parse_scope_step1 spec — either require a
stricter deny grammar (single backtick-wrapped path token), or document the freeform
fallback explicitly." Spike VIII picks **option 1** (strict grammar) — option 2 has no
deterministic answer for freeform prose.

### Reproduction (verified 2026-05-04)

`/tmp/spike-viii/repro_f1.py` reproduces the mangle exactly:
- P1 strict-per-spec stores deny path = freeform Korean prose verbatim → semantically wrong path token but no backtick dangle
- P2 naive-with-strip_outer_backticks (B-11 sub-agent emitted) → same wrong path with
  trailing backtick dangle (path ends with `)` so strip skips, leaves leading `` ` ``
  dangling)

### Design

**1. New helper `server/scope_parser.py` — `parse_scope_md(text: str) -> dict`**

Deterministic Python parser. Strict grammar enforcement:

```python
# Accepted bullet grammars (in priority order):
#   1. backtick-wrapped:  - `<path-token>` — <note>
#   2. plain-path:        - <path-token> — <note>
#   3. note-less:         - `<path-token>`           or  - <path-token>
# Anything else → entry-level error in `errors` list, entry skipped.
#
# `<path-token>` rules:
#   - no whitespace inside (rejects freeform prose with spaces)
#   - no backticks inside (rejects nested-backtick prose)
#   - any character otherwise (globs, dots, slashes preserved verbatim)
#   - outer backticks (form 1) stripped; inner content preserved verbatim
#   - plain-path form may contain dots/slashes/globs/dashes but no spaces
#     and no backticks
#
# `<note>` is everything after the FIRST ` — ` (em-dash with surrounding
# single spaces). Trimmed of leading/trailing whitespace. May be empty.
```

API:

```python
def parse_scope_md(text: str) -> dict:
    """Parse SCOPE.md text into the JSON shape consumed by reviewer Step 3 +
    verifier Step 1.

    Returns:
        {
          "task_summary": str,      # H1 line stripped of '# SCOPE — ' prefix
          "allow": [{"path": str, "note": str}, ...],
          "deny":  [{"path": str, "note": str}, ...],
          "completion": str,         # bash one-liner from fenced block
          "errors": [str, ...]       # section-level + entry-level errors
        }

    Errors surface as labelled strings:
      - "scope-missing"                — text empty
      - "allow-section-missing"
      - "completion-empty"
      - "deny-entry-N-grammar"        — entry index N violates strict grammar
      - "allow-entry-N-grammar"       — entry index N violates strict grammar
    """
```

**2. `parse_scope_step1.md` update**

Sub-agent shells out to the helper instead of writing inline parser code:

```python
import json, sys
from pathlib import Path
from server.scope_parser import parse_scope_md

text = Path("{{RUN_DIR}}/SCOPE.md").read_text(encoding="utf-8")
result = parse_scope_md(text)
out_path = Path("{{RUN_DIR}}/parsed_scope.json")
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                    encoding="utf-8")
print(f"WROTE: {out_path}")
```

Plus a "SCOPE.md grammar" doc paragraph for human authors describing the three
accepted bullet forms and the failure mode for freeform prose.

### Why a deterministic helper instead of tightening prompt prose

Spike VII E1 already established the precedent (`extract_wrote_paths` helper).
Pure prompt-rule tightening leaves room for LLM drift across sessions. A shared
helper is also unit-testable with fixtures — F1 regression cannot recur without
breaking a test.

The helper does NOT violate orchestrator-only (V4 #9): the **sub-agent** still
performs the read + parse + write. The helper is a shared library import, the same
way reviewer prompts already import `server.run_dir.write_run_artifact`.

### Acceptance — Track B

- B.1 `parse_scope_md` round-trips ASCII allow + Korean deny when both follow strict
  grammar (single-backtick path token + em-dash + note)
- B.2 freeform Korean prose deny entry emits `deny-entry-N-grammar` error, entry
  skipped (not stored as malformed path)
- B.3 missing `## Allow list` → `allow-section-missing`
- B.4 empty completion fence → `completion-empty`
- B.5 em-dash variants (`–` en-dash, `--` double-hyphen) all rejected — only canonical
  `—` U+2014 with single-space padding accepted
- B.6 `parse_scope_step1.md` calls the helper (no inline parser logic) — verified by
  regex grep of the prompt body
- B.7 reviewer B-11 input fixture (Spike VI) parses identically under the helper
  versus the prompt's previous behaviour for Allow entries (no regression)
- B.8 unit tests in `tests/unit/test_scope_parser.py` cover all 8 cases above

---

## Track A — verifier ★ bundle

### Bundle anatomy

```
~/.claude/skills/assemble/bundled/verifier/
├── SKILL.md                           # 4-step orchestrator workflow
├── prompts/
│   ├── subagent/
│   │   ├── verifier_extract_step1.md  # parsed_scope.json → completion bash
│   │   ├── verifier_execute_step2.md  # run bash, capture exit/stdout/stderr
│   │   ├── verifier_classify_step3.md # exit → verdict
│   │   └── verifier_report_step4.md   # write VERIFY_REPORT.md
│   └── orchestrator/
│       └── verifier_iter_revisit.md   # iteration helper (re-run Steps 2~4)
└── templates/
    └── VERIFY_REPORT.md.template      # 7-section shell
```

### Inputs

- `run_id` — resolves run_dir via `server.run_dir.run_dir_path(run_id)`
- `<run_dir>/parsed_scope.json` — must exist (reviewer ★ Step 1 or builder ★ Step 2
  output, or hand-authored after running scope_parser)
- (No `<base>..<tip>` git range — verifier is purely a completion-criterion runner)

### Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. One primary artifact:

- `VERIFY_REPORT.md` — 7 canonical sections (Summary with verdict line, Completion
  command, Execution result, Stdout sample, Stderr sample, Verdict reasoning,
  Recommendations).

Plus 3 intermediate JSONs for audit trail: `extracted_completion.json`,
`execution_result.json`, `verify_result.json`.

### Verdict logic (deterministic)

```python
verdict = "pass" if execution_result.exit_code == 0 else "fail"

reason = {
    "pass":   "completion command exited 0",
    "fail-exit-nonzero":     f"exited {exit_code}",
    "fail-timeout":          "timed out (30s budget)",
    "fail-output-truncated": "stdout/stderr exceeded 100KB cap",
}[outcome_label]
```

`outcome_label` is computed inside Step 3 sub-agent from `execution_result.json`
fields (`timed_out`, `truncated`, `exit_code`).

### Sub-agent matrix (4 step + 1 orchestrator helper)

| Step | Prompt file | Sub-agent type | Tools |
|---|---|---|---|
| 1 | `verifier_extract_step1.md` | `general-purpose` | Read, Write |
| 2 | `verifier_execute_step2.md` | `general-purpose` | Read, Write, **Bash** |
| 3 | `verifier_classify_step3.md` | `general-purpose` | Read, Write |
| 4 | `verifier_report_step4.md` | `general-purpose` | Read, Write |
| iter | `verifier_iter_revisit.md` | orchestrator helper | (none — main reads) |

Steps 1 and 2 are sequential (Step 2 reads Step 1's output). Steps 3 and 4 are
sequential (Step 4 reads Step 3's output). No parallel dispatch in the canonical
path. Orchestrator helper is loaded by main Claude only when iteration round-trip
requested.

### Iteration audit invariant

Every iteration produces exactly **4** rows in `dispatches.jsonl` with step names
`step1.iter{N}.extract`, `step2.iter{N}.execute`, `step3.iter{N}.classify`,
`step4.iter{N}.report`. Step 1 is skipped on subsequent iterations unless
`parsed_scope.json` changed; in that case the row count is 4, otherwise 3.

### Security model — completion command execution

verifier is the first ★ bundle that grants Bash tool access to a sub-agent. The
threat surface widens because `parsed_scope.json.completion` flows from SCOPE.md
authorship into shell execution.

**Threat model**:
- T1 (low): malicious SCOPE.md author injects `rm -rf ~/` in the completion field
- T2 (medium): runaway completion blocks pipeline indefinitely
- T3 (medium): completion emits 1GB stdout, exhausts memory or fills disk
- T4 (low): completion shells out to network resources, exfiltrates run_dir contents

**Mitigations** (defense in depth):

1. **Length cap** — `len(completion) ≤ 500` characters. Rejected at Step 1 with
   `extract-error: completion-too-long`. 500 chars is enough for legitimate
   one-liners (~3× the longest known fixture) and tight enough that obvious
   destructive payloads would need a fetch step that itself fails the cap.
2. **Timeout** — Step 2 wraps the bash call in `timeout 30s` (POSIX). Hard upper
   bound. Subprocess killed; `timed_out: true` recorded.
3. **Output cap** — Step 2 truncates stdout + stderr to 100KB each. Beyond that,
   `truncated: true` recorded; full output discarded.
4. **No shell metachar denylist** — explicit non-goal. Denylists are leaky and
   create false-security. The cap+timeout+author-trust model matches how `make`,
   CI runners, and `npm test` already operate. SCOPE author is the same human
   trusted to write the rest of the run dir.
5. **Bash scoped to Step 2 only** — Steps 1/3/4 sub-agents do not get Bash tool
   access in their dispatched prompts. ALLOWED_PROMPT_FILES gate enforces 4-file
   allowlist; harness preamble v3 still applied.
6. **Orchestrator-only main** — main Claude does NOT run the bash itself. Main
   only dispatches Step 2 sub-agent.

**Codex retro gate**: spec → Codex review (`codex:codex-rescue` second-opinion)
challenges threat model before A8 commit. If Codex flags additional vector
(e.g. `eval $(curl url)` style with cap-friendly URL), spec amended before
contracts.json freeze.

### contracts.json entries (3 new)

- `spike-viii-verifier-allowlist` — 4-file subagent allowlist contract
  (extract, execute, classify, report)
- `spike-viii-verifier-verdict-invariant` — `verdict = "pass" if exit_code == 0 else "fail"`
  deterministic rule (test asserts no LLM-judged verdict)
- `spike-viii-verifier-artifact-invariant` — VERIFY_REPORT.md 7-section invariant

### Acceptance — Track A

- A.1 verifier present in inventory scan with `bundled=True`, `stages=["verify"]`
- A.2 ALLOWED_PROMPT_FILES contains exactly 4 verifier subagent prompt files
- A.3 `dispatch_prompt("verifier", "verifier_X_stepN.md")` resolves correctly
  for all 4 steps; non-allowlisted file raises
- A.4 `wrap_with_preamble` v3 sha unchanged (matches Spike I `858e9ff1...e159`)
  on every verifier dispatch
- A.5 `substitute_inputs` auto-derives `RUN_DIR` from `RUN_ID` (Spike VII
  contract regression — verifier prompts use `{{RUN_DIR}}`)
- A.6 verdict invariant: 32 randomized exit codes via fixture → verdict
  deterministically `pass` ⟺ exit==0
- A.7 7-section invariant: VERIFY_REPORT.md template + render-time placeholders
  cover all 7 canonical headings
- A.8 SKILL.md frontmatter strict-load (Spike VI Phase A regression)
- A.9 reviewer/builder/debugger/plan-pack inventory entries unchanged
  (regression: bundle count goes from 4 → 5 ★ bundles, none renamed)
- A.10 pytest passes baseline +N (Track A test additions)

---

## B-13 dogfood — ship gate (12 AC)

run_id `<new>`, SCOPE.md authored fresh exercising Korean+backtick deny entries
(F1 fix validation) + reviewer/builder pattern allow entries.

```markdown
# SCOPE — Spike VIII verifier ★ B-13 dogfood

## Allow list

- `bundled/verifier/` — verifier ★ scaffold + 4 step prompts
- `server/scope_parser.py` — F1 fix deterministic helper

## Deny list

- `bundled/reviewer/` — Spike VI bundle, regression-protected
- `bundled/builder/` — Spike V bundle, regression-protected

## Completion criterion

​```bash
python3 -c "from server.run_dir import list_runs, run_dir_path; assert callable(list_runs); print('OK')"
​```
```

Plus an intentional-fail companion run with completion = `false` (or
`python3 -c "import sys; sys.exit(1)"`) to verify `verdict=fail`.

### Acceptance criteria

| # | AC |
|---|---|
| 1 | parse_scope_step1 (Track B fix) → parsed_scope.json correctly extracts Korean+backtick deny entries (no mangling, no error if grammar strict) |
| 2 | extract_step1 sub-agent reads parsed_scope.json, captures completion bash one-liner verbatim, writes extracted_completion.json |
| 3 | execute_step2 sub-agent runs bash, captures exit_code=0 + stdout="OK\n" + stderr="" + duration_ms |
| 4 | verify_result.json: `verdict="pass"`, `exit_code=0`, `reason="completion command exited 0"` |
| 5 | VERIFY_REPORT.md present with all 7 canonical sections; verdict line in Section 1 |
| 6 | dispatches.jsonl has 4 rows for iter1 (step1.iter1.extract, step2.iter1.execute, step3.iter1.classify, step4.iter1.report) |
| 7 | every dispatched prompt's preamble sha256 = canonical v3 `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159` |
| 8 | wall time real-dispatch ≤ 400s (4-step shorter than reviewer's 6) |
| 9 | RUN_DIR substitution: every prompt's resolved Inputs section contains absolute `~/.claude/channels/assemble/runs/<rid>` (no relative `runs/<rid>` survives) |
| 10 | orchestrator-only: main Claude does NOT call Bash directly during dispatch chain (verified by grep of session transcript) |
| 11 | F1 regression: parse_scope_step1 sub-agent on Korean+backtick deny entries yields zero `entry-grammar` errors when SCOPE author follows strict grammar |
| 12 | intentional-fail companion run (completion = `false`): verdict=`fail`, reason=`exited 1`, exit_code=1 |

12/12 PASS gates the ship CHANGELOG entry.

---

## V4 정체성 보호 (변경 X)

- ✅ Spike I~VII core contracts (verdict logic, 7 sections, 6-allowlist) — verifier
  adds 4-allowlist + its own verdict logic; reviewer's contracts untouched
- ✅ canonical preamble v3 sha unchanged (`858e9ff1...e159`)
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged (additive `parse_scope_md` helper only)
- ✅ V3 concierge menu layer unchanged
- ✅ existing ★ bundle prompts (plan-pack / debugger / builder / reviewer) unchanged
  — verifier is a NEW bundle, no rename, no migration
- ✅ `run_dir_path` / `substitute_inputs` / `extract_wrote_paths` API unchanged
- ✅ orchestrator-only V4 #9 — Bash permission is sub-agent (Step 2) only; main
  never executes shell during the dispatch chain
- ✅ `{{RUN_ID}}` + `{{RUN_DIR}}` token contracts unchanged
- ✅ `parse_scope_step1.md` contract change is **additive within prompt** —
  output JSON shape gains entry-level `errors` strings but the core
  `task_summary`/`allow`/`deny`/`completion`/`errors` keys remain. reviewer Step 3
  still consumes the same shape.

## 절대 금지 사항

- ❌ verifier가 git diff를 읽거나 SCOPE.md를 직접 다루는 것 (reviewer ★ 책임)
- ❌ verifier가 LLM-judged verdict를 내리는 것 (deterministic exit code only)
- ❌ shell metachar denylist 도입 (cap + timeout + 신뢰 모델로 충분, 위 § 보안 모델 참조)
- ❌ verifier가 자체적으로 SCOPE.md를 다시 파싱 (parsed_scope.json 신뢰)
- ❌ Step 2가 100KB output cap 우회 (truncated 플래그로 보고하고 끝)
- ❌ scope_parser.py가 reviewer 기존 sub-agent의 inline parser 행동을 1:1 모사
  (strict grammar로 격상하는 것이 본 spec의 의도)

## Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | scope_parser strict grammar로 인해 기존 SCOPE.md 작성자 freeform 입력 깨짐 | grammar-violation은 entry skip + errors 리포트, run 멈춤 X. dogfood SCOPE.md는 strict grammar로 자체 작성 |
| R2 | Step 2 sub-agent가 Bash 권한으로 의도치 않은 명령 실행 (e.g. cap 안 호환되는 한 줄 명령) | 30s timeout + 100KB cap. completion이 `rm -rf ~/`이면 cap 위반으로 reject 또는 cap 내 destructive면 SCOPE author 책임 (보안 모델 §) |
| R3 | parsed_scope.json `completion` 필드가 비어있는 케이스 | extract Step 1에서 length>0 verify, errors=["completion-empty"]면 verdict 자동 fail |
| R4 | Codex retro가 추가 위협 벡터 발견 | spec 수정 후 contracts.json 재freeze. dogfood 전 단계라 부담 적음 |
| R5 | 4-step 짧은 chain이 reviewer/builder 6-step 컨벤션과 비대칭 | verifier는 본질적으로 4 단계만 필요 (extract/execute/classify/report). 억지로 6 step 만들면 over-build |

## Source

- Parent: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_vii.md`
- Sibling spec: `2026-05-04-v4-spike-vii-design.md`
- Sibling plan: `2026-05-04-v4-spike-vii.md`
- F1 reproduction: `/tmp/spike-viii/repro_f1.py` (verified 2026-05-04)
- Carryforward source: `~/.claude/skills/assemble/docs/dogfood/spike-vi-b11.md` § F1
