# shipper ★ — Iteration revisit (orchestrator helper)

> NOTE: This is an orchestrator helper, NOT a subagent prompt. Main Claude reads this directly when re-shipping is requested after an amendment. NOT loaded via `dispatch_prompt`. Tools are inherited from main Claude's own access — no `Bash tool access GRANTED` marker here.

## When to load this

User revises something after a prior shipper run and asks for re-shipping. Common triggers:
- SCOPE.md amended (e.g. `release_kind` overridden, `build` command corrected, `tag_prefix` set).
- Dirty-tree resolved (commits/stash) after a prior preflight `fail`.
- `verify_result.json` flipped to `pass` after a prior preflight blocked on missing/failed verify.

Re-asking with no amendment is a **no-op** (see §Idempotency).

## Iteration semantics

| Step | Re-run condition |
|---|---|
| Step 1 (preflight) | **always re-run** — git status / verify_result may have changed |
| Step 2 (version) | **only if `release_kind` changed** OR previous Step 2 was skipped due to preflight fail |
| Step 3 (build) | **always re-run** — build artifacts are not idempotent; no caching |
| Step 4 (tag) | **only if Steps 1–3 all PASS** — never re-run a successful tag (collision; abort instead) |

`dispatches.jsonl` row counts per iteration N:
- Standard iteration (release_kind unchanged, build runs, tag created): **3 rows** — `step1.iter{N}.preflight`, `step3.iter{N}.build`, `step4.iter{N}.tag`. (Step 2 skipped — release_kind unchanged.)
- release_kind changed iteration: **4 rows** — all four steps re-dispatched.
- Build-fail iteration: **3 rows** — `step1`, (optional `step2`), `step3`. No `step4` row (Step 4 skipped because `build_result.exit_code ≠ 0`).
- Preflight-fail iteration: **2 rows** — `step1`, `step4` (abort-path render only). Step 2/3 skipped per spec § Step 1 fail behavior.

Each iteration appends `## Iteration N` to SHIP_REPORT.md without overwriting the prior trail (verifier ★ Spike VIII pattern).

## Decision tree (main Claude follows)

```
prior_iter      = highest N from `## Iteration N` headings in SHIP_REPORT.md (0 if none)
new_iter_N      = prior_iter + 1
prior_release   = release_kind from last iteration's parsed_scope.json snapshot (dispatches.jsonl)
current_release = parsed_scope.json.release_kind (current run_dir)

if user supplied no amendment AND no source-of-truth changed:
    # Idempotency
    return existing SHIP_REPORT.md path; record NO new dispatches

dispatch step1.iter{new_iter_N}.preflight   # always

if current_release != prior_release OR prior step2 was skipped:
    dispatch step2.iter{new_iter_N}.version

if preflight.verdict == "fail":
    dispatch step4.iter{new_iter_N}.tag      # abort-path render only, no git tag invocation
    append `## Iteration N` to SHIP_REPORT.md (verdict: blocked (preflight))
    return

dispatch step3.iter{new_iter_N}.build        # always re-run

if step3.build_result.exit_code != 0:
    # Build failed — render abort, do NOT dispatch tag
    append `## Iteration N` to SHIP_REPORT.md (verdict: blocked (build))
    return

# Steps 1–3 all PASS
new_tag = "<tag_prefix><new_version>"
if `git tag -l <new_tag>` returns non-empty:
    # Tag collision — already shipped at prior_sha
    append `## Iteration N` to SHIP_REPORT.md (verdict: blocked (tag))
    return

dispatch step4.iter{new_iter_N}.tag           # creates git tag locally
append `## Iteration N` to SHIP_REPORT.md (verdict: ship-ready)
```

## Audit invariant

Main records each dispatch via `record_dispatch` with iter-suffixed step name. Row count after iteration N must match the table in §Iteration semantics above. Negative test: re-asking without amendment produces zero new rows in `dispatches.jsonl`.

## Tag collision handling

If `<tag_prefix><new_version>` already exists in the repo (typical when prior iteration's Step 4 succeeded), main Claude treats it as already-shipped and does NOT re-dispatch Step 4. Re-dispatching would invoke `git_create_tag`, which fails with rc≠0 since git rejects duplicate tag names without `-f` (and `-f` is forbidden per SECURITY.md T6).

Render abort path with:
- `verdict: blocked (tag)`
- `reason: "already shipped at <prior_sha>; bump version or delete tag to retry"`

User next steps (documented in SHIP_REPORT §Hand-off): bump `release_kind` (e.g. `patch` → `minor`) and re-run, OR `git tag -d <tag>` locally if the prior tag was a mistake.

## Idempotency

Re-asking with no amendments is a **no-op**:
- No new rows in `dispatches.jsonl`.
- No new `## Iteration N` heading appended to SHIP_REPORT.md.
- Main returns the existing SHIP_REPORT.md path with the prior verdict unchanged.

Detection heuristic: SHA256 of current `parsed_scope.json` matches the most recent iteration's recorded `parsed_scope_hash` in `dispatches.jsonl` AND `git rev-parse HEAD` matches the prior iteration's `head_sha` AND `verify_result.json` mtime is unchanged.
