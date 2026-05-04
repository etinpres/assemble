# V4 Spike VII Design — RUN_DIR token + dispatch hardening

**Date**: 2026-05-04
**Status**: approved
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_vi.md`

---

## Scope

Three-track spike to fix all CRITICAL + HIGH carryforwards from Spike VI B-11 real-dispatch:

- **Track A (CRITICAL)** — F6 path-ambiguity fix. New `{{RUN_DIR}}` absolute-path token. Migrate all 32 `runs/{{RUN_ID}}/...` relative-path occurrences across 4 ★ bundles.
- **Track B (HIGH)** — F7 sub-agent stdout discipline. Tighten `WROTE:` parser to match the LAST `WROTE:` line, not the first. Strengthen prompt instruction.
- **Track C (HIGH)** — F8 AC10 wall-time budget revision. Real-dispatch needs 600s, self-execute keeps 300s.

Ship gate: **B-12 dogfood** — same input as Spike VI B-11 real-dispatch (`Spike V list_runs` change @ commit `832dfdd`), but with **no symlink** in `~/.claude/skills/assemble/runs/`. Sub-agent cwd-independent path resolution must work end-to-end. 12 AC PASS target.

### Out of scope

- ❌ verifier ★ bundle (Spike VIII candidate)
- ❌ shipper ★ bundle (Spike VIII candidate)
- ❌ F4 perf collapse (Step 1/2/3/5/6 → deterministic shell) — separate spike
- ❌ F1 한글 backtick mangling in `parse_scope_step1` — Spike VIII grammar tightening
- ❌ Naming convention `<bundle>_<step>.md` prefix migration — case-by-case in Spike VIII
- ❌ Codex CLI / Gemini CLI compat — V4 비범위

---

## Track A — F6 RUN_DIR absolute-path token

### Problem (B-11 real-dispatch evidence)

Sub-agents are dispatched with cwd typically at `~/.claude/skills/assemble/` (the SKILL package root). Prompts write paths like `runs/{{RUN_ID}}/SCOPE.md` which resolve to `~/.claude/skills/assemble/runs/<rid>/SCOPE.md` — but the canonical run dir is `~/.claude/channels/assemble/runs/<rid>/`.

B-11 real-dispatch worked **only because of a manual `runs/` symlink** in the SKILL dir. That is masking, not fixing. Spike VII removes the symlink dependency.

### Design

**1. New helper `run_dir_path(run_id) -> Path`** in `server/run_dir.py`.

```python
def run_dir_path(run_id: str) -> Path:
    """Return the absolute run directory path for `run_id`. Does not create it.

    Companion to `run_artifact_path` for callers that need just the directory
    (e.g. `{{RUN_DIR}}` token substitution). Reuses the same basename
    validation against `run_id` as `run_artifact_path` to keep the safety
    contract identical.
    """
    if not run_id or "/" in run_id or "\\" in run_id or run_id.startswith("."):
        raise ValueError(f"unsafe run_id: {run_id!r}")
    if run_id != Path(run_id).name:
        raise ValueError(f"unsafe run_id: not a plain basename: {run_id!r}")
    return _runs_dir() / run_id
```

Exported via `server/__init__.py` alongside `run_artifact_path`.

**2. `substitute_inputs` auto-derives `RUN_DIR`** from `RUN_ID` when caller omits it.

```python
def substitute_inputs(prompt_text: str, inputs: dict) -> str:
    # ... existing inputs-section guard ...
    if not inputs:
        return prompt_text
    enriched = dict(inputs)
    if "RUN_ID" in enriched and "RUN_DIR" not in enriched:
        from server.run_dir import run_dir_path
        enriched["RUN_DIR"] = str(run_dir_path(enriched["RUN_ID"]))
    # ... existing replace loop using `enriched` ...
```

Why auto-derive: every existing `record_dispatch` call site already passes `RUN_ID`. Auto-derivation = zero changes to orchestrator SKILL.md call sites; just prompts swap relative → absolute. Surgical Changes principle.

Caller can still pass `RUN_DIR` explicitly to override (e.g. dogfood / tests).

**3. Prompt migration: `runs/{{RUN_ID}}/X` → `{{RUN_DIR}}/X`** across 32 occurrences:

| Bundle | Files affected | Occurrences |
|---|---|---|
| reviewer | 6 sub-agent prompts | 23 |
| builder | scope_step2, test_step3, verify_step5 | 4 |
| debugger | repro_step2, fix_step5 | 5 |
| plan-pack | (none — uses `write_run_artifact` directly) | 0 |
| **total** | **11 prompt files** | **32** |

Existing `{{RUN_ID}}` token usage (106 occurrences) **stays as-is** — additive change. Only path-prefixed `runs/{{RUN_ID}}/...` patterns migrate.

**4. SKILL.md fix — reviewer's broken doc reference** (line 59):

```diff
- Main resolves `run_dir` via `server.run_dir.run_artifact_path(run_id, ".")`.
+ Main resolves `run_dir` via `server.run_dir.run_dir_path(run_id)`.
```

`run_artifact_path(run_id, ".")` would actually `raise ValueError` (basename validator rejects leading `.`) — the doc was aspirational. Fix the doc to match new helper.

### Regression test

`tests/unit/test_run_dir_token_invariant.py`:

```python
def test_no_relative_run_path_in_prompts():
    """No prompt may use `runs/{{RUN_ID}}/` — must use `{{RUN_DIR}}/`."""
    bundled = Path("bundled")
    offenders = []
    for prompt in bundled.glob("*/prompts/**/*.md"):
        text = prompt.read_text(encoding="utf-8")
        # explicit relative-path pattern only — bare `{{RUN_ID}}` is OK
        if "runs/{{RUN_ID}}" in text:
            offenders.append(str(prompt.relative_to(bundled)))
    assert not offenders, (
        f"Prompts must use {{{{RUN_DIR}}}}/ not runs/{{{{RUN_ID}}}}/. "
        f"Offenders: {offenders}"
    )

def test_run_dir_token_present_when_path_needed():
    """Bundles that write artifacts must reference {{RUN_DIR}}."""
    must_have = ["reviewer", "builder", "debugger"]
    for bundle in must_have:
        bd = Path(f"bundled/{bundle}/prompts")
        all_text = "\n".join(p.read_text() for p in bd.glob("**/*.md"))
        assert "{{RUN_DIR}}" in all_text, (
            f"{bundle}: lost RUN_DIR token after migration"
        )
```

### contracts.json entry

```json
{
  "id": "spike-vii-rundir-invariant",
  "summary": "All bundle prompts must use {{RUN_DIR}}/ for run artifact paths, never runs/{{RUN_ID}}/. Sub-agent cwd is unspecified; only absolute paths survive dispatch.",
  "test": "tests/unit/test_run_dir_token_invariant.py"
}
```

### Backward compatibility

- `{{RUN_ID}}` token: **preserved**. Used inside save blocks (`.replace("{{RUN_ID}}", run_id)` for sub-agent self-substitution) and as a contextual identifier.
- `run_artifact_path(run_id, filename)`: unchanged signature.
- Existing dogfood JSONs (B-11 etc.) reference `runs/<rid>/` paths in fixtures — those are historic data, not prompts; not touched.
- `runs/<RID>` symlink in SKILL dir (created during B-11 real-dispatch as a stop-gap): **delete during cleanup task**. Spike VII proves the symlink is no longer needed.

---

## Track B — F7 sub-agent stdout discipline

### Problem (B-11 real-dispatch evidence)

Step 3 sub-agent (`classify_files_step3.md`) printed:

```
Classification correct: 2 allow-hits, 0 deny, 0 unrelated.
WROTE: /Users/.../classification.json
```

Two textual patterns matching `WROTE: <path>`. Current orchestrator parser uses an unanchored `re.search(r"WROTE: (.+)", stdout)` which matches the **first** occurrence. Today the prose appears AFTER `WROTE:` in some cases and BEFORE in others — fragile.

### Design

**1. Tighten parser to match the LAST `WROTE:` line.**

In whichever helper records / verifies sub-agent output (`record_dispatch` or its caller), parse `WROTE:` paths as:

```python
import re
_WROTE_RE = re.compile(r"^WROTE: (.+)$", re.MULTILINE)

def extract_wrote_paths(stdout: str) -> list[str]:
    """Return all `WROTE: <path>` paths in MULTILINE order. Last is canonical."""
    return [m.group(1).strip() for m in _WROTE_RE.finditer(stdout)]
```

Caller takes `paths[-1]` (or all paths for multi-write steps). MULTILINE anchor + last-match semantic = prose lines never collide.

**2. Strengthen sub-agent prompt instruction** in every prompt that emits `WROTE:`:

```markdown
## Output discipline

Your final stdout MUST end with:

```
WROTE: <absolute-path-to-artifact>
```

(one line per file written, each at column 0). No prose AFTER the WROTE
lines. Prose BEFORE is tolerated but discouraged.
```

This block lives in a shared snippet (or inlined per-prompt — TBD in plan).

### Regression test

`tests/unit/test_wrote_parser.py`:

```python
def test_extract_wrote_takes_last_when_multiple():
    stdout = "WROTE: /old/path\nClassification ok\nWROTE: /new/path\n"
    assert extract_wrote_paths(stdout)[-1] == "/new/path"

def test_extract_wrote_ignores_inline_match():
    stdout = "Note: WROTE: literal in prose, not at column 0\nWROTE: /real\n"
    assert extract_wrote_paths(stdout) == ["/real"]
```

### Out of scope for Track B

- Forcing zero prose entirely (would break helpful diagnostic output).
- Structured JSON output protocol (Spike VIII candidate).

---

## Track C — F8 AC10 wall-time budget revision

### Problem

Spike VI B-11 self-execute: 100s wall (5x under budget).
Spike VI B-11 real-dispatch: 334s wall (just over 300s budget — marginal fail).

Real Agent dispatch has substantial per-call overhead (subagent startup, preamble injection, separate context window allocation × 6 dispatches).

### Design

**Split AC10 into two budgets:**

- `AC10a` — **self-execute** (orchestrator runs steps inline): wall ≤ **300s**
- `AC10b` — **real-dispatch** (orchestrator delegates each step to a subagent): wall ≤ **600s**

Apply to all ★ bundle dogfood ACs:
- reviewer ★ B-12 dogfood (this spike)
- future builder ★ / debugger ★ dogfoods retroactively documented

The AC budget revision is **dogfood doc-only** — no production code changes. Updates land in:
- `docs/dogfood/spike-vii-b12.md` (new — uses AC10a/b split)
- Reference future dogfoods in spec but don't retroactively rewrite past dogfood docs.

---

## B-12 dogfood (ship gate)

### Setup

```bash
# 1. Delete the B-11 stop-gap symlink (if present)
rm -f ~/.claude/skills/assemble/runs

# 2. Fresh run dir
RID="20260504-spikevii-b12"
mkdir -p ~/.claude/channels/assemble/runs/$RID

# 3. Copy SCOPE.md from Spike VI B-11 (same change set being reviewed)
cp ~/.claude/channels/assemble/runs/20260504-011811-b11r/SCOPE.md \
   ~/.claude/channels/assemble/runs/$RID/SCOPE.md
```

### Reviewer ★ invocation

Same as B-11 real-dispatch: review commit `832dfdd` (Spike V `list_runs` change). 6 sub-agent dispatches via `Agent({prompt: dispatch_prompt(...), ...})`.

### Acceptance criteria (12, all PASS to ship)

| # | AC | Measure |
|---|---|---|
| 1 | SCOPE.md found by Step 1 sub-agent (no symlink) | `parsed_scope.json` exists with non-empty allow + deny |
| 2 | Step 2 captures git diff to absolute `{{RUN_DIR}}/diff_inventory.json` | file exists at canonical path |
| 3 | Step 3 classification non-empty | `classification.json` has 2 entries (server/run_dir.py + tests) |
| 4 | Step 4 Rule 3 audit | `rule3_audit.json` exists |
| 5 | Step 5 verdict deterministic | `severity_grid.json.verdict == "merge-ready"` |
| 6 | Step 6 REVIEW_REPORT 7 sections | template invariant test passes |
| 7 | All 6 `dispatches.jsonl` rows present (iter1) | `wc -l == 6` |
| 8 | Each dispatch row preamble sha matches v3 (or v1/v2 ALLOW_LIST) | `verify_dispatches` returns OK |
| 9 | Verdict matches expectation (merge-ready) | matches Spike VI |
| 10a | Self-execute wall ≤ 300s | n/a for B-12 (dispatch mode) |
| 10b | Real-dispatch wall ≤ 600s | timer measurement |
| 11 | Zero `runs/{{RUN_ID}}/` patterns survive in prompts | regression test passes |
| 12 | `{{RUN_DIR}}` placeholder substituted in every dispatched prompt | `dispatches.jsonl` prompt sha replays cleanly with absolute paths |

### Failure-handling

If any AC fails, halt before ship. Fix in-place, re-run B-12. Spike doesn't ship until 12/12.

---

## V4 정체성 보호 (변경 X)

- ✅ Spike I~VI core contracts (verdict logic, 7 REVIEW_REPORT sections, 6-prompt allowlist)
- ✅ canonical preamble v3 sha
- ✅ ALLOW_LIST = {v1, v2, v3} (additive only — Track A doesn't touch preamble)
- ✅ orchestrator-only V4 #9 (main never reads SCOPE content directly)
- ✅ V3 concierge menu layer
- ✅ existing `{{RUN_ID}}` token semantics (additive `{{RUN_DIR}}` only)

---

## Decisions log

1. **`run_dir_path` as new helper**, not `run_artifact_path` overload. Why: keeps single-purpose helpers; `run_artifact_path(rid, ".")` aspirational doc would need a special-case carve-out in the basename validator that weakens the security posture. Cleaner to add a sibling.
2. **Auto-derive RUN_DIR from RUN_ID** in `substitute_inputs`. Why: surgical change. Zero orchestrator call site edits. Caller can override.
3. **Keep `{{RUN_ID}}` token** as-is (no removal). Why: backward compat + sub-agent self-substitution patterns rely on it. Additive change minimizes blast radius.
4. **Last-match `WROTE:` parser** rather than first-match. Why: humans append summary at end; LLMs append `WROTE:` at end. Last-match aligns with both conventions.
5. **AC10 split into a/b** rather than single 600s. Why: self-execute regression safety net stays tight; real-dispatch reflects true cost.
6. **B-12 dogfood deletes the symlink first**. Why: symlink masked F6. Removing it is the actual proof that the fix works.
7. **No prompt rename, no SKILL refactor.** Track A is path-only migration. Steps, sequence, allowlist names all unchanged.

---

## Sources

- Parent spec: `project_assemble_v4_spec.md` (V4 16 decisions + Phase A/B status)
- Spike VI carryforward: `project_assemble_v4_spike_vi.md` § "Spike VII candidates"
- B-11 real-dispatch evidence: `docs/dogfood/spike-vi-b11.md` + 21b3393
- Helper file: `server/run_dir.py`
- Substitution helper: `server/harness.py:197 substitute_inputs`
