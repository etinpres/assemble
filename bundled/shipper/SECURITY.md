# shipper ★ — Security model

## Surface

shipper's Bash surface is **larger than verifier ★** (3 of 4 dispatched steps grant Bash vs 1 of 4). Concretely:

- **Step 1 — read-only git probes** (`bundled/shipper/prompts/subagent/shipper_preflight_step1.md`). Bash invokes `python3` only; all git calls go through `server.git_helpers` argv-list wrappers (`git_status_porcelain`, `git_head_sha`, `git_branch`). NO direct `git` CLI.
- **Step 2 — Edit/Write only** (`shipper_version_step2.md`). NO Bash. Mutates the version file (VERSION / package.json / pyproject.toml) + `CHANGELOG.md` exclusively via the Edit/Write tools. This is the only Bash-free step in shipper.
- **Step 3 — single build command** (`shipper_build_step3.md`). One bash one-liner from `parsed_scope.build`, executed via `subprocess.Popen(start_new_session=True)` with TIMEOUT_S=300, per-stream CAP_BYTES=500_000 streaming cap, process-group SIGKILL on timeout or cap-hit. Spike VIII verifier FIX-1 streaming pattern inherited (10× timeout, 5× cap).
- **Step 4 — local annotated tag creation** (`shipper_tag_step4.md`). `git tag -a <name> -m <message>` via `server.git_helpers.git_create_tag` argv-list wrapper. NEVER `-f`, NEVER `git push`, NEVER any remote interaction.

The `Bash tool access GRANTED` substring marker (Spike VIII convention) appears in Steps 1, 3, 4 prompt bodies as the canonical grep target for security audits.

## Threat model

| # | Threat | Severity | Mitigation |
|---|---|---|---|
| T1 | Malicious SCOPE author injects destructive build payload (`rm -rf`, `> /dev/sda`) | low-med | length cap 500 on `build` field (`_BUILD_MAX_LEN` in `server/scope_parser.py:58`); SCOPE author trust scope = repo owner / equivalent trusted principal; same model as `make`/`npm test`. Untrusted contributors (open-source PRs adding SCOPE.md) introduce supply-chain risk equivalent to merging untrusted CI scripts. |
| T2 | Runaway build blocks pipeline | medium | `subprocess.Popen(start_new_session=True)` + streaming `select.select` read loop with TIMEOUT_S=300; on timeout, full process group killed via `os.killpg(SIGKILL)` (Codex retro F2/F3 inheritance — prevents `bash -c 'cmd &'` from surviving past timeout). exit_code=124 (GNU coreutils convention), `timed_out: true` recorded. |
| T3 | Build output flood saturates RAM (e.g. `yes \| head -c 10G`) | medium | **MITIGATED** — streaming read with per-stream byte counter inside `select.select` loop; child killed (process-group SIGKILL) immediately when either stream hits CAP_BYTES=500_000. Wrapper RAM bound = 1MB (CAP_BYTES × 2 streams). FIX-1 inheritance, 5× verifier cap. |
| T4 | Build artifact dropped in unexpected location | low | shipper does not consume build output paths — only exit code + bounded stdout/stderr capture. Artifact placement is build-tool's concern, surfaced in SHIP_REPORT §Hand-off, not auto-uploaded. |
| T5 | `git tag` collides with existing tag | medium | Step 4 pre-checks `server.git_helpers.git_tag_exists(cwd, tag_name)` BEFORE creating; collision aborts with `verdict: blocked (tag)` and renders the abort template. |
| T6 | `git tag -f` overwriting existing tag | high | Step 4 prompt body explicitly forbids `-f` / `--force`. `server.git_helpers.git_create_tag` always invokes `git tag -a` (annotated, no force). Harness preamble v3 surgical-changes rule reinforces. |
| T7 | Tag pushed to remote unintentionally | high | Step 4 prompt body explicitly forbids ANY form of `git push` / `git fetch` / `git pull`. SHIP_REPORT §Hand-off documents `git push origin <tag>` as a user-owned next-step command, never auto-invoked. |
| T8 | Pre-flight Bash escape (`git status; rm -rf /`) | high | Step 1 uses argv-list invocation only via `server.git_helpers.*` (`subprocess.run(["git", *args], shell=False)`). NO `shell=True`, NO string interpolation, NO `os.system`. argv-list grep gate test (`test_module_has_no_shell_true_or_os_system`) asserts source-level invariant. |
| T9 | Pre-flight reads outside repo | low | git probes scoped to `cwd` (assemble repo or run_dir parent). Cross-repo workflows (Step 1 probing repo A while Step 4 tagging repo B) are explicitly NOT supported in V4 — single-repo invariant. |

## Mitigations enumerated

1. **Length cap 500** — Step 1 enforces on `parsed_scope.build` field. Schema cap is `_BUILD_MAX_LEN = 500` in `server/scope_parser.py:58`; oversize inputs surface as `build-too-long` error label and Step 3 skips execution.
2. **Timeout 300s** — Step 3 wraps build in `subprocess.Popen(start_new_session=True)` + streaming `select.select` loop with `TIMEOUT_S=300` (`bundled/shipper/prompts/subagent/shipper_build_step3.md:43`). On timeout, full process group killed via `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)`. exit_code=124, `timed_out: true` recorded. Verifier FIX-1 inheritance with 10× timeout.
3. **Output cap 500KB streaming** — Step 3 per-stream byte counter (`CAP_BYTES = 500_000`, line 42) inside the `select.select` loop. Child killed (process-group SIGKILL) immediately when **either** stream hits cap (Spike IX Codex retro F2 fix — kill latency bounded to one select-loop tick ≤500ms regardless of which stream floods). Wrapper RAM bound = 1MB regardless of build output size (a 10GB build log cannot OOM the sub-agent). FIX-1 inheritance with 5× verifier cap.
4. **argv-list git invocation** — `server/git_helpers.py` ALL functions use `subprocess.run(["git", *args], shell=False)`. NO string command construction, NO `os.system`. Grep-gate test asserts NO `shell=True` / `os.system(` substring in module source.
5. **`git tag -a` only, NEVER `-f`** — Step 4 prompt body explicitly forbids `-f` / `--force` flags. `server.git_helpers.git_create_tag` validates `tag_name` BEFORE invoking git (Spike IX Codex retro F3 — extended ruleset rejects empty / whitespace / leading-dash / `..` substring / git check-ref-format forbidden chars `~^:?*[\\` / control chars / `.lock` suffix / leading-or-trailing slash / double-slash / `@`/`@{` refspec syntax with `ValueError`), then runs `git tag -a <name> -m <message>` only. Even though argv-list invocation already neutralizes shell metacharacters, the extended ruleset gives callers a deterministic exception path (instead of git's non-zero rc) for the full forbidden character class.
6. **NEVER `git push`** — Step 4 prompt body forbids ANY remote operation (`push`, `fetch`, `pull`). SHIP_REPORT §Hand-off documents push as a user-owned next-step command; the shipper bundle never auto-invokes it.
7. **Bash scoped to Steps 1, 3, 4** — Step 2 sub-agent does NOT receive Bash tool access (Edit/Write only). The `ALLOWED_PROMPT_FILES` allowlist in `server/harness.py` enumerates exactly 4 shipper subagent prompts; non-allowlisted dispatch raises `ValueError` (Spike VIII allowlist mechanism).
8. **Orchestrator-only main** — main Claude does NOT call Bash directly during the dispatch chain. Main only dispatches sub-agents. (V4 #9 invariant + Spike VIII enforcement; verified via `dispatches.jsonl` introspection in B-14 dogfood AC10.)

## Allowlist enforcement gate

`server.harness.ALLOWED_PROMPT_FILES` (frozenset) is enforced at `dispatch_prompt(prompt_file)` call time, NOT at `_resolve_prompt_path(prompt_file)` resolution time. Concretely:

- **`dispatch_prompt`** — checks the allowlist; raises `ValueError` if `prompt_file` is not in the frozenset. This is the gate for sub-agent dispatch (Bash grant goes through this).
- **`_resolve_prompt_path`** — does filesystem lookup only; iterates ALL bundles' `prompts/subagent/` dirs and returns the first match. Does NOT check the allowlist. This is intentional for orchestrator helpers loaded by main directly.

**Implication** (Codex retro F8 inheritance): a new prompt file added to any `prompts/subagent/` directory is resolvable by `_resolve_prompt_path` regardless of allowlist status. Such a file would only receive Bash access if dispatched via `dispatch_prompt`, which DOES check the allowlist. Filesystem placement (controlled by repo write access) is the secondary gate.

`shipper_iter_revisit.md` is intentionally outside `ALLOWED_PROMPT_FILES` because it is an orchestrator helper loaded by main (not a sub-agent dispatched prompt). Its placement under `prompts/orchestrator/` (not `prompts/subagent/`) further documents this distinction. It is registered in `ORCHESTRATOR_ONLY_PROMPTS` (Spike VIII Pre-IX FIX-3 contract).

## Build-command trust model (Spike IX Codex retro F1 — explicit clarification)

Step 3 executes `parsed_scope["build"]` (or its convention-detected fallback) verbatim via `subprocess.Popen(["bash", "-c", build_cmd], ...)`. **The bundle does NOT inspect, parse, or restrict the contents of the build command.** This matches the trust model of `make`, `npm test`, CI runners, and other build tools: the SCOPE author authors the build command, and the SCOPE author owns its consequences.

Concretely, this means:
- A SCOPE author MAY include `git push`, `npm publish`, `cargo publish`, `kubectl apply`, or any other side-effecting command in `parsed_scope["build"]`. Step 3 will execute it.
- A SCOPE author MAY include destructive shell (`rm -rf $HOME`, `:(){:|:&};:`, etc.). Step 3 will execute it.
- Length cap (≤500 chars) + 300s timeout + 500KB stream cap + process-group SIGKILL bound the *blast radius* but do NOT restrict *intent*.

Shipper's "local-only" identity refers to the **bundle's own automated behavior** — Step 1 (read-only git probes), Step 2 (Edit-only version/CHANGELOG), and Step 4 (`git tag -a`, NEVER `-f`, NEVER `push`) — not to whatever the SCOPE author chose to put in their build command. The SHIP_REPORT §Hand-off section enumerates explicit user-owned next steps for clarity, but it does NOT promise that no remote interaction occurred during Step 3.

If your threat model requires sandboxing the build command (untrusted SCOPE authors, supply-chain risk on shared CI), use OS-level isolation (chroot / firejail / cgroups / containers) outside the bundle. V4 explicitly does NOT provide this.

## Explicit non-goals

- **No publish / push automation in shipper's pipeline steps 1, 2, 4.** SHIP_REPORT §Hand-off documents `git push origin <branch> && git push origin <tag>`, `npm publish`, `python -m twine upload`, App Store / Play Console upload, gstack `/land-and-deploy` chain — all as user-owned next steps. Steps 1, 2, 4 NEVER invoke push, publish, or deploy. (Step 3 is the build command — see § Build-command trust model above.)
- **No multi-language version bumping** — only the 3 most common formats (VERSION / package.json / pyproject.toml) are detected by `server.version_helpers`. Cargo / Gem / Composer / etc. fall back to manual user edit before invoking shipper.
- **No remote interaction in Steps 1, 2, 4.** Step 1 git probes are read-only; Step 4 specifically forbids `git push`, `git fetch`, `git pull`. The annotated tag is local-only. Pushing it is the user's deliberate decision.
- **No `git tag -f` overwrite path** — duplicate tag → abort with `verdict: blocked (tag)`. User manually deletes the stale tag (`git tag -d`) or bumps the version before retrying.
- **No sandboxing (chroot/firejail/cgroups/namespaces)** — out of V4 scope. Steps 1, 3, 4 run with the same OS-level privileges as the rest of the dispatch chain.
- **No secret scrubbing** — SCOPE author's responsibility to keep secrets out of `## Build` commands and CHANGELOG entries (same convention as commit messages).
- **No shell metacharacter denylist.** Denylists leak. argv-list invocation (Step 1, Step 4) + cap+timeout+author-trust (Step 3) matches the trust model of CI runners and build tools.

## Known limitations

### T6 — Detached process timeout bypass (low residual risk, partially mitigated)

`start_new_session=True` + `os.killpg(SIGKILL)` in Step 3's timeout / cap-hit handler kills the entire process group, addressing `&` background operator, `nohup`, `disown`, `setsid`, `setpgrp` variants. Remaining un-mitigated bypasses:

- **`at now` / `crontab`** — schedules work for future execution via system daemons (`atd`, `cron`); these run outside shipper's process group entirely. NOT mitigated. Acceptable risk under SCOPE author trust model.
- **`systemd-run --user`** — spawns under a different cgroup. NOT mitigated. Acceptable risk.

Full process isolation (cgroups, namespaces) would be required to close these — out of V4 scope.

### Cross-repo workflows

`cwd` is assumed to be the assemble repo or whatever orchestrator launched from. Cross-repo flows (Step 1 probing one repo while Step 4 tagging another) are NOT supported. Single-repo invariant. SCOPE author specifying a `git_repo` field for cross-repo workflows is explicitly deferred to Spike X.

## Codex retro gate

Spike IX Phase E (MANDATORY per user directive on security-sensitive publish/push surface) dispatches `codex:codex-rescue` for adversarial review of:

- Threat table T1–T9 completeness vs the actual Step 1/3/4 prompt bodies and `server.git_helpers` source.
- Step 1 argv-list git invocation surface (T8 — confirm no `shell=True` / no string concat / no `os.system`).
- Step 3 streaming Popen pattern (T2/T3 — verify FIX-1 fidelity: TIMEOUT_S=300, CAP_BYTES=500_000, process-group SIGKILL).
- Step 4 `git tag` invocation (T5/T6/T7 — confirm no `-f`, no `push`, no remote interaction).
- SECURITY.md hand-off boundary completeness (no implicit publish path).

Findings either close as documented "non-goal" (amend §Explicit non-goals) or amend code/SECURITY.md before B-14 ship. The `Bash tool access GRANTED` substring marker is the canonical grep target — Codex verifies presence in Steps 1, 3, 4 prompt bodies and absence in Step 2.
