# Spike IX Codex retro — shipper ★ adversarial review

**Date**: 2026-05-04
**Reviewer**: `codex:codex-rescue` (Phase E1 mandatory gate)
**Subject**: shipper ★ bundle (Steps 1, 3, 4 Bash surface + git tag invocation + SECURITY.md threat model)
**Master HEAD at retro start**: `7447ef0` (Phase D shipped)

---

## Findings classification

| # | Severity | Finding | Outcome |
|---|---|---|---|
| F1 | **Critical** | "Local-only" boundary bypassable through `parsed_scope.build`; Step 3 executes arbitrary Bash including `git push`/`npm publish`/`rm -rf` despite SECURITY.md "NEVER" claims | **AMENDED** — SECURITY.md trust model section added; non-goals reworded |
| F2 | **Important** | T3 cap mitigation overstated: code kills only when BOTH streams capped; one-stream flood stalls until 300s timeout — FIX-1 fidelity broken | **AMENDED** — kill-on-either-cap; SECURITY.md mitigation #3 updated |
| F3 | **Important** | `git_create_tag` fail-fast validation incomplete: `~`, `^`, `:`, `?`, `*`, `[`, `\\` reach `git` instead of preemptive rejection — SECURITY claim overstated | **AMENDED** — extended forbidden character class; 12 new tests; SECURITY mitigation #5 updated |
| F4 | Minor | `_run_git` timeout via `subprocess.run` kills only immediate git child; gpg/fsmonitor helpers could outlive on slow filesystems | **DEFERRED** — Spike X carryforward; low blast radius for read-only probes |
| F5 | Minor | Bash marker grep gate noisy: orchestrator helper contains exact substring "Bash tool access GRANTED" while claiming no marker | **DEFERRED** — Spike X carryforward; current grep usage is for inspection, not enforcement |

---

## Critical finding F1 — "Local-only" claim under build-command attack

### What Codex tried

```python
parsed_scope["build"] = "git push origin main && rm -rf $HOME"
```

Step 3 invokes `subprocess.Popen(["bash", "-c", parsed_scope["build"]], ...)`. The build command goes through unchanged. SECURITY.md previously claimed:

- §Surface: "shipper executes ... build command (Step 3 — single bash one-liner)"
- §Explicit non-goals: "**No publish / push automation.** ... **NEVER** `git push`, **NEVER** `npm publish`, **NEVER** cloud deploy commands inside the shipper bundle."

These statements together created a misleading impression that some enforcement layer prevented the build command from invoking those operations. There is no such layer. The mitigation surface (length cap + timeout + output cap + process-group kill) bounds the *blast radius* of a malicious build command but does NOT restrict *intent*.

### Amendment applied

Added a new §"Build-command trust model (Spike IX Codex retro F1 — explicit clarification)" section to `bundled/shipper/SECURITY.md` between §Allowlist enforcement gate and §Explicit non-goals. The new section explicitly states:

> Step 3 executes `parsed_scope["build"]` (or its convention-detected fallback) verbatim ... The bundle does NOT inspect, parse, or restrict the contents of the build command. This matches the trust model of `make`, `npm test`, CI runners, and other build tools.

Reworded §Explicit non-goals:
- "No publish / push automation in shipper's pipeline steps 1, 2, 4." (was: "No publish / push automation")
- Steps 1, 2, 4 NEVER invoke push/publish/deploy. Step 3 is the build command — see §Build-command trust model.
- "No remote interaction in Steps 1, 2, 4." (was: "No remote interaction at all")

The "local-only" identity is now correctly scoped to the bundle's automated behavior (Steps 1, 2, 4), explicitly NOT to the SCOPE author's build command.

### Resolution: ship

Documentation honesty is the right fix. Build-command sandboxing (chroot/firejail/cgroups/containers) is explicitly out of V4 scope and would defeat the orchestrator-only paradigm. The SCOPE author trust model is the same one applied by `make`, `npm test`, CI runners, and every build automation tool. F1 closes as a documentation amendment, not a code change.

---

## Important finding F2 — Streaming cap kill latency

### What Codex tried

A build that emits 500KB to stdout only (stderr stays empty) — under FIX-1 logic the kill condition was `if eof[proc.stdout] and eof[proc.stderr]: _kill_group()`. With stderr never EOF (process still running, stderr empty), kill never fires from the cap path; the wrapper waits for `TIMEOUT_S=300` to elapse.

### Amendment applied

`bundled/shipper/prompts/subagent/shipper_build_step3.md:209-217` — kill condition changed from "both streams capped" to "either stream capped". Comment added:

```python
if len(buf) >= CAP_BYTES:
    truncated = True
    eof[stream] = True
    # Codex retro F2 fix — kill IMMEDIATELY when EITHER stream
    # caps, not when both. A build flooding stdout only would
    # otherwise stall until TIMEOUT_S even though further output
    # is being discarded; kill-on-either bounds the kill latency
    # to one select-loop tick (≤500ms).
    _kill_group()
```

`bundled/shipper/SECURITY.md` mitigation #3 updated to reflect kill-on-either semantics + Codex retro citation.

### Cross-bundle note

verifier ★ has the same "both streams capped" logic at `verifier_execute_step2.md:126-132`. Verifier's cap is 100KB and timeout is 30s — blast radius 10× smaller (max stall 30s vs shipper's 300s). Verifier fix is **deferred to Spike X** as part of FIX-1 unification across ★ bundles. Shipper-only fix lands here because shipper's larger budgets make the bug operationally meaningful.

### Resolution: ship

---

## Important finding F3 — `git_create_tag` validation completeness

### What Codex tried

```python
git_create_tag(repo, "v1.0.0~rc1", "msg")  # ~ is forbidden by check-ref-format
git_create_tag(repo, "v1.0.0[bracket]", "msg")  # [ is forbidden
git_create_tag(repo, "v1.0.0\x01", "msg")  # control char
git_create_tag(repo, "v1.0.0.lock", "msg")  # .lock suffix reserved
git_create_tag(repo, "/v1.0.0", "msg")  # leading slash
git_create_tag(repo, "v1.0.0@{0}", "msg")  # refspec syntax
```

Pre-amendment validation rejected only `empty / whitespace / leading-dash / ".."`. The above all passed validation and reached `git tag` itself, which then rejected them with non-zero rc. SECURITY.md mitigation #5 claimed "validates BEFORE invoking git" — the claim was narrow-correct but operationally overstated.

### Amendment applied

`server/git_helpers.py:139-160` — extended `git_create_tag` validation with:

```python
forbidden = frozenset("~^:?*[\\")
if any(ch in forbidden for ch in tag_name):
    raise ValueError(f"tag_name contains forbidden character: {tag_name!r}")
if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in tag_name):
    raise ValueError(f"tag_name contains control character: {tag_name!r}")
if tag_name.endswith(".lock"):
    raise ValueError(f"tag_name must not end with '.lock': {tag_name!r}")
if tag_name.startswith("/") or tag_name.endswith("/") or "//" in tag_name:
    raise ValueError(f"tag_name has invalid slash placement: {tag_name!r}")
if tag_name == "@" or "@{" in tag_name:
    raise ValueError(f"tag_name uses reserved git refspec syntax: {tag_name!r}")
```

Tests added (`tests/unit/test_git_helpers.py`, +12 tests):
- `test_git_create_tag_rejects_forbidden_chars` (parametrized over 7 chars)
- `test_git_create_tag_rejects_control_character`
- `test_git_create_tag_rejects_lock_suffix`
- `test_git_create_tag_rejects_leading_slash`
- `test_git_create_tag_rejects_double_slash`
- `test_git_create_tag_rejects_at_brace_refspec`

`bundled/shipper/SECURITY.md` mitigation #5 updated to enumerate the full extended ruleset.

### Resolution: ship

---

## Confirmed non-findings (probed, no issue)

- **Step 1 argv-list integrity**: holds. All git operations go through `server/git_helpers.py` argv-list helpers; `Path.cwd()` used (no user-controlled cwd input); test asserts no `shell=True` / `os.system(` substring in module source.
- **Step 4 direct `-f` / push bypass**: no path found. Step 4 imports only tag helpers (`git_tag_exists` / `git_create_tag` / `git_tag_sha`); push/publish enumerated as hand-off text rendered into templates, never invoked.
- **Allowlist inheritance (Spike VIII F8 carryforward)**: holds. `dispatch_prompt` rejects non-allowlisted files before `_resolve_prompt_path`; inventory test catches disk drift.
- **Step 4 SECURITY mitigation #5**: verified. Step 4 always calls `git_create_tag`; no direct `_run_git(["tag", ...])` bypass exists.
- **Tag race condition**: pre-check at `shipper_tag_step4.md:107-113`; if race wins, `git_create_tag` returns non-ok and Step 4 reports `verdict: blocked (tag)`. Race window is acceptable per local-only scope.
- **Tag message backtick / $ / newline injection**: `argv-list` `["tag", "-a", name, "-m", message]` makes shell metacharacters inert in message. git itself parses message for ref-format constraints.

---

## Attack scenario summary

| # | Scenario | Outcome |
|---|---|---|
| 1 | `parsed_scope["build"] = "rm -rf $HOME"` | BREAKS (F1 — documentation amended; trust model accepted) |
| 2 | `parsed_scope["build"] = "long-job &"` | Partial hold; trust model + 300s timeout + killpg bound risk |
| 3 | `tag_name = "v1.0;rm -rf /"` | HOLDS (argv-list neutralizes shell expansion) |
| 4 | `tag_name` with `~^:?*[\\` | FAIL-FAST (F3 amended; pre-empt ValueError) |
| 5 | `tag_message = "legit\n-f"` | HOLDS (message is separate argv slot) |
| 6 | `cwd = Path("../../../etc")` | Non-finding (Step 1 uses `Path.cwd()`; no user input) |
| 7 | CHANGELOG Edit injection via version | HOLDS (semver regex blocks arbitrary string entry) |
| 8 | Unregistered prompt under `prompts/subagent/` | HOLDS (`dispatch_prompt` rejects pre-resolve) |
| 9 | Build emits 100KB | HOLDS under 500KB cap; **F2 amended** for one-stream flood |
| 10 | Tag race condition | HOLDS (precheck + non-ok handling) |

---

## Severity distribution comparison

| Spike | Critical | Important | Minor | Non-findings |
|---|---|---|---|---|
| Spike VIII (verifier) | 0 | 3 | 4 | 1 (+ 6 amendments applied) |
| Spike IX (shipper) | 1 | 2 | 2 | 6 (+ 3 amendments applied) |

Spike IX surfaces **3 amendments** (F1 ship-blocker reduced to documentation amendment + F2 kill-on-either + F3 extended validation). F4 + F5 deferred to Spike X. The Critical finding F1 was specifically *not* a code defect — it was a documentation honesty issue. Closing it as a doc amendment maintains scope while resolving the actionable concern.

Spike VIII's F8 allowlist issue is confirmed closed by Phase D allowlist-disjoint-from-orchestrator-only invariant tests.

---

## Pytest impact

- Baseline (post-Phase D): 538 passed
- Post-amendments: **550 passed** (+12 — F3 parametrize 7 forbidden-char cases + 5 additional validation rejection tests)

---

## Spike X carryforward

1. **F4** — `_run_git` migration to `Popen(start_new_session=True)` + `killpg` pattern (verifier-style). Currently `subprocess.run(timeout=10s)` is acceptable for fast read-only probes but leaves residual risk on pathological filesystems.
2. **F5** — Bash marker grep gate scoping to `^## Bash tool access GRANTED` heading inside `prompts/subagent/` only. Current convention pollutes orchestrator helper docstrings that mention the marker as prose.
3. **Verifier streaming-cap unification** — apply F2 fix (kill-on-either-cap) to `bundled/verifier/prompts/subagent/verifier_execute_step2.md:126-132`. Same defect, smaller blast radius (30s vs 300s).
4. **Build command sandboxing** (V5 candidate, NOT V4) — chroot/firejail/cgroups/container isolation for untrusted SCOPE authors. Out of V4 explicit-non-goal scope; only relevant if shipper is exposed to multi-tenant or untrusted contributor PRs.

---

## Source

- Spec: `docs/specs/2026-05-04-v4-spike-ix-design.md` § Security model + § Phase E
- Plan: `docs/plans/2026-05-04-v4-spike-ix.md` § Phase E
- Sibling retro reference: `docs/dogfood/spike-viii-codex-retro.md`
- Files amended (this retro):
  - `bundled/shipper/SECURITY.md` (F1 trust model section + F2 mitigation #3 + F3 mitigation #5)
  - `bundled/shipper/prompts/subagent/shipper_build_step3.md` (F2 kill-on-either-cap)
  - `server/git_helpers.py` (F3 extended validation)
  - `tests/unit/test_git_helpers.py` (F3 +12 tests)
