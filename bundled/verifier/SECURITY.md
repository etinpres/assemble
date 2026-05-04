# verifier ★ — Security model

## Surface

verifier executes `parsed_scope.json.completion` (one-line bash) inside a sub-agent dispatched by main Claude. SCOPE.md author writes that string; sub-agent runs it. This is the first ★ bundle to grant Bash tool access.

## Threat model

| # | Threat | Severity | Mitigation |
|---|---|---|---|
| T1 | Malicious SCOPE author injects destructive payload (`rm -rf`, `> /dev/sda`) | low | length cap (500), runner trust model — same as `make`/`npm test`. **Trust scope**: SCOPE author = repo owner / equivalent trusted principal. Untrusted contributors (e.g., open-source PRs adding SCOPE.md) introduce supply-chain risk equivalent to merging untrusted CI scripts; SCOPE author trust does NOT auto-extend to untrusted parties. |
| T2 | Runaway completion blocks pipeline | medium | `subprocess.Popen(start_new_session=True)` + `communicate(timeout=30)` + `os.killpg(SIGKILL)` on timeout |
| T3 | Output flood saturates RAM during capture (e.g. `yes | head -c 10G`) | medium | **NOT FULLY MITIGATED** — see § Known limitations |
| T4 | Output flood saturates disk via final JSON write | low | 100KB stdout/stderr cap on the captured + persisted result |
| T5 | Network exfiltration of run_dir contents | low | length cap forces minimal payload; SCOPE author trust |
| T6 | Detached-process timeout bypass (`nohup cmd &`, `disown`) | low | NOT MITIGATED — `subprocess.run(timeout=30)` only kills the immediate child; document as known limitation |

## Mitigations enumerated

1. **Length cap** — Step 1 (`verifier_extract_step1.md`) rejects `len(completion) > 500`. Records `completion-too-long` error label; Step 2 skips execution.
2. **Timeout** — Step 2 wraps the bash call in `subprocess.Popen(start_new_session=True)` + `communicate(timeout=30)`. On timeout, the whole process group is killed via `os.killpg(SIGKILL)` (Codex retro F2/F3 — prevents `bash -c 'cmd &'` from surviving past timeout). exit_code=124 (GNU coreutils convention), `timed_out: true` recorded.
3. **Output cap (post-hoc)** — Step 2 truncates stdout + stderr to 100KB EACH after the subprocess returns. `truncated: true` flag recorded if either trips. **CAUTION**: this is a post-hoc trim of an in-memory capture. See § Known limitations.
4. **Skip-if-errors** — if Step 1 reports any errors, Step 2 SKIPS execution entirely. Records `skipped: true` + `skip_reasons: [...]` (full label array) + `skip_reason: <first label>` (convenience scalar).
5. **Bash scoped to Step 2 only** — Steps 1, 3, 4 sub-agents do NOT receive Bash tool access in their dispatched prompts. The `ALLOWED_PROMPT_FILES` allowlist in `server/harness.py` enumerates exactly 4 verifier prompts; non-allowlisted dispatch raises. Harness preamble v3 still applies.
6. **Orchestrator-only main** — main Claude does NOT call Bash directly during the dispatch chain. Main only dispatches Step 2 sub-agent. (Verified in B-13 dogfood AC10.)

## Allowlist enforcement gate

`server.harness.ALLOWED_PROMPT_FILES` (frozenset) is enforced at `dispatch_prompt(prompt_file)` call time, NOT at `_resolve_prompt_path(prompt_file)` resolution time. Concretely:

- **`dispatch_prompt`** — checks the allowlist; raises `ValueError` if `prompt_file` is not in the frozenset. This is the gate for sub-agent dispatch (Bash grant goes through this).
- **`_resolve_prompt_path`** — does filesystem lookup only; iterates ALL bundles' `prompts/subagent/` dirs and returns the first match. Does NOT check the allowlist. This is intentional for orchestrator helpers (e.g., `verifier_iter_revisit.md` lives in `prompts/orchestrator/` and is loaded by main directly without dispatch_prompt's allowlist check).

**Implication** (Codex retro F8): a new prompt file added to any `prompts/subagent/` directory is resolvable by `_resolve_prompt_path` regardless of allowlist status. Such a file would only receive Bash access if dispatched via `dispatch_prompt`, which DOES check the allowlist. The filesystem placement of new prompt files (controlled by repo write access) is the secondary gate.

`verifier_iter_revisit.md` is intentionally outside `ALLOWED_PROMPT_FILES` because it is an orchestrator helper loaded by main (not a sub-agent dispatched prompt). Its placement under `prompts/orchestrator/` (not `prompts/subagent/`) further documents this distinction.

## Explicit non-goals

- **No shell metacharacter denylist.** Denylists leak. Cap+timeout+output-cap+author-trust matches the trust model of CI runners and build tools.
- **No sandboxing (chroot/firejail/etc.)** — out of V4 scope. Step 2 runs with the same OS-level privileges as the rest of the dispatch chain.
- **No secret scrubbing.** SCOPE author's responsibility to keep secrets out of the completion command (same convention as commit messages).
- **No streaming output cap.** See § Known limitations T3.

## Known limitations

### T3 — Output flood during subprocess capture (medium severity, partial mitigation)

`subprocess.run(capture_output=True, text=True)` reads ALL stdout/stderr into the wrapper python's memory before returning. The 100KB cap is applied AFTER the call returns. A SCOPE author whose completion criterion is `yes | head -c 10G` (legal — single line, ≤500 chars) would OOM the verifier sub-agent before the cap fires.

**Effective bound**: `timeout=30s`. A 30-second `yes | head` would emit roughly 1-3 GB at typical pipe rates — enough to OOM most environments. The cap protects only the on-disk JSON + downstream readers, not the subprocess capture itself.

**Future hardening (Spike IX+)**: switch to `Popen` with line-by-line read + cumulative byte counter, kill the child when cap is hit. Out of scope for Spike VIII.

### T6 — Detached process timeout bypass (low severity, partially mitigated post-Codex retro F2)

**MITIGATED post-Codex retro F2** by `start_new_session=True` + `os.killpg(SIGKILL)` in Step 2's TimeoutExpired handler. This kills the entire process group, addressing the `&` background operator, `setsid`, `setpgrp` variants. Remaining un-mitigated bypasses:

- **`nohup`** — explicitly detaches from controlling terminal but stays in the process group; killpg still kills it. Mitigated.
- **`disown`** — bash builtin that removes a job from the shell's job table; the process stays in the group. Mitigated.
- **`at now` / `crontab`** — schedules work for future execution via system daemons (`atd`, `cron`); these run outside the verifier's process group entirely. NOT mitigated. Acceptable risk under SCOPE author trust model.
- **`systemd-run --user`** — similar to atd/cron — spawns under a different cgroup. NOT mitigated. Acceptable risk.

For `at`/`cron`/`systemd-run` style escapes, full process isolation (cgroups, namespaces) would be required — out of V4 scope.

## Codex retro gate

Spike VIII Task A8 dispatches `codex:codex-rescue` for second-opinion on this threat model + Step 2 prompt body before contracts.json freeze. Findings either close as documented "non-goal" or amend SECURITY.md before A9 tests.

The `Bash tool access GRANTED` substring marker in Step 2 prompt body (`bundled/verifier/prompts/subagent/verifier_execute_step2.md`) is the canonical grep target for security audits.
