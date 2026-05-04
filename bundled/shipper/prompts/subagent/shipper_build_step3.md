# shipper Step 3 — execute build artifact

You are dispatched as shipper Step 3 sub-agent. **Bash tool access GRANTED for this single step ONLY** — Steps 1, 2, 4 have their own scoped Bash policy (Step 2 is Edit-only, Steps 1 and 4 receive read-only / tag-only Bash respectively). Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`. Multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last match as canonical (helper `server.harness.extract_wrote_paths`).

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`

Required files in run_dir:
- `{{RUN_DIR}}/preflight.json` — pre-flight gate (Step 1 output). If `verdict != "pass"`, this step SKIPS execution.
- `{{RUN_DIR}}/parsed_scope.json` — parsed SCOPE.md (`build` field is consulted first).

## Bash tool access GRANTED

Scope: **ONE build command per dispatch**, executed via `subprocess.Popen(start_new_session=True)` from the wrapper python below. Wall-clock TIMEOUT_S=300, process-group SIGKILL on timeout or cap-hit.

Forbidden in the build command (acceptable risk per `bundled/shipper/SECURITY.md` T6 inheritance — orchestrator-only rule + author-trust model do NOT extend to background-survival tricks that escape the wrapper's process-group kill):

- NO trailing `&` background operator (e.g. `npm run build &`)
- NO `nohup` (e.g. `nohup make all`)
- NO `crontab` / `at` / `systemd-run` / `launchctl` (anything that schedules execution outside this process)
- NO `disown`, NO `setsid` from inside the command (the wrapper already runs `start_new_session=True`; redundant calls confuse the kill path)
- NO `setsid …` chains that re-parent the build to PID 1

The Bash surface is for **build commands** — `npm run build`, `python -m build`, `cargo build --release`, `pytest -q`, etc. The wrapper's process-group kill assumes the entire build tree is reachable from the bash child's pgid; the forbidden constructs break that assumption.

## Streaming Popen pattern (FIX-1, T2/T3 closure)

The cap is enforced **DURING** read via a `select.select` non-blocking streaming loop + per-stream cumulative byte counter. The child process is killed immediately (process-group SIGKILL) when either stream hits CAP_BYTES or wall-clock TIMEOUT_S. **Wrapper RAM bound = 1MB** (CAP_BYTES × 2 streams) regardless of build output size — a 10GB build log cannot OOM the sub-agent.

Inherited verbatim from `bundled/verifier/prompts/subagent/verifier_execute_step2.md` with **larger caps** (5× verifier's 100KB) and **longer timeout** (10× verifier's 30s) to fit legitimate build wall-clock + log-volume profiles.

```python
import json, subprocess, time, os, signal, select
from pathlib import Path

run_dir = Path("{{RUN_DIR}}")
preflight = json.loads((run_dir / "preflight.json").read_text(encoding="utf-8"))
parsed_scope = json.loads((run_dir / "parsed_scope.json").read_text(encoding="utf-8"))

CAP_BYTES = 500_000   # per-stream cap (stdout + stderr each); wrapper RAM ≤ 1MB
TIMEOUT_S = 300       # wall-clock timeout=300s; exit_code=124 on expiry

# ---------- Pre-flight gate ----------
if preflight.get("verdict") != "pass":
    result = {
        "build_command": None,
        "build_command_source": None,
        "exit_code": None,
        "duration_ms": 0,
        "stdout": "",
        "stderr": "",
        "truncated": False,
        "timed_out": False,
        "skipped": True,
        "skip_reason": "preflight not passed",
    }
    out = run_dir / "build_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE: {out}")
    # SystemExit(0): skip-path is terminal — no cleanup hooks below this line.
    # If post-Popen cleanup is added (tempdir teardown, lockfile release), refactor
    # to if/elif/else like verifier_execute_step2.md so skip-paths run finalizers.
    raise SystemExit(0)

# ---------- Build command resolution chain ----------
# Priority: SCOPE → auto package.json → auto pyproject → auto Cargo.toml → fallback pytest (assemble) → skip
build_cmd = None
build_cmd_source = None

scope_build = parsed_scope.get("build")
if isinstance(scope_build, str) and scope_build.strip():
    build_cmd = scope_build.strip()
    build_cmd_source = "scope"
else:
    # Auto-detect via server.version_helpers (PEP 621 / Poetry / package.json / VERSION).
    # NOTE: assemble itself uses VERSION format → falls through to pytest fallback below
    # because assemble has no compile artifact.
    try:
        from server.version_helpers import detect_version_format
        fmt_tuple = detect_version_format(Path.cwd())
        # detect_version_format returns (format, file_path, current_version) or None
        fmt = fmt_tuple[0] if fmt_tuple else None
    except Exception:
        fmt = None

    if fmt == "package.json":
        build_cmd = "npm run build"
        build_cmd_source = "auto-package.json"
    elif fmt in ("pyproject-pep621", "pyproject-poetry"):
        build_cmd = "python -m build"
        build_cmd_source = "auto-pyproject"
    elif fmt == "version-file":
        # Assemble's own use case — no compile artifact, run the test suite.
        # NOTE: this is TEST not BUILD; documented in spec § Step 3 fallback chain.
        build_cmd = "pytest -q"
        build_cmd_source = "fallback-pytest"
    elif (Path.cwd() / "Cargo.toml").is_file():
        # Cargo isn't supported by version_helpers (no auto-bump) but build IS supported.
        build_cmd = "cargo build --release"
        build_cmd_source = "auto-cargo"
    # else: build_cmd stays None → skip path below.

if build_cmd is None:
    result = {
        "build_command": None,
        "build_command_source": None,
        "exit_code": None,
        "duration_ms": 0,
        "stdout": "",
        "stderr": "",
        "truncated": False,
        "timed_out": False,
        "skipped": True,
        "skip_reason": "no build command available",
    }
    out = run_dir / "build_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE: {out}")
    # SystemExit(0): skip-path is terminal — see comment in pre-flight skip block above.
    raise SystemExit(0)

# ---------- Streaming Popen execution ----------
cmd = ["bash", "-c", build_cmd]
t0 = time.monotonic()
proc = None
stdout_buf = bytearray()
stderr_buf = bytearray()
truncated = False
timed_out = False
exit_code = None

try:
    # text=False — bytes-mode read so the byte counter is exact.
    # Decoding to str happens AFTER cap-bounded buffers are finalized,
    # so a 10GB stream cannot OOM the wrapper (FIX-1 / T3 closure).
    # start_new_session=True puts bash in its own process group so we can
    # kill the whole group on timeout (Codex retro F2/F3 inheritance:
    # `bash -c 'cmd &'` would otherwise exit 0 leaving the backgrounded
    # process alive, yielding a false-positive verdict).
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
                # If both streams are capped, kill child to unblock the
                # producer (no point continuing the loop).
                if eof[proc.stdout] and eof[proc.stderr]:
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
# errors="replace" for binary output safety; Korean characters in
# build logs round-trip via ensure_ascii=False on write.
stdout = stdout_buf.decode("utf-8", errors="replace")
stderr = stderr_buf.decode("utf-8", errors="replace")

result = {
    "build_command": build_cmd,
    "build_command_source": build_cmd_source,
    "exit_code": exit_code,
    "duration_ms": duration_ms,
    "stdout": stdout,
    "stderr": stderr,
    "truncated": truncated,
    "timed_out": timed_out,
    "skipped": False,
    "skip_reason": None,
}

out = run_dir / "build_result.json"
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"WROTE: {out}")
```

## Steps

1. **Pre-flight gate** — read `<RUN_DIR>/preflight.json`. If `verdict != "pass"`, write `build_result.json` with `{skipped: true, skip_reason: "preflight not passed", ...}`, emit `WROTE:` line, exit. Steps 2–6 below are NOT executed in the skip path.
2. **Read parsed_scope** — load `<RUN_DIR>/parsed_scope.json` and pull the `build` field.
3. **Resolve build command** (priority order, first hit wins):
   1. `parsed_scope["build"]` if non-empty string → source `scope`
   2. `server.version_helpers.detect_version_format(Path.cwd())`:
      - returns format `package.json` → `npm run build` (source `auto-package.json`)
      - returns format `pyproject-pep621` or `pyproject-poetry` → `python -m build` (source `auto-pyproject`)
      - returns format `version-file` → `pytest -q` (source `fallback-pytest`) — assemble's own case; this is TEST not BUILD because assemble has no compile artifact
   3. Direct check for `Cargo.toml` in `Path.cwd()` (NOT via version_helpers — Cargo auto-bump unsupported but build IS supported) → `cargo build --release` (source `auto-cargo`)
   4. Else → write skip result `{skipped: true, skip_reason: "no build command available"}` and exit
4. **Run streaming Popen** with the resolved command per the FIX-1 pattern above. Capture exit_code, duration_ms, stdout (last 500KB), stderr (last 500KB), truncated flag (if either stream hit cap), timed_out flag.
5. **Write `<RUN_DIR>/build_result.json`** with this schema:
   ```json
   {
     "build_command": "<resolved cmd>",
     "build_command_source": "scope|auto-package.json|auto-pyproject|auto-cargo|fallback-pytest",
     "exit_code": 0,
     "duration_ms": 1234,
     "stdout": "<last 500KB>",
     "stderr": "<last 500KB>",
     "truncated": false,
     "timed_out": false,
     "skipped": false,
     "skip_reason": null
   }
   ```
6. **Emit `WROTE: <abs path>`** and exit.

## Output discipline

- Single trailing `WROTE: <abs path>` line. Orchestrator parses ONLY the WROTE: regex.
- Do NOT echo build stdout/stderr into your final message — they are persisted in `build_result.json`.
- Do NOT add explanatory prose. The wrapper python prints `WROTE:` itself; do not duplicate.
- ensure_ascii=False — Korean / non-ASCII characters in build output round-trip.

## Verdict mapping (informational — classified upstream, not here)

The caller (Step 4 / orchestrator) computes:

```
verdict_step3 = "pass" if (exit_code == 0 OR skipped == True) else "fail"
```

This step does NOT compute or persist a `verdict` field — it only writes the raw signals (`exit_code`, `skipped`, `timed_out`, `truncated`). The deterministic verdict rule is enforced by the orchestrator-side helper that aggregates Steps 1–4 results into the final SHIP_REPORT.md verdict (`ship-ready` / `blocked`).
