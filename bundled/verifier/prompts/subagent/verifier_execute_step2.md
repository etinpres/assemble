# verifier Step 2 — execute completion bash

You are dispatched as verifier Step 2 sub-agent. **Bash tool access GRANTED for this single step ONLY** — Steps 1, 3, and 4 do NOT receive Bash. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- extracted_path: `{{RUN_DIR}}/extracted_completion.json`

## Goal

Read `{{RUN_DIR}}/extracted_completion.json`. If `errors` is non-empty, SKIP execution and record `skipped_due_to_extract_error`. Otherwise run the bash one-liner under `subprocess.Popen(start_new_session=True)` with a **streaming** 100KB stdout/stderr cap each (bytes-not-text: `text=False`, decode after cap). Capture exit_code, stdout, stderr, duration_ms, timed_out, truncated, skipped flags.

Run with `python3 -c "..."` (or write to a temp file then `python3 <file>`) from the assemble repo root — the harness sets that as CWD. `python3` + stdlib only for the wrapper logic; the inner `subprocess.Popen` invokes bash for the completion command. Process-group kill on timeout (Codex retro F2/F3 mitigation): `start_new_session=True` puts bash in its own process group so `os.killpg(SIGKILL)` terminates the whole group, preventing `bash -c 'cmd &'` from surviving past the timeout and yielding a false-positive verdict=PASS.

**FIX-1 (T3 closure)**: The cap is enforced DURING read via a `select.select` non-blocking streaming loop + per-stream cumulative byte counter. The child process is killed immediately (process-group SIGKILL) when either stream hits 100KB. Wrapper RAM bound = 200KB (CAP_BYTES × 2 streams) regardless of completion output size. Prior to FIX-1, `subprocess.run` / `Popen.communicate` (blocking, timeout=30) read all output into RAM before the cap fired — a 10GB stream could OOM the sub-agent (SECURITY.md T3). The streaming approach eliminates that risk.

```python
import json, subprocess, time, os, signal, select
from pathlib import Path

extracted_path = Path("{{RUN_DIR}}/extracted_completion.json")
extracted = json.loads(extracted_path.read_text(encoding="utf-8"))

CAP_BYTES = 100_000   # per-stream cap (stdout + stderr each); wrapper RAM ≤ 200KB
TIMEOUT_S = 30        # wall-clock timeout=30s; exit_code=124 on expiry

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
    stdout_buf = bytearray()
    stderr_buf = bytearray()
    truncated = False
    timed_out = False
    exit_code = None

    try:
        # text=False — we read bytes directly to control byte-counting.
        # Decoding to str happens AFTER the cap-bounded buffers are finalized,
        # so a 10GB stream cannot OOM the wrapper (FIX-1 / T3 closure).
        # start_new_session=True puts bash in its own process group so we can
        # kill the whole group on timeout (Codex retro F2/F3: `bash -c 'cmd &'`
        # would otherwise exit 0 leaving the backgrounded process alive,
        # yielding a false-positive verdict=PASS).
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        def _kill_group():
            """Kill the entire process group (Codex retro F2 mitigation)."""
            if proc is not None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

        # Non-blocking streaming read loop (select.select, POSIX, stdlib only).
        # Each iteration: select on live pipes with a short timeout, read up to
        # min(room, 4096) bytes from any ready stream, then check process status.
        # Stops when: (a) both streams EOF + process exited, (b) wall-clock
        # TIMEOUT_S exceeded, or (c) both streams have hit CAP_BYTES.
        eof = {proc.stdout: False, proc.stderr: False}
        streams = {proc.stdout: stdout_buf, proc.stderr: stderr_buf}

        while True:
            elapsed = time.monotonic() - t0
            if elapsed >= TIMEOUT_S:
                timed_out = True
                _kill_group()
                exit_code = 124  # GNU coreutils `timeout(1)` standard
                # Drain residual bytes from OS pipe buffer (bounded by CAP_BYTES).
                for stream, buf in streams.items():
                    if not eof[stream]:
                        try:
                            while True:
                                room = CAP_BYTES - len(buf)
                                if room <= 0:
                                    break
                                chunk = stream.read(min(room, 4096))
                                if not chunk:
                                    break
                                buf.extend(chunk)
                        except Exception:
                            pass
                        eof[stream] = True
                break

            ready_streams = [s for s, done in eof.items() if not done]
            if not ready_streams:
                # Both EOF — reap exit code.
                remaining = max(0.1, TIMEOUT_S - elapsed)
                exit_code = proc.wait(timeout=remaining)
                break

            ready, _, _ = select.select(
                ready_streams, [], [], min(0.5, TIMEOUT_S - elapsed)
            )
            for stream in ready:
                buf = streams[stream]
                room = CAP_BYTES - len(buf)
                if room <= 0:
                    # Cap already hit on this stream — skip reads.
                    eof[stream] = True
                    continue
                chunk = stream.read(min(room, 4096))
                if not chunk:
                    eof[stream] = True
                    continue
                buf.extend(chunk)
                if len(buf) >= CAP_BYTES:
                    truncated = True
                    eof[stream] = True
                    # Cross-bundle Spike IX Codex retro F2 sync — kill IMMEDIATELY
                    # when EITHER stream caps, not when both. A completion command
                    # flooding stdout only would otherwise stall until TIMEOUT_S
                    # even though further output is being discarded; kill-on-either
                    # bounds the kill latency to one select-loop tick (≤500ms).
                    _kill_group()

            # If process exited and both streams drained, we're done.
            if proc.poll() is not None and all(eof.values()):
                exit_code = proc.returncode
                break

    finally:
        # Defensive: ensure the group is dead if anything went wrong.
        if proc is not None and proc.returncode is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Decode bytes → str AFTER buffers are bounded (FIX-1 invariant).
    # errors="replace" for binary output safety; Codex F4 fenced-block
    # escape happens at report stage, not here.
    stdout = stdout_buf.decode("utf-8", errors="replace")
    stderr = stderr_buf.decode("utf-8", errors="replace")

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

This is the only verifier step that runs the SCOPE-author-provided bash command. Note: prior to Codex retro A8b, this used `subprocess.run` with a single-process timeout kill; migrated to `subprocess.Popen` + `os.killpg` process-group kill (see mitigation 1 below). FIX-1 further replaced blocking `Popen.communicate` (the old timeout=30 path) with a `select.select` streaming loop that enforces the 100KB cap PER BYTE during capture, not after. Mitigations enforced HERE:

1. **Timeout 30s** — Step 2 wraps the bash call in `subprocess.Popen(start_new_session=True)` + streaming read loop with wall-clock `TIMEOUT_S = 30`. On timeout, the whole process group is killed via `os.killpg(SIGKILL)` (Codex retro F2/F3 — prevents `bash -c 'cmd &'` from surviving past timeout). exit_code=124 (GNU coreutils convention), `timed_out: true` recorded.
2. **Output cap 100KB — streaming guarantee (FIX-1)** — both stdout and stderr individually capped at CAP_BYTES = 100_000 via a per-stream byte counter inside the `select.select` read loop. Child is killed (process-group SIGKILL) immediately when either stream hits the cap. `truncated: true` recorded if either trips. **Wrapper RAM bound = 200KB** (CAP_BYTES × 2 streams) regardless of completion output size. Prior approach (blocking `Popen.communicate`, timeout=30) buffered all output in RAM before trimming — a 10GB stream OOMed the wrapper (T3). Streaming eliminates this (SECURITY.md T3 MITIGATED).
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

- Bash tool **only** for the completion subprocess invocation (via the python `subprocess.Popen` + streaming `select.select` loop). Do NOT explore the run_dir with ad-hoc shell commands. Do NOT use Bash for `cat` / `ls` / etc.
- Do NOT modify run_dir from the wrapper python beyond writing `execution_result.json`. The bash command itself MAY touch the filesystem (including run_dir) per SCOPE author's discretion — the security model trusts the SCOPE author for side-effects within the bash one-liner.
- Do NOT redact, sanitize, or transform stdout/stderr — preserve verbatim (capped only).
- Do NOT echo stdout content into your final WROTE message — orchestrator parses ONLY the WROTE: regex.
- ensure_ascii=False — Korean characters in stdout/stderr (e.g. test output, error messages in Korean) must round-trip.

## Save

Write JSON via Python `json.dumps(..., indent=2, ensure_ascii=False)`. Print `WROTE: <absolute path>` and exit.
