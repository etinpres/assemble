# verifier Step 4 — render VERIFY_REPORT.md

You are dispatched as verifier Step 4 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- extracted_path: `{{RUN_DIR}}/extracted_completion.json`
- exec_path: `{{RUN_DIR}}/execution_result.json`
- verify_path: `{{RUN_DIR}}/verify_result.json`
- template_path: `~/.claude/skills/assemble/bundled/verifier/templates/VERIFY_REPORT.md.template`

## Goal

Read the 3 prior JSONs + template. Substitute placeholders via `str.replace` (NOT Jinja). Write `{{RUN_DIR}}/VERIFY_REPORT.md` with all 7 canonical sections.

Run with `python3 -c "..."` (or write to a temp file then `python3 <file>`) from the assemble repo root — the harness sets that as CWD. python3 + stdlib only. NO Bash.

```python
import json
from pathlib import Path

run_dir = Path("{{RUN_DIR}}")
extracted = json.loads((run_dir / "extracted_completion.json").read_text(encoding="utf-8"))
exec_result = json.loads((run_dir / "execution_result.json").read_text(encoding="utf-8"))
verify = json.loads((run_dir / "verify_result.json").read_text(encoding="utf-8"))

template_path = Path.home() / ".claude/skills/assemble/bundled/verifier/templates/VERIFY_REPORT.md.template"
template = template_path.read_text(encoding="utf-8")

# Sample stdout/stderr to first 2000 chars
def sample(s, n=2000):
    if not s:
        return "(empty)"
    truncated = s[:n]
    # Codex retro F4: escape triple-backtick to prevent fenced-block break-out
    # (a malicious completion stdout could close our fence early and inject
    # fake markdown sections to deceive a human reader of VERIFY_REPORT.md)
    return truncated.replace("```", "` ` `")

# Verdict reasoning prose (2-3 sentences synthesizing reason + exec metadata)
verdict = verify["verdict"]
reason = verify["reason"]
if verdict == "pass":
    verdict_reasoning = (
        f"The completion command exited 0 in {verify['duration_ms']}ms. "
        f"This satisfies the completion criterion: deterministic exit-code verdict "
        f"requires exit_code == 0 with no skip and no timeout."
    )
else:
    verdict_reasoning = (
        f"Result: {verdict} — {reason}. "
        f"The completion command did NOT satisfy the verdict invariant "
        f"(pass iff exit_code == 0 AND not skipped AND not timed_out)."
    )

# Recommendations (empty list if pass; populated for fail variants)
recs = []
if verify["skipped"]:
    recs.append(f"- Address Step 1 errors: {', '.join(exec_result.get('skip_reasons', []))}.")
elif verify["timed_out"]:
    recs.append("- Optimize completion command to fit within 30s timeout, OR raise the cap if SCOPE author has a legitimate longer-running check.")
elif verify["exit_code"] not in (0, None):
    recs.append(f"- Inspect stderr (above) for failure mode. exit_code={verify['exit_code']}.")
if exec_result.get("truncated"):
    recs.append("- Output exceeded 100KB cap — full capture preserved only up to truncation point. Consider redirecting verbose output to a file instead of stdout.")
# Codex retro F3: warn when completion contains background operator
completion_str = extracted.get("completion", "")
if " & " in completion_str or completion_str.endswith("&") or "& " in completion_str:
    recs.append(
        "- ⚠️ Completion command contains background operator (`&`) — verdict reflects bash exit code only, not backgrounded process completion. Backgrounded process is killed on timeout via process-group SIGKILL (Step 2 mitigation), but in the success path, exit_code=0 is recorded immediately when bash exits, regardless of backgrounded work."
    )

recommendations = "\n".join(recs) if recs else "(none — verdict pass)"

# Build substitution map
subst = {
    "{{RUN_ID}}": "{{RUN_ID}}",  # orchestrator-substituted, but keep here for completeness
    "{{VERDICT}}": verdict,
    "{{REASON}}": reason,
    "{{EXIT_CODE}}": str(verify.get("exit_code")),
    "{{DURATION_MS}}": str(verify.get("duration_ms", 0)),
    "{{TIMED_OUT}}": str(verify.get("timed_out", False)).lower(),
    "{{TRUNCATED}}": str(verify.get("truncated", False)).lower(),
    "{{SKIPPED}}": str(verify.get("skipped", False)).lower(),
    "{{COMPLETION}}": extracted.get("completion", ""),
    "{{COMPLETION_LENGTH}}": str(extracted.get("length", 0)),
    "{{STDOUT_SAMPLE}}": sample(exec_result.get("stdout", "")),
    "{{STDERR_SAMPLE}}": sample(exec_result.get("stderr", "")),
    "{{VERDICT_REASONING}}": verdict_reasoning,
    "{{RECOMMENDATIONS}}": recommendations,
}

body = template
for key, val in subst.items():
    if key == "{{RUN_ID}}":
        continue  # let orchestrator handle this one
    body = body.replace(key, val)

out = run_dir / "VERIFY_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
```

## Output structure

The rendered VERIFY_REPORT.md MUST contain exactly 7 H2 sections in order:
1. Summary (with verdict line)
2. Completion command
3. Execution result
4. Stdout sample
5. Stderr sample
6. Verdict reasoning
7. Recommendations

## Constraints

- python3 + stdlib only. NO Bash, NO Jinja.
- Use `str.replace` for substitution — matches reviewer Step 6 convention.
- Sample stdout/stderr to first 2000 chars; full capture stays in execution_result.json for human deep-dive.
- ensure_ascii=False is implicit (Python str + write_text encoding="utf-8").
- Do NOT modify the 3 input JSONs.
- Do NOT regenerate the template — read it from disk.
- Recommendations bullet list — empty when verdict=pass; populated with stderr-derived hints / specific failure-mode hints when fail.
- Verdict reasoning is 2-3 sentence prose synthesis, NOT free-form LLM commentary.

## Save

`out.write_text(body, encoding="utf-8")` then `print(f"WROTE: {out}")` and exit.
