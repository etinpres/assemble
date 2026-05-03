# Spike V final readiness — B-10 dogfood PASS, ship

## Result

**13/13 full PASS. Ship.**

B-10 dogfood run `20260503-145104-a531` (add `list_runs(run_dir: Path | None = None) -> list[str]` to `server/run_dir.py` — sorted sub-directory enumeration of the runs root). Iteration 0 only — `verify.sh exit 0` confirmed at Step 5; Step 8 iteration round-trip skipped (no follow-up work). ~7 min wall-clock total across Steps 0–7.

builder ★ bundle's first real-world dogfood run. Linear pipeline executed cleanly; orchestrator dispatched 6 sub-agents (Steps 2–7) with byte-identical preamble sha across all dispatches.

## 13 acceptance criteria — final mapping

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Step 1 Q1/Q2 answered; `TASK_SUMMARY`, `KNOWN_FILES`, `TEST_CMD`, `AC_CMD` collected | ✅ | Inputs serialized into Step 2 dispatch prompt verbatim |
| 2 | `SCOPE.md` non-empty allow/deny/AC/breakdown | ✅ | 1497 B; 2 allow-list entries, 6 deny-list entries, 1 bash AC, 2 numbered sub-tasks |
| 3 | `IMPL_REPORT.md` skeleton 7 sections | ✅ | front matter + Task / Test (red) / Implementation / Verify (green) / Self-review / Commit message / TL;DR |
| 4 | `test_first.sh` exits non-zero before implementation | ✅ | exit 1 with `ImportError: cannot import name 'list_runs'` (precise feature-absent signal) |
| 5 | `## Test (red)` filled in `IMPL_REPORT.md` | ✅ | exit code + first 3 stderr lines captured |
| 6 | `server/run_dir.py` modified with `list_runs()` function | ✅ | `+13 lines` at line 113; signature exactly `list_runs(run_dir: Path | None = None) -> list[str]` |
| 7 | Changes within SCOPE allow-list only | ✅ | git diff --stat: 2 files (`server/run_dir.py` +13, `tests/unit/test_run_dir.py` +43); allow-list hits 2/2 |
| 8 | `verify.sh` exits 0 after implementation | ✅ | exit 0; behavioral verifier (import + call + pytest) |
| 9 | `## Verify (green)` filled — behavioral verifier, not static grep | ✅ | output captures `list_runs() returned: [...]` real call output + pytest 5/5 |
| 10 | `## Self-review` filled — 0 deny-list violations, merge-ready | ✅ | scope check 2/2, deny violations 0, off-allow-list 0; surgical changes confirmed |
| 11 | `## Commit message` filled with conventional commit format | ✅ | `feat(server): add list_runs() to enumerate run directories` + 3-line body |
| 12 | `status: complete` in IMPL_REPORT front-matter | ✅ | line 4: `status: complete` (flipped from `in-progress` by Step 7) |
| 13 | `dispatches.jsonl` 6 rows (Steps 2–7), preamble_sha all v3 byte-identical | ✅ | 6 rows, all `preamble_sha256: 8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`, `preamble_bytes: 1599` |

Plus the audit trail confirms:

- `dispatches.jsonl` 6 entries (step2/3/4/5/6/7), all `prompt_file` matching the builder 7-file allowlist; preamble_sha byte-identical to debugger ★ Spike IV runs (canonical preamble v3 unchanged across spikes).
- `progress.json` 3 stages (plan/execute/verify), default `pending` (B-10 dogfood drove builder pipeline directly without V3 concierge stage marking — concierge auto-recommendation is a separate code path validated in V3 testing).
- `IMPL_REPORT.md` 1845 B final, 7 sections all filled, no `<TBD:` remaining.
- `SCOPE.md` 1497 B, AC bash one-liner: `python3 -c "from server.run_dir import list_runs; print(list_runs())" && echo OK`.
- `test_first.sh` 226 B, `verify.sh` 312 B; both behavioral (run the actual import + call + pytest).

## B-10 dogfood narrative

**Run start (UTC 05:51:04)** — fresh `run_id 20260503-145104-a531` minted via `create_run`. Step 0 (run_dir resolve) implicit; Step 1 (task interview) main-side, 4 inputs prepared:

```
TASK_SUMMARY: server/run_dir.py에 list_runs() 함수 추가...
KNOWN_FILES: server/run_dir.py (수정), tests/unit/test_run_dir.py (신규 추가)
TEST_CMD: pytest tests/unit/test_run_dir.py
AC_CMD: python3 -c "from server.run_dir import list_runs; print(list_runs())"
```

**Step 2 (SCOPE.md + IMPL_REPORT skeleton)** — sub-agent emitted `WROTE: .../IMPL_REPORT.md`. SCOPE.md AC matched the user-provided AC_CMD verbatim (no improvisation). Allow-list correctly narrowed to 2 files; deny-list excluded `bundled/_shared/`, `server/` (other files), `bundled/`, `hooks/`, `config/`, `tests/` (other files) — 6 entries.

**Step 3 (test_first.sh red phase)** — sub-agent wrote test_first.sh with the AC command, ran it, captured exit 1 + `ImportError`. The red signal is precisely "feature missing" rather than "file missing" or "trivial syntax error" — confirming the test is meaningful (anti-pattern caught: not a false-positive red).

**Step 4 (implementation)** — sub-agent edited 2 files within allow-list. `list_runs()` implementation is 13 lines: resolves `run_dir` parameter (default to `_runs_dir()`), checks existence with `is_dir()`, returns `sorted([p.name for p in path.iterdir() if p.is_dir()])` with proper empty-dir/missing-dir/file-only short-circuits. 5 pytest cases cover (a) empty dir, (b) sorted return, (c) files-only short-circuit, (d) injected path, (e) non-existent path. No reformatting of surrounding code (rule 3 preserved).

**Step 5 (verify.sh green phase)** — sub-agent wrote verify.sh with three-layer behavioral check: (1) import, (2) call + assert isinstance list, (3) pytest. exit 0 + stdout shows real return value (current 39 run directories enumerated) + pytest 5/5 PASS. This is the AC=bash cross-cutting pattern in action — the user can re-run `bash verify.sh` interactively without LLM mediation.

**Step 6 (self-review diff vs SCOPE)** — sub-agent ran `git diff --stat HEAD`, parsed against SCOPE allow/deny lists. 2/2 allow-list hits, 0 deny violations, 0 off-allow-list changes, surgical changes preserved. Recommendation: merge-ready.

**Step 7 (commit message + finish)** — `<TBD:` scan returned 0 matches in body sections (all 4 — Test/Implementation/Verify/Self-review — filled). Commit message conventional `feat(server)`. `status: in-progress` → `status: complete`.

**Step 8 (iteration round-trip)** — skipped. No follow-up work; B-10 was a single-task dogfood.

## Spike VI carryforward

Three items surface for follow-up:

1. **`builder_artifact_invariant` contract** (final review Important finding) — spec called for 2 contracts.json entries, plan author substituted iter-audit invariant. The 4-artifact existence guard (SCOPE.md + test_first.sh + verify.sh + IMPL_REPORT.md) is unregistered. Add a contracts.json entry anchored on `bundled/builder/SKILL.md` `## Artifacts` section.

2. **`reviewer ★` bundle** — Spike V spec listed as Spike VI candidate. SCOPE.md is now an artifact builder produces, so a downstream reviewer that gates on diff-vs-SCOPE has clear input contract. Distinct from builder Step 6 self-review (which is the implementer's own report); reviewer ★ would be an independent gate.

3. **scope_step2 `WROTE:` covers IMPL_REPORT only, not SCOPE.md** — silent SCOPE.md write failure could pass Step 2's check and only surface as a confusing Step 3 error. Low priority (read_run_artifact at Step 3 entry would catch it), but the dual-write asymmetry is a code smell. Consider parallel WROTE-style emission or explicit existence check.

## Ship

Spike V → master at `8d79573` (B8 commit). B-10 dogfood artifact at `~/.claude/channels/assemble/runs/20260503-145104-a531/`. server/run_dir.py + tests/unit/test_run_dir.py changes commit separately as `feat(server): add list_runs()`. This document commits as `docs(v4-spike-v): ship — B-10 dogfood 13/13 PASS, Spike VI carryforward`.
