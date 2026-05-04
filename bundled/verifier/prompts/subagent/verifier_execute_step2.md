# verifier Step 2 — execute completion bash

You are dispatched as verifier Step 2 sub-agent. **Bash tool access GRANTED for this single step ONLY** — Steps 1, 3, and 4 do NOT receive Bash. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- extracted_path: `{{RUN_DIR}}/extracted_completion.json`

## Goal

Read `{{RUN_DIR}}/extracted_completion.json`. If `errors` is non-empty, SKIP execution and record `skipped_due_to_extract_error`. Otherwise run the bash one-liner under `subprocess.Popen(start_new_session=True)` with a 100KB stdout/stderr cap each. Capture exit_code, stdout, stderr, duration_ms, timed_out, truncated, skipped flags.

Run with `python3 -c "..."` (or write to a temp file then `python3 <file>`) from the assemble repo root — the harness sets that as CWD. `python3` + stdlib only for the wrapper logic; the inner `subprocess.Popen` invokes bash for the completion command. Process-group kill on timeout (Codex retro F2/F3 mitigation): `start_new_session=True` puts bash in its own process group so `os.killpg(SIGKILL)` terminates the whole group, preventing `bash -c 'cmd &'` from surviving past the timeout and yielding a false-positive verdict=PASS.

```python
import json, subprocess, time, os, signal
from pathlib import Path

extracted_path = Path("{{RUN_DIR}}/extracted_completion.json")
extracted = json.loads(extracted_path.read_text(encoding="utf-8"))

if extracted["errors"]:
    result = {
        "skipped": True,
        "skip_reasons": extracted["errors"],
        "skip_reason": extracted["errors"][0],  # convenience: first label
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "duration_ms": 0,
        "timed_out": False,
        "truncated": False,
    }
else:
    cmd = ["bash", "-c", extracted["completion"]]
    t0 = time.monotonic()
    proc = None
    try:
        # start_new_session=True puts the bash process in its own process
        # group so we can kill the whole group on timeout (Codex retro F2/F3:
        # `bash -c 'cmd &'` would otherwise exit 0 leaving the backgrounded
        # process alive, yielding a false-positive verdict=pass).
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=30)
            timed_out = False
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            # Kill the whole process group (Codex F2 mitigation).
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            stdout, stderr = proc.communicate()
            timed_out = True
            exit_code = 124  # GNU coreutils `timeout(1)` standard: 124 = command timed out
    finally:
        # Defensive: if anything else goes wrong, ensure the group is dead.
        if proc is not None and proc.returncode is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    duration_ms = int((time.monotonic() - t0) * 1000)

    truncated = False
    if len(stdout) > 100_000:
        stdout = stdout[:100_000]
        truncated = True
    if len(stderr) > 100_000:
        stderr = stderr[:100_000]
        truncated = True

    result = {
        "skipped": False,
        "skip_reasons": [],
        "skip_reason": "",
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "truncated": truncated,
    }

out = Path("{{RUN_DIR}}/execution_result.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"WROTE: {out}")
```

## Security model — read before executing

This is the only verifier step that runs the SCOPE-author-provided bash command. Note: prior to Codex retro A8b, this used `subprocess.run` with a single-process timeout kill; migrated to `subprocess.Popen` + `os.killpg` process-group kill (see mitigation 1 below). Mitigations enforced HERE:

1. **Timeout 30s** — Step 2 wraps the bash call in `subprocess.Popen(start_new_session=True)` + `communicate(timeout=30)`. On timeout, the whole process group is killed via `os.killpg(SIGKILL)` (Codex retro F2/F3 — prevents `bash -c 'cmd &'` from surviving past timeout). exit_code=124 (GNU coreutils convention), `timed_out: true` recorded.
2. **Output cap 100KB** — both stdout and stderr individually capped. `truncated: true` recorded if either trips. Caps the on-disk JSON size and downstream readers' memory; NOT a streaming guard against in-memory buffering during subprocess capture (see SECURITY.md A4 for the streaming-vs-buffered distinction).
3. **Skip-if-errors** — if Step 1 (A2) reported errors (`completion-empty`, `completion-too-long`, `completion-multiline`, `parsed-scope-missing`, `parsed-scope-malformed`, `completion-non-string`), execution is SKIPPED entirely. All error labels are preserved in `skip_reasons` (full array); `skip_reason` (first element) is provided for convenience.
4. **Bash scoped to Step 2 ONLY** — Steps 1, 3, 4 do NOT receive Bash tool access (per ALLOWED_PROMPT_FILES allowlist + harness preamble v3 contract). Main Claude does NOT call Bash directly during the dispatch chain.
5. **Length cap (500)** — enforced upstream by Step 1; A3 trusts the bound.
6. **No shell metacharacter denylist** — explicit non-goal. Cap + timeout + author-trust model matches `make`/`npm test` runners. SCOPE author is the same human trusted with the rest of the run dir.

Full threat model in `bundled/verifier/SECURITY.md` (lands A4).

## Output JSON shape

```json
{
  "skipped": false,
  "skip_reasons": [],
  "skip_reason": "",
  "exit_code": 0,
  "stdout": "OK\n",
  "stderr": "",
  "duration_ms": 142,
  "timed_out": false,
  "truncated": false
}
```

Or skipped (example with multiple errors from A2):

```json
{
  "skipped": true,
  "skip_reasons": ["completion-too-long", "completion-multiline"],
  "skip_reason": "completion-too-long",
  "exit_code": null,
  "stdout": "",
  "stderr": "",
  "duration_ms": 0,
  "timed_out": false,
  "truncated": false
}
```

## Constraints

- Bash tool **only** for the completion subprocess invocation (via the python `subprocess.Popen` + `communicate` call). Do NOT explore the run_dir with ad-hoc shell commands. Do NOT use Bash for `cat` / `ls` / etc.
- Do NOT modify run_dir from the wrapper python beyond writing `execution_result.json`. The bash command itself MAY touch the filesystem (including run_dir) per SCOPE author's discretion — the security model trusts the SCOPE author for side-effects within the bash one-liner.
- Do NOT redact, sanitize, or transform stdout/stderr — preserve verbatim (capped only).
- Do NOT echo stdout content into your final WROTE message — orchestrator parses ONLY the WROTE: regex.
- ensure_ascii=False — Korean characters in stdout/stderr (e.g. test output, error messages in Korean) must round-trip.

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print `WROTE: <absolute path>` and exit.
