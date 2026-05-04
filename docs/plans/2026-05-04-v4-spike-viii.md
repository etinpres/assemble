# V4 Spike VIII Plan — verifier ★ bundle + F1 한글 backtick fix

**Date**: 2026-05-04
**Spec**: `docs/specs/2026-05-04-v4-spike-viii-design.md`
**Track A**: verifier ★ bundle (orthogonal — 4 step + iter helper)
**Track B**: F1 한글 backtick mangle fix in parse_scope_step1

13 tasks total (B1, B2, A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, B-13).
Each task ≡ one independent commit. subagent-driven-development:
fresh sub-agent per task. Order: Track B first (parser hardening before
verifier consumes parsed_scope.json), then Track A (verifier scaffold →
prompts → SKILL → contracts → tests → SKILL polish → security retro),
then B-13 dogfood.

---

## Order summary

```
B1 → B2 → A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9 → A10 → B-13
```

Dependencies are linear except A4 (security model docs) which can land
in parallel with A5 (classify) if needed; spec ordering kept linear for
review simplicity.

---

## Task B1 — server/scope_parser.py + unit tests

**Goal**: Add deterministic SCOPE.md parser. F1 fix root cause closure.

**Inputs**: SCOPE.md text (str). Spec § Track B § Design.

**Outputs**:
- `~/.claude/skills/assemble/server/scope_parser.py` (new)
- `~/.claude/skills/assemble/server/__init__.py` exports `parse_scope_md`
- `~/.claude/skills/assemble/tests/unit/test_scope_parser.py` (new)
- `~/.claude/skills/assemble/tests/fixtures/scope_md/` (new dir with 8 fixtures)

**Allow list**:
- `server/scope_parser.py`
- `server/__init__.py` (additive export only)
- `tests/unit/test_scope_parser.py`
- `tests/fixtures/scope_md/*.md`

**Deny list**:
- `server/run_dir.py`, `server/harness.py`, `server/inventory.py`, others
- existing reviewer/builder/debugger/plan-pack prompts
- existing reviewer prompt `parse_scope_step1.md` (Task B2 owns it)

**API**:

```python
def parse_scope_md(text: str) -> dict:
    """See spec § Track B § Design — API."""
```

**Grammar enforcement** (per spec):

1. Strict path token: no whitespace, no backticks
2. Bullet form 1: `` - `<token>` — <note> ``
3. Bullet form 2: `- <plain-token> — <note>`
4. Bullet form 3 (note-less): backtick-wrapped or plain, single token, no em-dash
5. Em-dash MUST be U+2014 with single space on each side; `–` `--` rejected
6. Outer backticks (form 1) stripped; inner content preserved verbatim

**Errors emitted** (entry-level + section-level, all collected):
- `scope-missing` — text empty/whitespace
- `allow-section-missing`, `deny-section-missing` (deny may be empty list, just no `## Deny list` header at all is fine — only allow is mandatory; clarify in test)
- `completion-empty` — completion fence absent or empty
- `allow-entry-{N}-grammar`, `deny-entry-{N}-grammar` — N is 0-indexed bullet position within the section, **including skipped bullets** (so callers can map back to source line)

**Test cases** (8 minimum):

| # | Fixture | Expected |
|---|---|---|
| T1 | `ascii_simple.md` — backtick-wrapped allow + plain-path allow + note | both parse, no errors |
| T2 | `korean_strict.md` — strict-grammar Korean entry: ``- `path/with/한글.md` — 한글 노트`` | parses, path preserved verbatim, note in Korean |
| T3 | `korean_freeform_deny.md` — B-11 reproducer: `` - `server/` 내 `run_dir.py` 외 모든 파일 (`__init__.py`, ...) — 변경 금지 `` | error `deny-entry-0-grammar`, entry skipped |
| T4 | `missing_allow.md` — only `## Deny list` + completion | error `allow-section-missing` |
| T5 | `empty_completion.md` — empty fence | error `completion-empty` |
| T6 | `em_dash_variants.md` — `–` en-dash + `--` double-hyphen | both reject as grammar errors |
| T7 | `note_less.md` — bullets with no em-dash | parse, note = "" |
| T8 | `mixed.md` — 4 valid + 2 freeform deny | 4 entries stored, 2 errors emitted |

**Implementation notes**:
- regex compile-once at module level
- use `re.VERBOSE` for readability
- helper `_parse_bullet(line, idx, section_label) -> tuple[entry_or_None, error_or_None]`
- H1 extraction: `re.match(r'^# SCOPE\s*—\s*(.+)$', line)`
- completion fence: state machine on `^\`\`\`bash` open + `^\`\`\`` close; capture intervening lines, `.strip()`

**Acceptance**:
- `pytest tests/unit/test_scope_parser.py -v` → 8 tests pass
- B-11 reproducer fixture `korean_freeform_deny.md` emits the expected error label
- spec § Track B § B.1–B.8 satisfied

**Commit message**: `feat(v4-spike-viii-B1): server/scope_parser.py — strict-grammar SCOPE.md parser closes F1 mangle`

---

## Task B2 — parse_scope_step1.md update (helper call + grammar doc)

**Goal**: reviewer Step 1 sub-agent uses `parse_scope_md` helper instead of
emitting inline parser logic. SCOPE.md author guidance added.

**Inputs**: B1 helper available. Spec § Track B § design.

**Outputs**:
- `~/.claude/skills/assemble/bundled/reviewer/prompts/subagent/parse_scope_step1.md` (modify)
- `~/.claude/skills/assemble/tests/unit/test_parse_scope_step1_prompt.py` (new — checks prompt body for helper import marker)

**Allow list**:
- `bundled/reviewer/prompts/subagent/parse_scope_step1.md`
- `tests/unit/test_parse_scope_step1_prompt.py`

**Deny list**:
- other reviewer prompts (Steps 2~6)
- builder/debugger/plan-pack prompts
- server/* (B1 owns scope_parser.py)

**Prompt body changes**:

1. Replace inline parsing instructions ("split on FIRST ` — `", "strip leading `- `") with helper invocation block:

   ```python
   import json, sys
   from pathlib import Path
   from server.scope_parser import parse_scope_md

   text = Path("{{RUN_DIR}}/SCOPE.md").read_text(encoding="utf-8")
   result = parse_scope_md(text)
   out = Path("{{RUN_DIR}}/parsed_scope.json")
   out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
   print(f"WROTE: {out}")
   ```

2. Add `## SCOPE.md grammar` section with three accepted bullet forms + freeform-prose failure mode + Korean+backtick example (cite the B-11 reproducer)

3. Keep `## Inputs` and `## Save` sections; remove `## Constraints` em-dash split rule (now in helper)

4. Update `## Output JSON shape` to reflect new entry-level error labels

**Tests**:
- regex `from server\.scope_parser import parse_scope_md` present in prompt body
- regex `split on FIRST` ABSENT from prompt body (old logic removed)
- prompt frontmatter unchanged
- prompt file count unchanged (rename guard)

**Acceptance**:
- spec § Track B § B.6 satisfied
- reviewer existing tests still green (parse_scope_step1 ALLOWED_PROMPT_FILES gate, dispatch contract)

**Commit message**: `refactor(v4-spike-viii-B2): parse_scope_step1.md calls server.scope_parser, drops inline parser logic`

---

## Task A1 — verifier bundle scaffold

**Goal**: Empty-but-discoverable verifier bundle. Inventory, allowlist, stage routing, frontmatter all wired.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/SKILL.md` (new — minimal frontmatter + "scaffolding only" body, body filled in A7)
- `~/.claude/skills/assemble/bundled/verifier/prompts/subagent/.gitkeep`
- `~/.claude/skills/assemble/bundled/verifier/prompts/orchestrator/.gitkeep`
- `~/.claude/skills/assemble/bundled/verifier/templates/.gitkeep`
- `~/.claude/skills/assemble/server/harness.py` — extend `_BUNDLES` tuple + `_BUNDLED_DIR_TO_STAGE` map + `ALLOWED_PROMPT_FILES` set
- `~/.claude/skills/assemble/tests/unit/test_verifier_inventory_scan.py` (new)

**Allow list**:
- `bundled/verifier/**`
- `server/harness.py` (additive — ALLOWED_PROMPT_FILES set, _BUNDLES tuple, stage map)
- `tests/unit/test_verifier_inventory_scan.py`

**Deny list**:
- existing reviewer/builder/debugger/plan-pack contents
- `server/run_dir.py`, `server/__init__.py`, `server/scope_parser.py`
- contracts.json (A8 owns)

**SKILL.md frontmatter** (final form even though body comes A7):

```yaml
---
name: "verifier"
description: "Verify-stage ★ bundle. Executes parsed_scope.json completion bash and emits deterministic exit-code verdict. Sub-agents own all reads/writes/Bash; main Claude orchestrates only."
stages: ["verify"]
---
```

A7 fills the body. A1 leaves a "## Status: scaffolding (Spike VIII A1) — body filled in A7" stub.

**Harness changes**:

```python
# server/harness.py
_BUNDLES = ("plan-pack", "debugger", "builder", "reviewer", "verifier")  # add

_BUNDLED_DIR_TO_STAGE = {
    "plan-pack": "plan",
    "debugger":  "debug",
    "builder":   "execute",
    "reviewer":  "review",
    "verifier":  "verify",  # add
}

ALLOWED_PROMPT_FILES = frozenset({
    # ... existing 6 reviewer + 6 builder + 6 debugger + plan-pack ...
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md",
})
```

(Iteration helper `verifier_iter_revisit.md` is NOT in the subagent allowlist — it's loaded by main directly, not dispatched.)

**Tests**:
- `test_verifier_in_inventory_scan` — scanning bundled/ yields entry with `name="verifier"`, `bundled=True`, `stages=["verify"]` (Spike VI B1 fix style)
- `test_verifier_allowlist_added` — 4 prompt filenames in `ALLOWED_PROMPT_FILES`
- `test_verifier_stage_route` — stage `"verify"` → bundle name `"verifier"`
- `test_existing_bundles_unchanged` — reviewer/builder/debugger/plan-pack still present

**Acceptance**:
- spec § A.1, A.2, A.9 satisfied
- pytest baseline +4 new tests, no regressions

**Commit message**: `feat(v4-spike-viii-A1): verifier bundle scaffold + harness allowlist + inventory route`

---

## Task A2 — verifier_extract_step1.md (parsed_scope.json → completion bash)

**Goal**: Step 1 sub-agent reads parsed_scope.json, validates `completion` field, writes `extracted_completion.json`.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/prompts/subagent/verifier_extract_step1.md` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_extract_step1_prompt.py` (new — body invariants only; full E2E in A9)

**Allow list**:
- `bundled/verifier/prompts/subagent/verifier_extract_step1.md`
- `tests/unit/test_verifier_extract_step1_prompt.py`

**Deny list**:
- other verifier prompt files (A3/A5/A6 own)
- reviewer/builder/debugger/plan-pack prompts
- server/* (A1 already wired)

**Prompt body shape** (per reviewer prompt convention):

```
# verifier Step 1 — extract completion bash

You are dispatched as verifier Step 1 sub-agent. Print `WROTE: <absolute path>`
on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json`

## Goal

Read parsed_scope.json, validate the `completion` field, write
`{{RUN_DIR}}/extracted_completion.json`.

## Validation rules

1. completion must be non-empty after `.strip()`
2. `len(completion) <= 500` (security cap, see verifier SKILL.md § Security)
3. completion must be a single line (no embedded newline)

If any rule violated, write the JSON with `errors` populated and exit 0
(orchestrator detects via `errors` field, not exit code).

## Output JSON shape

```json
{
  "completion": "<bash one-liner stripped>",
  "length": <int>,
  "errors": []   // or ["completion-empty", "completion-too-long", "completion-multiline"]
}
```

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print
`WROTE: <absolute path>` and exit.

## Constraints

- python3 + stdlib only. Do NOT call Bash.
- Preserve completion verbatim — do not normalize quotes, do not reformat.
- Do NOT execute the completion command (Step 2's responsibility).
```

**Tests**:
- prompt body contains `{{RUN_DIR}}` placeholder
- prompt body contains `extracted_completion.json` artifact name
- prompt body does NOT contain `Bash` instruction (extract step has no shell access)
- prompt body contains `len(completion) <= 500` rule
- WROTE: line discipline present

**Acceptance**: spec § A2 satisfied; ALLOWED_PROMPT_FILES gate passes for this filename.

**Commit message**: `feat(v4-spike-viii-A2): verifier_extract_step1 prompt — parsed_scope.json → completion bash with length cap`

---

## Task A3 — verifier_execute_step2.md (Bash execution + capture)

**Goal**: Step 2 sub-agent runs the bash command from extracted_completion.json with timeout + output cap, writes execution_result.json.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/prompts/subagent/verifier_execute_step2.md` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_execute_step2_prompt.py` (new)

**Allow list**:
- `bundled/verifier/prompts/subagent/verifier_execute_step2.md`
- `tests/unit/test_verifier_execute_step2_prompt.py`

**Deny list**:
- other verifier prompts
- reviewer/builder/debugger/plan-pack prompts

**Prompt body shape**:

```
# verifier Step 2 — execute completion bash

You are dispatched as verifier Step 2 sub-agent. **Bash tool access GRANTED**
for this single step. Print `WROTE: <absolute path>` and exit.

## Inputs

- run_id: `{{RUN_ID}}`
- extracted_path: `{{RUN_DIR}}/extracted_completion.json`

## Goal

Read extracted_completion.json. If `errors` non-empty, skip execution and
record `skipped_due_to_extract_error`. Otherwise run the bash one-liner
under `timeout 30s` with a 100KB stdout/stderr cap each. Capture exit_code,
stdout, stderr, duration_ms, timed_out, truncated flags.

## Execution recipe

```python
import json, subprocess, time
from pathlib import Path

extracted = json.loads(Path("{{RUN_DIR}}/extracted_completion.json").read_text())
if extracted["errors"]:
    result = {
        "skipped": True,
        "skip_reason": extracted["errors"][0],
        "exit_code": None, "stdout": "", "stderr": "",
        "duration_ms": 0, "timed_out": False, "truncated": False,
    }
else:
    cmd = ["bash", "-c", extracted["completion"]]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=30, errors="replace")
        timed_out = False
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    duration_ms = int((time.monotonic() - t0) * 1000)

    truncated = False
    if len(stdout) > 100_000:
        stdout = stdout[:100_000]; truncated = True
    if len(stderr) > 100_000:
        stderr = stderr[:100_000]; truncated = True

    result = {
        "skipped": False, "skip_reason": "",
        "exit_code": exit_code, "stdout": stdout, "stderr": stderr,
        "duration_ms": duration_ms,
        "timed_out": timed_out, "truncated": truncated,
    }

out = Path("{{RUN_DIR}}/execution_result.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(f"WROTE: {out}")
```

## Constraints

- Bash tool **only** for the completion subprocess invocation. No
  ad-hoc shell exploration of the run_dir.
- Do NOT modify run_dir contents beyond writing execution_result.json.
- Do NOT redact or sanitize stdout/stderr — preserve verbatim (capped only).
- Do NOT echo stdout content into your final WROTE message.
```

**Tests**:
- prompt body contains `subprocess.run` + `timeout=30`
- prompt body contains `100_000` (output cap)
- prompt body contains `timed_out` + `truncated` fields
- prompt body contains `Bash tool access GRANTED` security marker (used by Codex retro at A8)

**Acceptance**: spec § A.3 + § Security model satisfied.

**Commit message**: `feat(v4-spike-viii-A3): verifier_execute_step2 prompt — sandboxed bash with timeout 30s + 100KB cap`

---

## Task A4 — security model (SKILL.md § Security inserted, A7 stub later expands)

**Goal**: Document threat model + mitigations + Bash-scope rule. Surface as
a clearly labeled section so Codex retro at A8 can review it standalone.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/SECURITY.md` (new — primary doc)
- `~/.claude/skills/assemble/bundled/verifier/SKILL.md` (modify — add link to SECURITY.md from the scaffolding stub)

**Allow list**:
- `bundled/verifier/SECURITY.md`
- `bundled/verifier/SKILL.md` (additive link only; full body lands A7)

**Deny list**:
- other verifier prompt files
- existing bundles

**SECURITY.md content** (final form, ~50 lines):

```markdown
# verifier ★ — Security model

## Surface

verifier executes `parsed_scope.json.completion` (one-line bash) inside a
sub-agent dispatched by main Claude. SCOPE.md author writes that string;
sub-agent runs it. This is the first ★ bundle to grant Bash tool access.

## Threat model

| # | Threat | Severity | Mitigation |
|---|---|---|---|
| T1 | Malicious SCOPE author injects destructive payload (`rm -rf`, `> /dev/sda`) | low | length cap (500), runner trust model — same as `make`/`npm test` |
| T2 | Runaway completion blocks pipeline | medium | `timeout 30s` POSIX |
| T3 | Output flood (1GB stdout) | medium | 100KB cap each on stdout/stderr; `truncated: true` flag |
| T4 | Network exfiltration | low | length cap forces minimal payload; SCOPE author trust |

## Mitigations enumerated

1. **Length cap** — Step 1 rejects `len(completion) > 500`
2. **Timeout** — Step 2 wraps in `subprocess.run(..., timeout=30)`; killed sub-process recorded as `timed_out=true, exit_code=124`
3. **Output cap** — Step 2 truncates stdout/stderr to 100KB each
4. **Bash scope** — Step 2 sub-agent prompt is the ONLY verifier prompt
   granting Bash. Steps 1/3/4 are pure I/O sub-agents
5. **Allowlist gate** — `ALLOWED_PROMPT_FILES` in `server/harness.py`
   contains exactly 4 verifier prompts; non-allowlisted dispatch raises
6. **Orchestrator-only main** — main Claude does NOT call Bash during
   the dispatch chain (verified in B-13 AC10)

## Explicit non-goals

- **No shell metacharacter denylist.** Denylists leak. Cap+timeout+author-trust matches the trust model of CI runners and build tools.
- **No sandboxing (chroot/firejail/etc.)** — out of V4 scope; Step 2 runs
  with the same privileges as the rest of the dispatch chain.
- **No secret scrubbing** — SCOPE author's responsibility to keep secrets
  out of the completion command (same convention as commit messages).

## Codex retro gate

Spike VIII A8 dispatches `codex:codex-rescue` for second-opinion on this
threat model + Step 2 prompt body before contracts.json freeze. Findings
either close as documented "non-goal" or amend SECURITY.md before A9 tests.
```

**SKILL.md scaffolding stub modification** (additive):

Add at the end of the stub body:

```
> See `SECURITY.md` for threat model + mitigation surface (Step 2 Bash scope).
```

**Tests**: none added in A4 (Codex review is the validator). A8 will
add a regression test that SECURITY.md exists and contains the four
threat-table headings.

**Acceptance**: SECURITY.md present + Codex review pending at A8.

**Commit message**: `docs(v4-spike-viii-A4): verifier SECURITY.md — threat model + Bash-scope mitigations`

---

## Task A5 — verifier_classify_step3.md (exit → verdict)

**Goal**: Step 3 sub-agent reads execution_result.json, applies deterministic
verdict rule, writes verify_result.json.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/prompts/subagent/verifier_classify_step3.md` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_classify_step3_prompt.py` (new)

**Allow list**:
- `bundled/verifier/prompts/subagent/verifier_classify_step3.md`
- `tests/unit/test_verifier_classify_step3_prompt.py`

**Deny list**: other verifier prompts, existing bundles.

**Prompt body shape** (~40 lines):

```
# verifier Step 3 — classify execution result

You are dispatched as verifier Step 3 sub-agent. Print `WROTE: <absolute path>`
and exit. No other prose.

## Inputs

- run_id: `{{RUN_ID}}`
- exec_path: `{{RUN_DIR}}/execution_result.json`

## Verdict logic (deterministic)

```python
exec_result = json.loads(Path("{{RUN_DIR}}/execution_result.json").read_text())

if exec_result["skipped"]:
    verdict = "fail"
    reason = f"skipped: {exec_result['skip_reason']}"
elif exec_result["timed_out"]:
    verdict = "fail"
    reason = "timed out (30s budget)"
elif exec_result["exit_code"] == 0:
    verdict = "pass"
    reason = "completion command exited 0"
else:
    verdict = "fail"
    reason = f"exited {exec_result['exit_code']}"

result = {
    "verdict": verdict,
    "reason": reason,
    "exit_code": exec_result["exit_code"],
    "duration_ms": exec_result["duration_ms"],
    "truncated": exec_result["truncated"],
    "timed_out": exec_result["timed_out"],
}
out = Path("{{RUN_DIR}}/verify_result.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(f"WROTE: {out}")
```

## Constraints

- python3 + stdlib only. NO Bash.
- NO subjective judgment — verdict is `pass` if and only if `exit_code == 0`
  and not skipped/timed-out.
- Truncated stdout/stderr does NOT auto-fail — verdict logic ignores it; the
  `truncated` flag surfaces in VERIFY_REPORT for human review.
```

**Tests**:
- prompt body contains the deterministic verdict rule (regex match for
  `verdict = "pass" if`)
- prompt body does NOT contain `Bash` permission marker
- prompt body asserts `truncated` does not auto-fail

**Acceptance**: spec § A.6 (verdict invariant) satisfied at prompt level.

**Commit message**: `feat(v4-spike-viii-A5): verifier_classify_step3 prompt — deterministic exit-code verdict`

---

## Task A6 — verifier_report_step4.md + VERIFY_REPORT.md.template

**Goal**: Step 4 sub-agent renders 7-section VERIFY_REPORT.md from prior JSONs.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/prompts/subagent/verifier_report_step4.md` (new)
- `~/.claude/skills/assemble/bundled/verifier/templates/VERIFY_REPORT.md.template` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_report_step4_prompt.py` (new)

**Allow list**:
- `bundled/verifier/prompts/subagent/verifier_report_step4.md`
- `bundled/verifier/templates/VERIFY_REPORT.md.template`
- `tests/unit/test_verifier_report_step4_prompt.py`

**Deny list**: other verifier prompts, existing bundles, contracts.json.

**Template structure** (`VERIFY_REPORT.md.template`):

```markdown
# Verification report — {{RUN_ID}}

**Verdict**: {{VERDICT}}
**Reason**: {{REASON}}

## 1. Summary

Run `{{RUN_ID}}` verified completion criterion. Result: **{{VERDICT}}** ({{REASON}}).
Exit code: `{{EXIT_CODE}}`. Duration: `{{DURATION_MS}}ms`.

## 2. Completion command

```bash
{{COMPLETION}}
```

(captured from `parsed_scope.json.completion`, length {{COMPLETION_LENGTH}} chars)

## 3. Execution result

| Field | Value |
|---|---|
| Exit code | `{{EXIT_CODE}}` |
| Duration | `{{DURATION_MS}}ms` |
| Timed out | `{{TIMED_OUT}}` |
| Output truncated | `{{TRUNCATED}}` |
| Skipped | `{{SKIPPED}}` |

## 4. Stdout sample

```
{{STDOUT_SAMPLE}}
```

(first 2000 chars; full capture in `execution_result.json`)

## 5. Stderr sample

```
{{STDERR_SAMPLE}}
```

(first 2000 chars; full capture in `execution_result.json`)

## 6. Verdict reasoning

{{VERDICT_REASONING}}

## 7. Recommendations

{{RECOMMENDATIONS}}
```

**Prompt body** (~50 lines):

Sub-agent reads template, substitutes via `str.replace` (NOT Jinja — same convention as reviewer Step 6), writes `VERIFY_REPORT.md`. Sample fields capped at 2000 chars from the full execution_result.json. Verdict reasoning is a 2–3 sentence prose synthesis ("the command exited 0 because X, satisfying the completion criterion"). Recommendations bullet list — empty when verdict=pass, populated with stderr-derived hints when fail.

**Tests**:
- prompt body references all 7 section titles in order
- template file present and contains all 7 H2 headings
- prompt body uses `str.replace` (not jinja)

**Acceptance**: spec § A.7 (7-section invariant) satisfied at prompt+template level.

**Commit message**: `feat(v4-spike-viii-A6): verifier_report_step4 prompt + VERIFY_REPORT.md.template — 7-section render`

---

## Task A7 — SKILL.md body expansion

**Goal**: Replace A1's stub body with full reviewer-style SKILL.md (When to invoke, Inputs, Artifacts, Verdict logic, CRITICAL orchestrator-only, Step-by-step 0~4, Iteration audit invariant, Sub-agent matrix, Identity guards). Plus orchestrator helper `verifier_iter_revisit.md`.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/SKILL.md` (replace body)
- `~/.claude/skills/assemble/bundled/verifier/prompts/orchestrator/verifier_iter_revisit.md` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_skill_md_invariants.py` (new)

**Allow list**:
- `bundled/verifier/SKILL.md`
- `bundled/verifier/prompts/orchestrator/verifier_iter_revisit.md`
- `tests/unit/test_verifier_skill_md_invariants.py`

**Deny list**:
- subagent prompts (A2/A3/A5/A6 own)
- SECURITY.md (A4 owns; A7 only links to it)
- contracts.json (A8 owns)
- existing bundles

**SKILL.md body shape** (mirrors reviewer SKILL.md verbatim where structure overlaps):

- `# verifier ★ — completion criterion runner`
- `## When to invoke` — after parsed_scope.json exists, when AC bash needs deterministic verdict
- `## Inputs` — run_id (resolves run_dir), parsed_scope.json (must exist with non-empty completion)
- `## Artifacts` — primary VERIFY_REPORT.md + 3 intermediate JSONs
- `## Verdict logic` — exit_code → pass/fail, deterministic
- `## CRITICAL — orchestrator-only enforcement` — main never calls Bash, all reads/parses/writes/execs in sub-agents
- `## Allowlist` — exactly 4 subagent prompts (extract/execute/classify/report)
- `## Step-by-step workflow` — Steps 0~4 mirroring reviewer's pattern
- `## Iteration audit invariant` — 4 rows in dispatches.jsonl per iter
- `## Sub-agent matrix` — table from spec
- `## Security` — link to SECURITY.md (A4 owns content)
- `## Identity guards` — orchestrator-only ✓, preamble v3 ✓, record_dispatch mandatory, Bash scoped to Step 2

**verifier_iter_revisit.md** (orchestrator helper, ~30 lines):

Loaded by main Claude when user requests re-verification (e.g. completion edited). Instructs main on:
1. Re-read parsed_scope.json (skip Step 1 dispatch if completion unchanged)
2. Re-dispatch Steps 2~4 with `iter{N}` step labels
3. Append `## Iteration N` section to VERIFY_REPORT.md (don't overwrite)

Not in ALLOWED_PROMPT_FILES (read directly by main, not dispatched).

**Tests**:
- SKILL.md contains all 11 H2 sections in the order above
- SKILL.md frontmatter strict-load (Spike VI Phase A invariant)
- `verifier_iter_revisit.md` exists, has no `## Inputs` placeholder block (orchestrator helper, not subagent)
- SKILL.md body references SECURITY.md path

**Acceptance**: spec § A.1, A.7, A.8 satisfied; SKILL.md is reviewer-symmetric.

**Commit message**: `feat(v4-spike-viii-A7): verifier SKILL.md body + verifier_iter_revisit orchestrator helper`

---

## Task A8 — contracts.json 3 entries + Codex retro

**Goal**: Add 3 contract entries; run Codex retro on threat model + Step 2 prompt; record findings inline.

**Outputs**:
- `~/.claude/skills/assemble/tests/contracts/contracts.json` (modify — append 3 entries)
- `~/.claude/skills/assemble/tests/contracts/test_contracts_spike_viii.py` (new)
- `~/.claude/skills/assemble/docs/dogfood/spike-viii-codex-retro.md` (new — Codex transcript + amendments)

**Allow list**:
- `tests/contracts/contracts.json`
- `tests/contracts/test_contracts_spike_viii.py`
- `docs/dogfood/spike-viii-codex-retro.md`
- (potentially `bundled/verifier/SECURITY.md` if Codex flags amendment)
- (potentially `bundled/verifier/prompts/subagent/verifier_execute_step2.md` if Codex flags amendment)

**Deny list**:
- existing contract entries
- other verifier files unless Codex retro requires amendment

**Contract entries** (3):

```json
{
  "id": "spike-viii-verifier-allowlist",
  "type": "allowlist",
  "owner": "verifier",
  "files": [
    "verifier_extract_step1.md",
    "verifier_execute_step2.md",
    "verifier_classify_step3.md",
    "verifier_report_step4.md"
  ],
  "description": "verifier ★ subagent prompt files. Bash tool granted to step2 only."
},
{
  "id": "spike-viii-verifier-verdict-invariant",
  "type": "invariant",
  "owner": "verifier",
  "rule": "verdict == 'pass' iff exit_code == 0 AND not skipped AND not timed_out",
  "description": "Deterministic verdict logic. No LLM judgment. Truncated output is metadata, not verdict input."
},
{
  "id": "spike-viii-verifier-artifact-invariant",
  "type": "invariant",
  "owner": "verifier",
  "rule": "VERIFY_REPORT.md MUST contain 7 H2 sections (Summary, Completion command, Execution result, Stdout sample, Stderr sample, Verdict reasoning, Recommendations) in this order",
  "description": "Schema lock for downstream consumers (keeper ★ trace audit, future ship gates)"
}
```

**Codex retro procedure**:

Use `codex:codex-rescue` agent in foreground:

```
Prompt to Codex:
"Spike VIII verifier ★ bundle introduces sub-agent Bash execution of an
SCOPE.md-author-controlled completion one-liner. Threat model in
bundled/verifier/SECURITY.md (~50 lines). Step 2 prompt in
bundled/verifier/prompts/subagent/verifier_execute_step2.md. Cap = 500
char + 30s timeout + 100KB output truncation. No metacharacter denylist.

Challenge: are the cap+timeout+output-cap mitigations sufficient to
contain T1 (destructive author payload)? Specifically:
1. Can a 500-char one-liner deliver a destructive payload that the cap
   does not stop? (e.g. `eval $(curl url)` where url is short)
2. Are there bypass paths around `subprocess.run(timeout=30)`? (e.g.
   `nohup` + background process)
3. Is `text=True` + 100KB cap sufficient for binary-output commands
   that might inject bytes downstream readers (VERIFY_REPORT.md
   markdown injection via stderr sample)?
4. Anything we missed?

Be adversarial. Returning 'looks fine' is failure mode."
```

Findings recorded in `docs/dogfood/spike-viii-codex-retro.md`:
- Each Codex challenge with verbatim quote
- Resolution: amend SECURITY.md / prompt / SKILL.md, OR document explicit non-goal with reasoning
- Final verdict line ("retro complete; 0 amendments" or "retro complete; N amendments applied")

If Codex flags vector requiring amendment, A8 commit includes amendment files; otherwise just contracts + retro doc.

**Tests** (`test_contracts_spike_viii.py`):
- 3 new contract entries present in contracts.json with expected ids
- allowlist contract has exactly 4 file entries
- verdict invariant rule matches deterministic logic regex
- artifact invariant references all 7 section titles

**Acceptance**:
- spec § A.6, A.7 satisfied (contract level)
- Codex retro doc present + closed
- Any amendments triggered by Codex retro applied + tested

**Commit message**:
- If 0 amendments: `docs(v4-spike-viii-A8): contracts.json 3 entries + Codex retro complete (no amendments)`
- If amendments: `feat(v4-spike-viii-A8): contracts.json 3 entries + Codex retro amendments to SECURITY/prompts`

---

## Task A9 — integration tests (unit + scan + harness regression)

**Goal**: Wire the verifier bundle through the full harness path; ensure no regression in existing 4 ★ bundles + plan-pack.

**Outputs**:
- `~/.claude/skills/assemble/tests/unit/test_verifier_dispatch_path.py` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_run_dir_substitution.py` (new)
- `~/.claude/skills/assemble/tests/unit/test_verifier_preamble_attached.py` (new)

**Allow list**:
- `tests/unit/test_verifier_dispatch_path.py`
- `tests/unit/test_verifier_run_dir_substitution.py`
- `tests/unit/test_verifier_preamble_attached.py`

**Deny list**:
- production code (A1~A8 own respective surfaces)
- contracts.json (A8 owns)

**Tests**:

`test_verifier_dispatch_path.py`:
- `dispatch_prompt("verifier", "verifier_extract_step1.md")` returns prompt with v3 preamble + RUN_DIR substituted
- non-allowlisted file (e.g. `verifier_unknown.md`) raises
- iteration helper `verifier_iter_revisit.md` is NOT in subagent allowlist (raises if dispatched)

`test_verifier_run_dir_substitution.py`:
- all 4 verifier subagent prompts contain `{{RUN_DIR}}` after dispatch_prompt resolution → contains absolute path
- no `{{RUN_DIR}}` literal survives in dispatched prompt

`test_verifier_preamble_attached.py`:
- sha256 of first 256 bytes of dispatched prompt = canonical v3 hash `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159`
- 4 prompts × 1 sha each = 4 hash matches

**Existing bundle regression check** (run by CI, not new test):
- pytest count baseline 353 + B1 tests + A1 tests + A2 tests + A3 tests + A5 tests + A6 tests + A7 tests + A8 tests + A9 tests = expect ~25–35 new tests, no failures in pre-existing 353

**Acceptance**: spec § A.4, A.5, A.10 satisfied; baseline maintained.

**Commit message**: `test(v4-spike-viii-A9): verifier integration — dispatch path + RUN_DIR + preamble v3 sha`

---

## Task A10 — SKILL.md polish + CHANGELOG entry

**Goal**: Final SKILL.md review (post-A8 amendments if any), CHANGELOG `[Unreleased] V4 Spike VIII` entry.

**Outputs**:
- `~/.claude/skills/assemble/bundled/verifier/SKILL.md` (polish — apply Codex amendments if not done at A8)
- `~/.claude/skills/assemble/CHANGELOG.md` (modify — `[Unreleased]` section gains Spike VIII entry)

**Allow list**:
- `bundled/verifier/SKILL.md` (polish only — body shape from A7)
- `CHANGELOG.md`

**Deny list**:
- everything else (this is doc polish only)

**CHANGELOG entry shape**:

```markdown
## [Unreleased] — V4 Spike VIII

### Added

- **verifier ★ bundle** — first ★ bundle to execute completion bash and
  emit deterministic exit-code verdict. 4 sub-agent steps (extract /
  execute / classify / report) + iteration helper. Bash tool granted
  to Step 2 only with 500-char length cap + 30s timeout + 100KB output
  cap. cross-cutting B (AC=bash 실행) self-mechanized.
- `server/scope_parser.py` — strict-grammar SCOPE.md parser, closes F1
  Korean+backtick deny mangle (Spike VI carryforward).

### Changed

- `parse_scope_step1.md` (reviewer ★) — calls `server.scope_parser.parse_scope_md`
  instead of inline parser logic. SCOPE.md grammar guidance added.

### Contracts

- `spike-viii-verifier-allowlist` (4 prompts)
- `spike-viii-verifier-verdict-invariant` (deterministic exit→verdict)
- `spike-viii-verifier-artifact-invariant` (7-section VERIFY_REPORT.md)

### Dogfood

- B-13: 4-dispatch verifier ★ run + intentional-fail companion. 12/12 AC PASS.
```

**Acceptance**: CHANGELOG present and valid markdown; SKILL.md final form passes A9 invariants.

**Commit message**: `docs(v4-spike-viii-A10): CHANGELOG + verifier SKILL.md polish`

---

## Task B-13 — dogfood ship gate

**Goal**: First end-to-end self-verification of verifier ★. Validates F1 fix in the same run.

**Outputs**:
- `~/.claude/skills/assemble/docs/dogfood/spike-viii-b13.md` (new — full transcript + 12 AC table)
- (no production code in this task; ship CHANGELOG `## V4 Spike VIII` line lifts `[Unreleased]` once 12/12 PASS)

**Procedure**:

1. **Setup** — fresh run_id (e.g. `20260504-spikeviii-b13`). Author SCOPE.md per spec § B-13 § dogfood SCOPE template (Korean+backtick deny entries strict grammar). Place at `~/.claude/channels/assemble/runs/<rid>/SCOPE.md`.

2. **Step Track B integration** — Dispatch reviewer's `parse_scope_step1.md` via `general-purpose` agent (Track B helper now active). Verify `parsed_scope.json` has Korean entries with no `entry-grammar` errors → AC11 PASS.

3. **Step verifier** — Dispatch verifier 4 steps in order:
   - Step 1: extract — captures `completion = "python3 -c \"from server.run_dir import list_runs, run_dir_path; ..."`
   - Step 2: execute — runs bash, captures `exit_code=0, stdout="OK\n", stderr=""`
   - Step 3: classify — verdict=pass, reason="completion command exited 0"
   - Step 4: report — VERIFY_REPORT.md 7 sections rendered

4. **Companion intentional-fail run** — fresh run_id `<rid>-fail`. SCOPE.md identical except completion = `false` (or `python3 -c "import sys; sys.exit(1)"`). Dispatch verifier 4 steps. Verify verdict=fail, exit_code=1, reason="exited 1" → AC12 PASS.

5. **Audit** — read `dispatches.jsonl` from primary run, verify 4 rows + every preamble sha = canonical v3.

6. **Wall time** — record real-dispatch start/end; budget 400s. (4-step shorter than reviewer's 6 = ~230s; 400s is comfortable.)

7. **Orchestrator-only audit** — grep session transcript for direct Bash calls by main during dispatch chain. Expected: only sub-agent dispatches.

8. **Doc** — write `docs/dogfood/spike-viii-b13.md` with all 12 AC table entries, evidence quotes, screenshots/JSON dumps where relevant.

9. **If 12/12 PASS** — flip CHANGELOG `[Unreleased]` → `## [V4 Spike VIII] — 2026-05-04`. Commit. Memory file `project_assemble_v4_spike_viii.md` written + `MEMORY.md` index updated.

**Allow list**:
- `docs/dogfood/spike-viii-b13.md`
- `CHANGELOG.md` (only the unreleased→released flip)
- (no other files — production code finalized at A10)

**Deny list**:
- everything else — B-13 is verification + doc only

**Acceptance**: 12/12 AC PASS per spec table.

**Commit message**: `docs(v4-spike-viii-B13): B-13 dogfood 12/12 PASS + ship CHANGELOG`

---

## Risk register (plan-level, additive to spec)

| # | Risk | Mitigation |
|---|---|---|
| P1 | A4 SECURITY.md amendments from Codex retro overlap with A7 SKILL.md polish → merge churn | Sequence: A7 lands skeletal SKILL.md → A8 Codex retro → A10 final polish absorbs amendments. A8 amends SECURITY.md only if Codex flags |
| P2 | A2/A3/A5/A6 prompts touch shared `prompts/subagent/` dir → potential file-add ordering issue | Independent file names, no shared file content. Each task `Write`s a distinct path |
| P3 | Track B helper `parse_scope_md` lands before reviewer prompt that consumes it (B1 → B2) — could break reviewer in interim if test suite runs B1 + B2 separately | B1 helper is additive; reviewer prompt unchanged until B2. No regression window. Confirmed via test isolation in B1 commit |
| P4 | B-13 SCOPE.md uses Korean+backtick — if author writes freeform-prose deny by mistake, Track B fix surfaces grammar errors → AC1 fails | Spec dogfood SCOPE template uses STRICT grammar deliberately. AC1 + AC11 specifically check this case |
| P5 | verifier Step 2 timeout=30s might be tight for legitimate slow completions (e.g. test suite invocation) | dogfood completion is single python import; ≪30s. Future spec amendment can raise; for V4 ship 30s is safe ceiling |

---

## Out of scope reminders

- `keeper ★` (cross-cutting C trace audit) — Spike IX+ candidate
- `shipper ★` — Spike IX+ candidate
- F4 perf collapse (Step 1/2/3/5/6 → deterministic shell) — separate spike
- naming convention `<bundle>_<step>.md` migration — case-by-case
- subagent-driven-development internal hardening (Spike VII follow-up)
- Codex CLI / Gemini CLI compat — V4 비범위

## Source

- Spec: `docs/specs/2026-05-04-v4-spike-viii-design.md`
- Parent: `project_assemble_v4_spec.md`
- Sibling: `docs/plans/2026-05-04-v4-spike-vii.md`
- F1 reproduction: `/tmp/spike-viii/repro_f1.py`
