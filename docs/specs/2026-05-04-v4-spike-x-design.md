# V4 Spike X Design — keeper ★ bundle (cross-cutting C closure)

**Date**: 2026-05-04
**Status**: draft (pre-review)
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_ix.md`

---

## Scope

Two-track spike landing the **sixth self-sufficient ★ bundle** (meta — keeper) AND
the cross-bundle learning recall mechanism that closes V4 spec § Cross-cutting C
("트레이스 자가 점검 + 학습 회수"). After Spike X, V4's "검증 가능한 산출물 기반
자가 강제 시스템" promise is operationally complete (Spike IX closed stage-cover;
Spike X closes the audit-trail loop).

- **Track A — keeper ★ bundle (meta stage, single self-sufficient ★)** — 4-step
  pipeline that audits a finished run's deposited artifacts, extracts violation
  candidates by deterministic rules, summarizes them with bounded LLM prose,
  and appends to a global ledger with deterministic prune. Output:
  `KEEPER_REPORT.md` + appended entries in
  `~/.claude/channels/assemble/learnings.jsonl`.
- **Track B — cross-bundle learning recall (additive harness extension)** —
  introduces `wrap_with_preamble_and_learnings(prompt, run_id, stage)` that
  injects top-K relevant prior learnings as a body-prefix fence (placed AFTER
  the `[TASK]` delimiter, BEFORE the original body). Preamble bytes unchanged;
  ALLOW_LIST + canonical preamble sha invariants preserved. `dispatch_and_record`
  routes to the new wrapper automatically — zero call-site changes for existing
  ★ bundles.

Ship gate: **B-15 dogfood** — 4 sub-runs covering the verdict matrix:
1. **happy** — full plan→build→review→verify→ship sequence, then keeper audits
   the run, finds zero violations, emits `KEEPER_REPORT.md` with `audit: clean`,
   appends nothing to ledger. Verifies clean-path early-exit.
2. **abort** — synthetic SCOPE deviation seeded into a run (file edited that
   matches a deny pattern), keeper detects, emits 1 learning entry, appends to
   ledger.
3. **build-fail** — verify_result.verdict=fail, keeper extracts AC-failure
   learning, appends to ledger.
4. **iter-N learnings recall** — second run picks up learnings.jsonl entries
   from runs 2+3, dispatches a plan-pack iteration, body shows `[PRIOR LEARNINGS]`
   fence with top-K entries (recency + stage-priority ranked).

12 AC PASS target.

### Critical scope boundary — single-run safe, multi-run deferred

keeper ★ assumes assemble runs are sequential (no concurrent runs). Ledger
append is a Read-then-Write through Write tool — not atomic across processes.
This is V4-acceptable: assemble doesn't support concurrent runs anyway. Multi-
run safety (file locks, atomic rename via Bash) is **V5 scope**.

### Out of scope

- ❌ Multi-run concurrency safety (file locks, advisory inotify) — V5 scope
- ❌ False-positive learning-feedback loop (user marks an entry as wrong, system
  learns to suppress) — V5 scope; V4 ships static `learnings.skip` denylist
  (user-edited)
- ❌ Cross-machine learning sync (rsync / git-tracked ledger) — explicitly NOT
  V4; ledger is local to one machine
- ❌ Visual learning UI — out of scope; ledger is jsonl + KEEPER_REPORT.md only
- ❌ `roles.json` standard role dictionary file (memory-only spec; deferred
  again — Spike XI candidate)
- ❌ F4 perf collapse (reviewer ★ Steps 1/2/3/5/6 deterministic shell)
- ❌ /assemble eject command (Spike XII candidate)
- ❌ Phase G empty-mac dogfood (V4 release gate; Spike XIII external validation)
- ❌ Build command sandboxing (V4-out-of-trust-model; V5 candidate)
- ❌ Codex CLI / Gemini CLI compat — V4 비범위

---

## Track A — keeper ★ bundle

Meta-stage orthogonal bundle. Reads run_dir artifacts deposited by other
bundles (parsed_scope.json, audit JSONs, REPORT.md files, dispatches.jsonl),
detects 4 violation categories deterministically, summarizes prose-only via
bounded LLM, appends to global learnings.jsonl with deterministic prune.

### Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<rid>/`.
- `<run_dir>/parsed_scope.json` — required; provides `allow` / `deny` lists for
  Rule R2 (SCOPE deviation detection). Missing → keeper emits `audit: skipped`
  with reason `parsed_scope.json missing`, no ledger writes.
- `<run_dir>/dispatches.jsonl` — optional; presence enables Rule R5 (dispatch-
  audit consistency: any `status: failed` row → flag).
- `<run_dir>/*.json` (audit trail) — keeper enumerates known names: preflight,
  version_bump, build_result, tag_result, verify_result, execution_result,
  extracted_completion. Each contributes evidence to relevant rules.
- `<run_dir>/*.md` (reports) — REVIEW_REPORT, VERIFY_REPORT, SHIP_REPORT,
  KEEPER_REPORT. Report verdicts informational; not used for rule firing.

### Sub-agent matrix (4 step + 1 orchestrator helper)

| Step | Prompt file | Sub-agent type | Tools granted |
|---|---|---|---|
| 1 | `keeper_audit_step1.md` | `general-purpose` | Read, Write, **Bash** (read-only `git diff --name-only HEAD~..HEAD` for SCOPE deviation, scoped to repo cwd) |
| 2 | `keeper_extract_step2.md` | `general-purpose` | Read, Write, **Bash** (`python3 ~/.claude/skills/assemble/bundled/keeper/scripts/extract_rules.py <run_dir>` — single canned invocation) |
| 3 | `keeper_summarize_step3.md` | `general-purpose` | Read, Write |
| 4 | `keeper_ledger_step4.md` | `general-purpose` | Read, Write, **Bash** (single canned `python3 ~/.claude/skills/assemble/bundled/keeper/scripts/ledger_update.py <run_dir>` invocation) |
| iter | `keeper_iter_revisit.md` | orchestrator helper (NOT in allowlist; ORCHESTRATOR_ONLY_PROMPTS) | — |

Bash granted to 3 of 4 (vs verifier 1/4, shipper 3/4). Step 1 = read-only git
probe; Step 2 + 4 = canned Python invocations. Step 3 = pure file IO.

> **B5 amendment (recorded post-implementation)**: original spec scoped Step 4 as
> Read/Write only. During Phase B5 implementation the ledger I/O surface was
> deemed too complex for inline `python3 -c` (~80 lines), so it was shipped as
> `bundled/keeper/scripts/ledger_update.py` invoked via Bash — same canned-script
> pattern as Step 2. This widens Step 4 to Bash. Documented inline above; plan
> §B5 already pre-recorded the amendment rationale.

### Step responsibilities

#### Step 1 — audit inventory

Sub-agent walks run_dir, enumerates which bundles ran, reads dispatches.jsonl
header (if present), runs read-only `git diff --name-only HEAD~..HEAD` (cwd =
repo containing run_dir's tracked SCOPE.md). Writes `audit_inventory.json`:

```json
{
  "run_id": "20260504-...",
  "bundles_observed": ["plan-pack", "reviewer", "verifier", "shipper"],
  "artifacts_present": {
    "parsed_scope.json": true,
    "dispatches.jsonl": true,
    "verify_result.json": true,
    "shipper_report_md": true,
    ...
  },
  "verdicts_collected": {
    "reviewer": "merge-ready",
    "verifier": "pass",
    "shipper": "ship-ready"
  },
  "git_diff_files": ["src/auth.py", "tests/unit/test_auth.py"],
  "head_sha": "<40 hex>"
}
```

Verdict: `audit-ready` if `parsed_scope.json` present AND ≥1 bundle artifact
detected; else `audit-skipped` with reason.

#### Step 2 — deterministic rule extraction

Sub-agent runs `python3 .../bundled/keeper/scripts/extract_rules.py <run_dir>`.
The script (≤200 lines, version-controlled, no LLM) reads
`audit_inventory.json` + targeted artifacts, applies 5 deterministic rules,
writes `learning_candidates.json`:

| Rule | Category | Detection logic |
|---|---|---|
| R1 | `rule-violation` | dispatches.jsonl scan: any row with `status: failed` → 1 candidate (rule-3 surrogate, since direct 4-rule violation isn't observable from artifacts) |
| R2 | `scope-deviation` | parsed_scope.deny ∩ git_diff_files non-empty → 1 candidate per matched (deny-pattern, file) pair |
| R3 | `ac-failure` | verify_result.verdict == "fail" → 1 candidate with `command_executed` + `reason` |
| R4 | `todo-leakage` | `git diff --unified=0 HEAD~..HEAD | grep '^+' | grep -E 'TODO|FIXME|XXX'` → 1 candidate per added marker |
| R5 | `dispatch-failure` | dispatches.jsonl: count rows with `status: failed`; ≥1 → 1 candidate with step labels |

Each candidate is a structured record (no prose):

```json
{
  "rule_id": "R2",
  "category": "scope-deviation",
  "evidence": {"file": "src/auth.py", "deny_pattern": "auth/*"},
  "evidence_hash": "<sha256 of canonical-form evidence>"
}
```

`evidence_hash` is SHA-256 of `json.dumps(evidence, sort_keys=True)` — used
later for dedup across runs.

#### Step 3 — bounded LLM summarization

Sub-agent reads `learning_candidates.json`, writes a ≤200-char human-readable
summary for each candidate. Output `learnings_to_emit.json`:

```json
{
  "run_id": "...",
  "entries": [
    {
      "rule_id": "R2",
      "category": "scope-deviation",
      "summary": "Edited src/auth.py despite deny pattern auth/* — extract helper outside denied tree before editing.",
      "evidence": {...},
      "evidence_hash": "..."
    }
  ]
}
```

Constraints (deterministic guards before LLM):
- summary ≤ 200 chars (truncate at 197 + "…" if exceeded)
- summary single line (newlines stripped)
- summary in same language as parsed_scope.task_summary (Korean if Korean
  detected via existing `scope_parser` heuristic, else English)
- Each entry preserves `evidence` + `evidence_hash` from Step 2 verbatim

If LLM fails / returns empty: Step 3 falls back to a deterministic template
per rule_id (`{R2}: edited {file} matching deny {pattern}`).

#### Step 4 — ledger append + prune

Sub-agent reads existing `~/.claude/channels/assemble/learnings.jsonl`,
appends new entries from `learnings_to_emit.json`, applies prune rules,
writes back via Write (full overwrite of jsonl). Also writes `KEEPER_REPORT.md`.

**Ledger entry schema**:

```json
{"ts":"2026-05-04T...Z","run_id":"...","rule_id":"R2","category":"scope-deviation","summary":"...","evidence_hash":"<sha256>","evidence":{...}}
```

**Prune rules (applied in order, deterministic)**:

1. **TTL**: drop entries with `ts < now - 30 days`
2. **Skiplist**: drop entries with `evidence_hash ∈ skiplist` (where skiplist
   = lines from `~/.claude/channels/assemble/learnings.skip`, one hash per
   line, comments `#` allowed)
3. **Dedup**: collapse entries with identical `evidence_hash` to the most
   recent `ts` (group-by, keep-max-ts)
4. **Cap**: after above, cap at 100 active entries — FIFO eviction by `ts`
   ascending until len ≤ 100

`KEEPER_REPORT.md` 7-section template (clean) OR 4-section abort variant
(audit-skipped). Sections (clean): Run summary / Audit inventory / Rules
fired / Learnings emitted / Ledger state delta / Prune summary / Next-run
recall preview.

### Verdict logic (deterministic)

```python
verdict = "audit-clean" if (
    audit_inventory.verdict == "audit-ready"
    AND total_learnings_emitted == 0
) else "audit-flagged" if (
    audit_inventory.verdict == "audit-ready"
    AND total_learnings_emitted >= 1
) else "audit-skipped"  # parsed_scope missing, etc.
```

Three outcomes (no pass/fail — keeper is observational, not gating):
- `audit-clean` → no violations detected; ledger unchanged
- `audit-flagged` → ≥1 candidate emitted; ledger appended; KEEPER_REPORT
  enumerates each
- `audit-skipped` → preconditions absent; KEEPER_REPORT abort variant

### Artifacts

run_dir = `~/.claude/channels/assemble/runs/<rid>/`. Ledger root =
`~/.claude/channels/assemble/`.

| Path | Producer | Schema |
|---|---|---|
| `<run_dir>/audit_inventory.json` | Step 1 | inventory + verdict |
| `<run_dir>/learning_candidates.json` | Step 2 | candidate list |
| `<run_dir>/learnings_to_emit.json` | Step 3 | summarized entries |
| `<run_dir>/KEEPER_REPORT.md` | Step 4 | 7-section happy or 4-section abort |
| `~/.claude/channels/assemble/learnings.jsonl` | Step 4 (shared, append + prune) | one JSON per line |
| `~/.claude/channels/assemble/learnings.skip` | user-managed (NOT keeper) | one evidence_hash per line, `#` comments |

### Schema additions to existing artifacts

None. keeper consumes existing artifacts read-only. Track A is purely
additive at the file level.

### Security model (`SECURITY.md` — 7 threats T1-T7 + 6 mitigations + 5 explicit non-goals)

**Bash surface = 2 of 4 steps**. Threat coverage:

- **T1** Step 1 git probe shell escape — argv-list invariant via existing
  `git_helpers` (Spike IX pattern), NO `shell=True` (mitigation #1)
- **T2** Step 2 canned Python script substitution — `extract_rules.py` is
  shipped in version control, hash pinned in `contracts.json`. Sub-agent
  invokes by literal path; no user-controlled args (mitigation #2)
- **T3** Ledger jsonl injection — entries written via `json.dumps(ensure_ascii=False)`,
  one per line; no user-controlled `\n` injection possible because Step 3
  output is sanitized (single-line summary; newlines stripped pre-write)
  (mitigation #3)
- **T4** Skiplist file traversal — `learnings.skip` path is hardcoded,
  not user-parameterized (mitigation #4)
- **T5** Concurrent ledger corruption — Read-modify-Write race possible if
  two assemble runs overlap. **NOT mitigated in V4** — documented as known
  limitation; V5 will add `fcntl.flock` or atomic rename. Single-run V4
  guarantee makes this acceptable (mitigation #5: documentation)
- **T6** Stale-evidence false positive — if user reverts a deny-list violation
  in a later run, the old learning still recommends avoiding the path. Mitigated
  by 30-day TTL + user `learnings.skip` denylist (mitigation #6)
- **T7** PII / secret in ledger — if SCOPE.md or git diff exposes secrets,
  evidence may capture them. **NOT mitigated** — explicitly: keeper does NOT
  redact. SCOPE author's responsibility (matches verifier ★ trust model).
  Documented under § Build-command-equivalent trust model (rebrand: § Audit-
  evidence trust model).

**Explicit non-goals** (5):
1. No remote ledger sync
2. No cross-machine portability
3. No PII redaction
4. No false-positive feedback (V5)
5. No concurrent run safety (V5)

### contracts.json (3 entries — Spike VIII pattern)

- `spike-x-keeper-allowlist` — 4 sub-agent prompt files enumerated; Bash → step1
  + step2 only
- `spike-x-keeper-verdict-invariant` — 3-outcome rule (`audit-clean` /
  `audit-flagged` / `audit-skipped`)
- `spike-x-keeper-artifact-invariant` — KEEPER_REPORT 7-section happy + 4-section
  abort schema lock; ledger entry schema lock (8 keys)

---

## Track B — cross-bundle learning recall

Additive harness extension. Existing `wrap_with_preamble` + `dispatch_prompt`
+ `dispatch_and_record` semantics preserved byte-for-byte when ledger is
empty. With non-empty ledger, top-K relevant entries are spliced into the
**body region** (after `[TASK]\n`, before original prompt body) — preserving
preamble sha invariant.

### New helper

```python
# server/learnings.py (NEW MODULE)

def select_relevant(stage: str, k: int = 5) -> list[dict]:
    """Top-K learnings ledger entries ranked for `stage`.

    Ranking (deterministic):
      1. category match: STAGE_CATEGORY_PRIORITY[stage] → matches sort first
      2. recency: ts descending
      3. tie-break: rule_id alpha ascending
    Returns ≤K entries; empty list if ledger missing/empty.
    """

def render_learnings_fence(entries: list[dict]) -> str:
    """Render `[PRIOR LEARNINGS — 우선 회피]` fenced block.

    Format:
        [PRIOR LEARNINGS — 우선 회피]
        1. (R2) Edited src/auth.py despite deny pattern auth/* — ...
        2. (R3) Verify command exited 1 — check pytest path before declaring AC pass.
        ...
        [/PRIOR LEARNINGS]

    Empty entries → empty string (no fence). Each line ≤200 chars (already
    enforced at extraction).
    """
```

### `wrap_with_preamble_and_learnings`

```python
# server/harness.py (ADDITIVE FUNCTION)

def wrap_with_preamble_and_learnings(
    prompt: str,
    run_id: Optional[str] = None,
    stage: Optional[str] = None,
    k: int = 5,
) -> str:
    """`wrap_with_preamble` + body-prefix learnings fence injection.

    If `run_id is None` OR `stage is None` OR ledger empty → returns
    `wrap_with_preamble(prompt)` unchanged (zero-byte regression).

    Else:
        wrapped = wrap_with_preamble(prompt)         # <pre>\n[TASK]\n<body>
        entries = select_relevant(stage, k)
        if not entries: return wrapped
        fence = render_learnings_fence(entries)
        # splice fence between [TASK]\n and body
        return wrapped.replace(
            "\n[TASK]\n",
            f"\n[TASK]\n{fence}\n\n",
            1,  # only first occurrence
        )

    Result format (with non-empty ledger):
        <preamble>
        [TASK]
        [PRIOR LEARNINGS — 우선 회피]
        1. ...
        2. ...
        [/PRIOR LEARNINGS]

        <original body>
    """
```

### `dispatch_and_record` integration

Existing `dispatch_and_record(run_id, prompt_file=...)` already has `run_id`.
Stage derivation from `prompt_file`:

```python
# server/harness.py — extend
_PROMPT_TO_STAGE = {
    # plan-pack ★
    "prd_step2.md": "plan",
    "prd_step3.md": "plan",
    ...
    # debugger ★
    "repro_step2.md": "debug",
    ...
    # builder ★
    "scope_step2.md": "execute",
    ...
    # reviewer ★
    "parse_scope_step1.md": "review",
    ...
    # verifier ★
    "verifier_extract_step1.md": "verify",
    ...
    # shipper ★
    "shipper_preflight_step1.md": "ship",
    ...
    # keeper ★ (Spike X)
    "keeper_audit_step1.md": "meta",
    ...
}
```

`dispatch_and_record` change (single line):

```python
prompt_text = dispatch_prompt(prompt_file)  # OLD
# →
stage = _PROMPT_TO_STAGE.get(prompt_file)
prompt_text = wrap_with_preamble_and_learnings(
    _resolve_prompt_path(prompt_file).read_text(encoding="utf-8"),
    run_id=run_id,
    stage=stage,
)
```

(`dispatch_prompt` itself remains unchanged for back-compat with code paths
that don't have `run_id`.)

### Stage→category priority map

```python
# server/learnings.py
STAGE_CATEGORY_PRIORITY = {
    "plan":    ["scope-deviation", "ac-failure", "todo-leakage", "rule-violation", "dispatch-failure"],
    "execute": ["scope-deviation", "todo-leakage", "rule-violation", "ac-failure", "dispatch-failure"],
    "debug":   ["ac-failure", "rule-violation", "scope-deviation", "todo-leakage", "dispatch-failure"],
    "review":  ["scope-deviation", "todo-leakage", "rule-violation", "ac-failure", "dispatch-failure"],
    "verify":  ["ac-failure", "rule-violation", "scope-deviation", "todo-leakage", "dispatch-failure"],
    "ship":    ["scope-deviation", "ac-failure", "rule-violation", "todo-leakage", "dispatch-failure"],
    "meta":    ["scope-deviation", "ac-failure", "todo-leakage", "rule-violation", "dispatch-failure"],
}
```

### Critical preserve invariants (Track B)

- ✅ Canonical preamble v3 sha unchanged: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged
- ✅ `_split_preamble_body` returns identical preamble bytes (fence is in body
  region, after `[TASK]\n` delimiter)
- ✅ `_TASK_DELIM = "\n[TASK]\n"` unchanged
- ✅ `verify_dispatches` ok=True regression-safe (preamble shas unchanged
  regardless of ledger state)
- ✅ Empty/missing ledger → byte-identical to today (existing tests pass
  unchanged)
- ✅ `wrap_with_preamble(prompt)` signature unchanged — back-compat preserved
  for any caller that bypasses `dispatch_and_record`

---

## 4 critical decisions resolved (pre-spec)

### D1 — Ledger format = single append-only `learnings.jsonl`

**Options considered**: per-run files / single jsonl / category-sharded jsonl.

**Decision**: single `~/.claude/channels/assemble/learnings.jsonl`. Reasons:
- Append + atomic-overwrite-on-prune is simple
- 100-entry cap → max ~50KB; trivial to scan
- Per-run files would balloon directory inode count
- Sharded jsonl premature optimization (Codex retro will flag if needed)

### D2 — Injection mechanism = body-prefix fence (NOT preamble extension)

**Options considered**:
- A. Extend canonical preamble v3 (preamble sha changes, ALLOW_LIST + 5 ★
  bundles all need sync — heavy invariant break)
- B. Body-prefix fence after `[TASK]\n` (preamble sha unchanged)
- C. Separate function for new bundles only (existing 5 ★ don't benefit)

**Decision**: Option B. Reasons:
- preamble sha invariant is load-bearing across Spike I~IX
- Body-prefix preserves dispatch audit chain byte-perfect for empty ledger
- All existing ★ bundles auto-receive learnings via `dispatch_and_record`
  (zero call-site changes)
- ALLOW_LIST stays {v1, v2, v3}

### D3 — Pruning policy = TTL 30d + skiplist + dedup + FIFO cap 100

**Options considered**: TTL only / cap only / quality-score / LRU.

**Decision**: composite (TTL + skiplist + dedup + cap), applied in order. Reasons:
- TTL keeps ledger fresh
- Skiplist user-overridable (false-positive escape valve)
- Dedup prevents same-violation spam
- FIFO cap prevents unbounded growth
- All 4 rules are deterministic → unit-testable

### D4 — Extraction = hybrid (deterministic categorization + LLM summary)

**Options considered**:
- A. Pure LLM (read trace dir, summarize)
- B. Pure deterministic (Python rules + template prose)
- C. Hybrid (Python rules → structured candidates → LLM prose summary)

**Decision**: Option C. Reasons:
- V4 spirit: deterministic where possible, LLM only where natural language helps
- Step 2 (rules) → testable with fixtures
- Step 3 (summary) → bounded by 200-char + single-line + language-match constraints
- Fallback: Step 3 LLM failure → deterministic template prose (`{R2}: edited
  {file} matching deny {pattern}`)
- This mirrors verifier ★ pattern (deterministic exit-code → LLM-friendly
  recommendations text)

---

## Phase plan

| Phase | Tasks | Output |
|---|---|---|
| A | A1: `server/learnings.py` module (select_relevant + render_learnings_fence + STAGE_CATEGORY_PRIORITY); A2: extend `parsed_scope` schema docstring (no actual schema change — just docs that keeper reads `allow`/`deny`); A3: ledger location helpers (`learnings_path`, `learnings_skip_path`, `read_ledger`, `write_ledger`, `prune_ledger`) | server module + 30+ unit tests |
| B | B1: `bundled/keeper/SKILL.md` 5-section + sub-agent matrix; B2: `keeper_audit_step1.md` prompt; B3: `keeper_extract_step2.md` + `bundled/keeper/scripts/extract_rules.py`; B4: `keeper_summarize_step3.md`; B5: `keeper_ledger_step4.md`; B6: `keeper_iter_revisit.md`; B7: KEEPER_REPORT template (happy + abort variants) | keeper bundle assets |
| C | C1: SECURITY.md (7 threats + 6 mitigations + 5 non-goals); C2: contracts.json 3 entries; C3: inventory.py `_BUNDLED_DIR_TO_STAGE` += `("keeper": "meta")`; C4: harness.py `_BUNDLED_DIR_TO_STAGE` sync (universal-defense convention from Spike VIII) | safety + integrity layer |
| D | D1: extend `ALLOWED_PROMPT_FILES` (4 keeper subagent prompts); D2: extend `ORCHESTRATOR_ONLY_PROMPTS` (`keeper_iter_revisit.md`); D3: implement `wrap_with_preamble_and_learnings` + `_PROMPT_TO_STAGE` map; D4: route `dispatch_and_record` through new wrapper | dispatch chain wired |
| E | E1: `superpowers:code-reviewer` overall review; E2: Codex retro (mandatory per cross-cutting C complexity) | review verdicts + amendments |
| F | F1: B-15 dogfood — 4 sub-runs (happy / abort / build-fail / iter-N learnings recall); F2: 12 AC matrix; F3: dogfood doc | ship gate evidence |
| G | G1: CHANGELOG flip; G2: memory `project_assemble_v4_spike_x.md` write; G3: MEMORY.md index update; G4: ship commit | master ship |

Phase A and Phase B can run partially in parallel (B prompts can be drafted
once A1's STAGE_CATEGORY_PRIORITY is defined). Phase C and D have ordering
constraint — D depends on C2 contracts.json structure.

### Codex retro mandatory point (per cross-cutting C complexity)

Phase E2 invokes `codex:codex-rescue` adversarial review on:
- Step 2 deterministic extraction logic (`extract_rules.py`) — does it false-
  positive on legitimate refactors? false-negative on subtle deny-list overlaps?
- Step 4 prune order (TTL → skiplist → dedup → FIFO cap) — any race condition
  combination that loses entries unexpectedly?
- Track B body-prefix fence — does the splice handle edge cases (multiple
  `[TASK]\n` in body, prompt prefixed with `[TASK]\n` literal in user content)?
- Ledger schema durability — is the 8-key entry record forward-compat for
  V5 multi-run safety?

Spike VIII/IX retro patterns: 5-8 findings expected; 0-1 critical; ≥3
amendments applied at Phase E.

---

## AC matrix (B-15 dogfood, target 12 PASS / 0 FAIL)

| AC | Description | Verification |
|---|---|---|
| AC1 | keeper bundle on disk: `bundled/keeper/SKILL.md`, 4 subagent prompts, 1 orchestrator helper, 1 script (`extract_rules.py`), 1 KEEPER_REPORT template | filesystem ls + checksum |
| AC2 | `ALLOWED_PROMPT_FILES` += 4 keeper prompts; `ORCHESTRATOR_ONLY_PROMPTS` += keeper_iter_revisit.md | unit test (allowlist roundtrip) |
| AC3 | `inventory.json._BUNDLED_DIR_TO_STAGE` includes `keeper:meta`; harness.py copy synced | unit test (universal-defense symmetry) |
| AC4 | Run 1 (happy): seeded clean run, keeper emits `audit-clean`, ledger unchanged byte count | jsonl byte diff = 0 |
| AC5 | Run 2 (abort): seeded SCOPE deviation, keeper emits 1 R2 entry, ledger byte count grows | jsonl entries +1 |
| AC6 | Run 3 (build-fail): seeded verify_result.verdict=fail, keeper emits 1 R3 entry | jsonl entries +1 |
| AC7 | Run 4 (recall): plan-pack iter-N dispatch produces wrapped prompt with `[PRIOR LEARNINGS]` fence containing top-K entries from runs 2+3 | grep wrapped prompt for fence + entry summaries |
| AC8 | KEEPER_REPORT.md row count: happy=7 sections, abort=4 sections (skipped variant) | section header count |
| AC9 | `verify_dispatches(run_id)` returns ok=True for all 4 sub-runs (preamble sha invariant preserved) | server.harness.verify_dispatches |
| AC10 | Wall time: self-execute mode ≤ 60s, real-dispatch mode ≤ 600s | timestamp delta |
| AC11 | Codex retro applied amendments ≥ 0 (mandatory invocation, amendments optional based on findings) | retro doc presence |
| AC12 | pytest passing count: baseline 563 + new tests (target ≥ 600 passed, no regressions) | pytest -q final count |

---

## V4 정체성 보호 (변경 X)

- ✅ Spike I~IX core contracts (verdict logic / 7-section / allowlist / RUN_DIR
  token / FIX-1 streaming + Codex F2/F3 process-group kill / extended tag
  validation / kill-on-EITHER-cap / Spike IX A1 IGNORECASE)
- ✅ canonical preamble v3 sha unchanged: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3} (additive — 4 new keeper subagent prompt files
  added to ALLOWED_PROMPT_FILES; ALLOW_LIST itself unchanged)
- ✅ V3 concierge menu layer unchanged
- ✅ 5 self-sufficient ★ bundle prompts unchanged
- ✅ Phase D wiring convention (ALLOWED_PROMPT_FILES + _BUNDLED_DIR_TO_STAGE +
  ORCHESTRATOR_ONLY_PROMPTS + contracts.json) — keeper follows same pattern
- ✅ universal-defense convention (Spike IX cleanup): _BUNDLED_DIR_TO_STAGE
  synced both sides
- ✅ ORCHESTRATOR_ONLY_PROMPTS single source (server.harness)
- ✅ orchestrator-only V4 #9 — main never executes Bash; keeper sub-agents
  own all 2 Bash-granted steps
- ✅ scope_parser deterministic helper (B-13 strict grammar) unchanged
- ✅ `parsed_scope.json` shape unchanged (keeper reads existing `allow`/`deny`/`completion`)
- ✅ `wrap_with_preamble(prompt)` signature unchanged — additive wrapper for
  learnings injection only

---

## Spike XI candidates (deferred from Spike X)

- **F4 perf collapse** — reviewer ★ deterministic shell collapse
- **roles.json file** — memory-defined dictionary not yet on disk
- **release-publish / deploy-target roles** — for future shipper hand-off chain
- **multi-language version bumping** — Cargo / Gem / etc. (Spike IX scope-out)
- **/assemble eject command** — Spike XII candidate
- **Phase G empty-mac dogfood** — V4 release gate (Spike XIII external validation)
- **Multi-run concurrency safety** — file locks; V5 candidate (NOT V4)
- **False-positive feedback loop** — user-driven learning suppression; V5
- **Build command sandboxing** — V4-out-of-trust-model; V5

---

## Source

- Spec: this file (`docs/specs/2026-05-04-v4-spike-x-design.md`)
- Plan: `docs/plans/2026-05-04-v4-spike-x.md` (drafted next)
- Parent: `project_assemble_v4_spec.md`
- Sibling specs: `2026-05-04-v4-spike-vii-design.md`,
  `2026-05-04-v4-spike-viii-design.md`, `2026-05-04-v4-spike-ix-design.md`
