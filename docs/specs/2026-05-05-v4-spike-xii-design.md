# V4 Spike XII Design — `/assemble eject` command (bundle → user-skill copier)

**Date**: 2026-05-05
**Status**: draft (pre-review)
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_xi.md`

---

## Scope

Single-track infrastructure spike landing the `/assemble eject` command —
copies a bundled skill from `~/.claude/skills/assemble/bundled/<bundle>/`
to a user-controlled destination at `~/.claude/skills/<name>/` so the user
can fork and customize freely without touching the assemble bundle.

V4 결정 #1 lineup is 10/10 complete after Spike XI. Spike XII = the
**last-mile** between "bundles ship inside assemble" (Spike XI) and "blank-Mac
dogfood validates V4 paradigm" (Spike XIII = V4 release gate). Without
eject, a user who likes the `plan-pack ★` bundle but wants to tweak
the AI-slop anti-pattern table is forced to edit assemble's bundled
copy in-place — which (a) breaks the bundled-quality guarantee, (b)
makes assemble upgrades destructive, (c) blocks the "사용자가 자신의 컴
스킬로 가져와 자유롭게 수정 가능" promise of V4 결정 #5.

Ship gate: **B-17 dogfood** — single self-execute run that ejects one
bundle into a tempdir-overridden `ASSEMBLE_HOME`, verifies file-by-file
copy fidelity, source-bundle SHA invariant, ejected SKILL.md frontmatter
yaml-strict validity, and inventory scan integration (ejected skill
appears with `bundled=False` while source still appears with
`bundled=True`).

### Architectural identity (V4 #9 exception scope)

eject is **main-direct IO**, not sub-agent dispatch. Same pattern as
`guardian` standard bundle (Spike XI):

- NO `prompts/subagent/` directory for eject
- NO entry in `ALLOWED_PROMPT_FILES`
- NO entry in `_PROMPT_TO_STAGE`
- NO entry in `_BUNDLES` / `_BUNDLED_DIR_TO_STAGE`
- NO `wrap_with_preamble` involvement

V4 결정 #9 explicitly allows "단순 IO·AskUserQuestion만 예외." eject's
behavior is: parse args → resolve paths → AskUserQuestion (only on
destination conflict) → atomic copytree → print summary. Zero analytical
reasoning, zero LLM judgment in the IO path. Main Claude reads
`docs/eject-flow.md` and follows deterministic steps.

Decision rationale: eject is a *user-invoked utility* invoked OUTSIDE
the V3 concierge flow (a user types `/assemble eject plan-pack` directly,
not "I have an idea, recommend tools"). Promoting it to a sub-agent
pipeline would (a) add allowlist/_PROMPT_TO_STAGE pressure for zero
benefit, (b) waste a fresh subagent context on copytree semantics that
are easier to verify directly in `server/eject.py` unit tests.

### Out of scope

- ❌ `roles.json` 파일 도입 — Spike XII+ candidate (separate spike B per user prompt)
- ❌ Phase G 빈손 컴 dogfood — Spike XIII (V4 release gate)
- ❌ `/assemble import` 명령 (역방향: 사용자 스킬 → 번들로 흡수) — V5
- ❌ Multi-bundle eject (single command ejecting multiple bundles atomically) — V5
- ❌ Cross-machine bundle distribution (npm-style registry, scp helpers) — V5
- ❌ Auto git-init / git-track for ejected destination — V5
- ❌ Codex CLI / Gemini CLI 호환 — V4 비범위 (V5 어댑터 트랙)
- ❌ Frontmatter mutation on copy (e.g., flipping `name:` to a custom string) — eject is **pure copy**; user edits after
- ❌ Removal/disabling of source bundled copy after eject — both coexist; user manages
- ❌ Shared `_template_helpers.py` extraction — Spike XII does NOT add a 4th template-test site, so deferred
- ❌ Multi-language version bumping / `roles.json` / multi-run concurrency — same V5 backlog as Spike X/XI
- ❌ F4 perf collapse (reviewer ★ deterministic shell) — separate spike, untouched here
- ❌ ★ standard bundle promotion (`reviewer ★`-style 자동 검증 hook for ANTI_PATTERNS) — Spike XI Tier-1 carryforward, untouched

---

## Phase A learnings to apply (Spike XI codebase enforcement scan boilerplate)

Per `project_assemble_v4_spec.md` § "Spec/plan 작성 전 codebase enforcement scan",
the following 7-item checklist was sanity-checked against master `10e2810`
*before* this spec was written. Pre-scan results (verbatim):

1. **Per-bundle wiring atomic with file creation** — N/A. eject ships
   *zero* new bundle prompts, so `ALLOWED_PROMPT_FILES` /
   `_PROMPT_TO_STAGE` / `_BUNDLES` / `_BUNDLED_DIR_TO_STAGE` are all
   untouched. Bidirectional integrity test (`test_dispatch_prompt.py
   ::test_allowed_prompt_files_matches_bundle_inventory`) keeps
   passing because the test auto-derives expected from disk and we add
   nothing new to disk under `bundled/*/prompts/{subagent,orchestrator}/`.
2. **STAGE_CATEGORY_PRIORITY** — N/A. eject does not introduce a new
   stage. 10 stages (debug/design/discover/execute/meta/plan/review/
   safety/ship/verify) cover everything; eject is meta-orthogonal
   (an admin command, not a stage).
3. **WROTE: contract** — N/A. eject has no dispatchable prompt body.
4. **Frontmatter convention** — N/A for eject itself (no SKILL.md
   added). However: Phase D dogfood verifies that the *ejected output*'s
   SKILL.md still passes `test_yaml_strict_load.py` (because copy is
   byte-faithful, this is automatic; the test just needs to be able to
   re-discover the ejected file under a tempdir-rooted scan, which
   we do not exercise — eject test sets `ASSEMBLE_HOME=<tempdir>` and
   checks file presence + frontmatter parses cleanly via `yaml.safe_load`).
5. **ALLOWED_PROMPT_FILES + _PROMPT_TO_STAGE = BASENAMES** — N/A
   (no entries added).
6. **Template section count 실측** — N/A (no templates added).
7. **Pytest baseline 실측** — measured `789 passed in 17.62s` on
   master `10e2810`, captured as plan baseline. `+N` projection per
   Phase below; live target on B-17 ship commit ≥ 803 (789 + at
   least 14 new eject unit tests).

This is the lightest enforcement scan footprint of any V4 spike to
date — eject's V4 #9 exception status keeps it out of the
allowlist/dispatch contract surface entirely.

---

## Module — `server/eject.py` (Phase A, ~150 LoC)

Single new Python module. Pure functions, deterministic, no I/O side-effects
in the resolver layer. `apply_eject` is the only side-effect function; uses
atomic temp-dir + rename so partial failures leave no half-copied state.

### API surface

```python
# server/eject.py
from pathlib import Path
from typing import NamedTuple

class EjectError(Exception):
    """Base exception for eject failures with a human-readable reason."""

class EjectPlan(NamedTuple):
    """Result of dry_run_plan — files that would be copied + warnings."""
    src: Path
    dest: Path
    bundle_name: str
    files: list[Path]              # absolute paths under src
    total_bytes: int
    dest_exists: bool              # True iff dest dir already exists pre-apply
    warnings: list[str]            # e.g., "destination already contains a SKILL.md"

def assemble_root(home: Path | None = None) -> Path:
    """Returns ~/.claude/skills/assemble (or $ASSEMBLE_HOME-rooted equivalent)."""

def available_bundles(home: Path | None = None) -> list[str]:
    """Sorted list of bundle directory names under assemble/bundled/.
    Excludes _shared and any dir starting with `_` or `.`.
    """

def resolve_source(bundle_name: str, home: Path | None = None) -> Path:
    """Returns absolute Path to bundled/<bundle_name>/. Raises EjectError if
    not found, with the available list in the message."""

_RESERVED_NAMES = frozenset({"assemble", "_shared"})
_NAME_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"

def validate_dest_name(name: str) -> str:
    """Returns canonical name on success. Raises EjectError on:
      - empty / whitespace-only
      - path separator (/, \\)
      - reserved name
      - regex mismatch (lowercase letter start, then [a-z0-9_-], len ≤ 64)
    """

def resolve_dest(name: str, home: Path | None = None) -> Path:
    """Returns ~/.claude/skills/<name>/ (validated). Does NOT create."""

def dry_run_plan(bundle_name: str, dest_name: str, home: Path | None = None) -> EjectPlan:
    """Walks src tree, builds file list, computes total size, peeks dest existence,
    emits warnings. Pure read-only — does not mutate anything."""

def apply_eject(plan: EjectPlan, *, overwrite: bool = False) -> EjectPlan:
    """Performs the copy. Returns the same plan (for chaining).

    Atomicity contract:
      1. Create temp dir under same parent as dest (`<dest>.tmp.<pid>.<rand>`)
      2. shutil.copytree(src, temp_dir/<bundle_basename_or_name>) — full tree
      3. If dest exists and overwrite=False → EjectError (caller must AskUserQuestion first)
      4. If dest exists and overwrite=True → atomic rename of dest to backup name first
      5. os.rename(temp_dir/<inner>, dest)
      6. Cleanup temp_dir
      7. On any exception: shutil.rmtree(temp_dir, ignore_errors=True), re-raise

    Implementation note: copy_function defaults to shutil.copy2 (preserves mtime,
    permissions, NOT ACL/xattr — Linux/macOS scope; assemble does not run on Windows).
    """
```

### Path resolution

- `assemble_root(home)`:
  - `home = home or Path(os.environ.get('ASSEMBLE_HOME', Path.home()))`
  - returns `home / '.claude/skills/assemble'`
  - tests pass tempdir as `home=` arg or set `ASSEMBLE_HOME=<tempdir>` env
  - **No alternate skills root** — destination always under `<home>/.claude/skills/`,
    matching `inventory.enumerate_skill_paths` semantics. This guarantees the
    ejected skill is automatically discoverable by inventory after copy.

### Available bundles (Phase A: deterministic list)

```python
def available_bundles(home: Path | None = None) -> list[str]:
    bundled_root = assemble_root(home) / "bundled"
    if not bundled_root.is_dir():
        return []
    return sorted(
        p.name for p in bundled_root.iterdir()
        if p.is_dir()
        and not p.name.startswith("_")
        and not p.name.startswith(".")
    )
```

Expected on master `10e2810`: `['builder', 'debugger', 'design-pack',
'guardian', 'idea-shaper', 'keeper', 'plan-pack', 'reviewer', 'shipper',
'verifier']` — exactly the 10 bundles from V4 결정 #1.

### Destination name validation

Three guards (deny-by-default):

1. **Reserved**: name ∈ {`assemble`, `_shared`}. Reason: collision with
   the assemble skill itself or the shared infra dir. (`_shared` is
   not actually a user-skill candidate but we deny anyway for hygiene.)
2. **Path-traversal / separator**: name contains `/`, `\\`, or `..`.
3. **Regex**: must match `^[a-z][a-z0-9_-]{0,63}$`. Lowercase to match
   POSIX file conventions (`~/.claude/skills/<name>/SKILL.md` is
   case-sensitive on macOS APFS-by-default-case-insensitive but
   case-sensitive on Linux ext4). Forcing lowercase removes a class of
   case-collision footguns.

EjectError message includes both the reason and the offending input.
No silent normalization (no auto-lowercase) — returns `name` verbatim
on success, raises on any deviation.

### Atomic apply (the only side-effect function)

The 7-step contract above is **invariant** — preserved across implementation
revisions. Single test (`test_apply_eject_atomic_failure_no_partial_state`)
forces an exception inside the copy via a monkeypatched `shutil.copytree`
to assert the dest never gets a partial-tree.

Backup-on-overwrite: when `overwrite=True` and dest exists, we rename
dest to `<dest>.bak.<timestamp>` *before* renaming the temp tree to dest.
This means an interrupted overwrite leaves a `.bak.<ts>` survivor for
manual recovery — better than `rm -rf` and trusting the new copy.

The `.bak.<timestamp>` survivors are NOT auto-cleaned. User must remove
manually. SKILL.md doc surface in `docs/eject-flow.md` mentions this.

---

## Orchestrator flow — `docs/eject-flow.md` (Phase C, ~80 LoC)

Single doc file read by main Claude when the SKILL.md sub-command router
detects an `eject ...` arg. Layout:

```
# /assemble eject — flow

## Args
   eject <bundle> [--name <custom-name>] [--dry-run] [--force]

## Step 1 — parse
   - bundle: required positional, must be in `available_bundles()`
   - --name: optional override for destination dir name (default: bundle)
   - --dry-run: print plan + exit, no FS mutation
   - --force: bypass conflict AskUserQuestion (still emits backup)

## Step 2 — resolve
   1. Run `from server.eject import resolve_source, validate_dest_name, resolve_dest, dry_run_plan`.
   2. `src = resolve_source(bundle)` — print "Source: <src>" or fail.
   3. `name = validate_dest_name(args.name or bundle)` — print "Dest name: <name>" or fail.
   4. `dest = resolve_dest(name)` — print "Dest path: <dest>".
   5. `plan = dry_run_plan(bundle, name)` — print summary table:
        - files: <count>
        - bytes: <human>
        - dest_exists: <bool>
        - warnings: <each on own line>

## Step 3 — confirm (only if dest exists AND --force not set)
   - AskUserQuestion question: "Destination <dest> already exists. Overwrite?"
   - 3 options: [Cancel] / [Overwrite (backup created)] / [View dest contents first]
   - "View" path: list files under dest, then re-ask same question.
   - "Cancel": print "Eject cancelled" and stop.

## Step 4 — apply (skipped if --dry-run)
   - `apply_eject(plan, overwrite=<from confirm>)` — print "Ejected → <dest>".
   - If exception raised: print error + suggest --dry-run to inspect first.

## Step 5 — post-eject hint
   Print:
     "Ejected skill ready at: <dest>"
     "Inventory will pick it up on next /assemble run (source: user)."
     "Original bundle remains at: <src> (still selectable as ★ bundled)."
     "Customize freely. References to assemble.server.* won't resolve outside the assemble harness — see docs/eject-flow.md §Limitations."
```

### Limitations note (in eject-flow.md)

The doc has a `## Limitations` section that documents:

- Ejected SKILL.md may reference `from server.harness import wrap_with_preamble`
  or `~/.claude/skills/assemble/bundled/_shared/harness-preamble.md` — these
  paths only resolve inside the assemble harness. User must adapt.
- ★ bundles' Bash-grant subagent prompts assume `dispatch_and_record`
  routing — outside assemble these are just .md files.
- Templates with `{{PLACEHOLDER}}` pattern still work; user just
  substitutes manually or via their own subagent.
- contracts.json and SECURITY.md are copied verbatim but contain
  references to V4 spike documentation paths that won't resolve
  outside the assemble repo.

This is **documentation, not enforcement**. eject's job is to produce
a faithful copy, not to lobotomize the bundle.

---

## SKILL.md branch — sub-command router (Phase C, ~30 LoC)

Insert a new `## Sub-commands` section near the top of `~/.claude/skills/assemble/SKILL.md`,
between current `## 0. Prerequisites` and `## 1. Boot`. Keep V3 concierge
flow as the default (no behavior change for `/assemble <task>` invocations).

```markdown
## Sub-commands

After §1 Boot extracts the task token, additionally check for sub-command
keywords. If matched, route to the corresponding flow doc and STOP §2~§7
default concierge flow:

| Keyword (first arg token) | Flow doc | Spike |
|---|---|---|
| `eject` | `~/.claude/skills/assemble/docs/eject-flow.md` | XII |
| (future) `roles` | (deferred) | — |
| (future) `import` | (deferred) | V5 |

Behavior: if first token after `/assemble` is a sub-command keyword,
read the flow doc and follow it line-by-line. Default concierge flow
(§2 inventory refresh through §7 list) is bypassed.

If no sub-command keyword matches, proceed to §1 Boot's existing
`resume`/`list`/task-string routing.
```

This preserves backward compatibility: any current `/assemble <free task>`
invocation still routes to V3 concierge unchanged. Only the new
keyword `eject` triggers the new flow.

### Why sub-command routing in SKILL.md (not a separate skill)

User explicitly directed: "**eject은 새 명령이라 새 파일들**: server/eject.py
... 또는 SKILL.md 본체에 분기 추가". Decision = SKILL.md branch
(simpler, single-skill UX, no extra installation step). Reasoning:

- A separate `~/.claude/skills/assemble-eject/` skill would force
  the user to memorize TWO slash commands (`/assemble` and
  `/assemble-eject`).
- Sub-command routing is the canonical Claude Code pattern (e.g.,
  `/git status` vs `/git diff`).
- Future `roles` / `import` sub-commands extend the same router with
  zero new top-level skills.

Trade-off: SKILL.md grows by ~30 LoC. Acceptable given V3 concierge
flow remains untouched.

---

## Tests — `tests/unit/test_eject.py` (Phase B, ~14 cases)

| # | Test | Asserts |
|---|---|---|
| 1 | `test_assemble_root_default_home` | `assemble_root()` returns `~/.claude/skills/assemble` |
| 2 | `test_assemble_root_with_explicit_home` | `assemble_root(home=Path('/tmp/x'))` returns `/tmp/x/.claude/skills/assemble` |
| 3 | `test_assemble_root_respects_env_var` | `ASSEMBLE_HOME=/tmp/y` makes `assemble_root()` return `/tmp/y/.claude/skills/assemble` |
| 4 | `test_available_bundles_lists_disk_dirs` | with tempdir mocking 3 bundle dirs + `_shared` + `.git`, returns `['a', 'b', 'c']` (sorted, excludes `_*` and `.*`) |
| 5 | `test_available_bundles_returns_empty_when_no_bundled_dir` | tempdir without bundled subdir → `[]` (no exception) |
| 6 | `test_resolve_source_known_bundle` | known name → returns abs Path |
| 7 | `test_resolve_source_unknown_raises_with_available_list` | unknown name → EjectError mentions both unknown and 'Available:' list |
| 8 | `test_validate_dest_name_accepts_canonical` | `'foo-bar_2'` returns `'foo-bar_2'` |
| 9 | `test_validate_dest_name_rejects_reserved_assemble` | `'assemble'` raises EjectError |
| 10 | `test_validate_dest_name_rejects_path_separator` | `'foo/bar'` and `'..'` and `'foo\\bar'` all raise |
| 11 | `test_validate_dest_name_rejects_uppercase_or_invalid_chars` | `'Foo'`, `'foo bar'`, `'1foo'`, `''` all raise |
| 12 | `test_dry_run_plan_lists_files_and_size` | tempdir bundle with 3 files (SKILL.md / template / prompt) → plan.files len 3, total_bytes > 0, dest_exists=False |
| 13 | `test_dry_run_plan_warns_on_dest_collision` | dest already exists → plan.dest_exists=True, warnings non-empty |
| 14 | `test_apply_eject_creates_dest_skill_and_preserves_source` | apply on tempdir bundle → dest tree matches src tree (SHA-256 of each file equal); source unmodified (mtime + sha unchanged) |
| 15 | `test_apply_eject_overwrite_creates_backup` | dest exists + overwrite=True → backup `<dest>.bak.<ts>` exists, dest replaced cleanly |
| 16 | `test_apply_eject_atomic_failure_no_partial_state` | monkeypatched copytree raises mid-tree → dest does NOT exist after exception (no partial copy left) |
| 17 | `test_apply_eject_inventory_integration` | apply via `ASSEMBLE_HOME=<tempdir>`, then `inventory.enumerate_skill_paths(home=<tempdir>)` includes the ejected SKILL.md (verifies post-eject discoverability) |

Total = 17 tests. Pre-scan baseline 789 → projected 806 on Phase B
green. Phase D dogfood adds 1 more (B-17 contract probe), so ship
target ≥ 807. Plan/spec reconciliation will trim tests if any are
redundant (e.g., #1+#2+#3 may collapse to a single parametrized test).

### Test fixtures

Single shared `tempdir_assemble_home` fixture:

```python
@pytest.fixture
def tempdir_assemble_home(tmp_path, monkeypatch):
    """Creates ~/.claude/skills/assemble/bundled/{a,b,c}/ scaffolding under
    tmp_path. Each scaffolded bundle has SKILL.md + 1 template file.
    Sets ASSEMBLE_HOME env var to tmp_path."""
    home = tmp_path
    bundled = home / ".claude/skills/assemble/bundled"
    for name in ("a", "b", "c"):
        d = bundled / name
        (d / "templates").mkdir(parents=True)
        (d / "SKILL.md").write_text(f'---\nname: "{name}"\ndescription: "test"\n---\n')
        (d / "templates" / "x.md.template").write_text("# X\n")
    (bundled / "_shared").mkdir()  # excluded
    monkeypatch.setenv("ASSEMBLE_HOME", str(home))
    return home
```

This fixture mirrors the real `bundled/` layout shape but with throwaway
content. Real `bundled/idea-shaper/` etc. are NOT mutated by tests.

---

## B-17 dogfood (Phase D, ship gate)

Single self-execute run, modeled after Spike X B-15's tempdir-rooted approach.

### Setup

1. Create `tmp/spike-xii-b17/` tempdir.
2. Copy a single source bundle (`idea-shaper` — smallest, standard grade,
   no Bash-grant complexity) to `tmp/spike-xii-b17/.claude/skills/assemble/bundled/idea-shaper/`.
3. Set `ASSEMBLE_HOME=tmp/spike-xii-b17` env.
4. Invoke `apply_eject(dry_run_plan('idea-shaper', 'idea-shaper'))`.

### 12 acceptance criteria

| # | Check | PASS condition |
|---|---|---|
| AC1 | Source unmodified | SHA-256 of every file under `bundled/idea-shaper/` equal pre+post |
| AC2 | Dest tree exists | `<home>/.claude/skills/idea-shaper/` is a dir with SKILL.md |
| AC3 | File count match | `count(<dest>/**/*) == count(<src>/**/*)` |
| AC4 | Per-file SHA match | for every file in src, dest has matching SHA-256 |
| AC5 | mtime preservation | dest SKILL.md mtime within 1s of src (copy2 contract) |
| AC6 | Frontmatter still parses | `yaml.safe_load(<dest>/SKILL.md frontmatter)` returns dict |
| AC7 | `test_yaml_strict_load` re-runs green against dest | reuse the test's helpers, assert no errors |
| AC8 | `test_yaml_strict_load` count = pre+1 | because ejected adds 1 SKILL.md to bundled scan? **NO** — eject puts dest OUTSIDE bundled, so test_yaml_strict_load count unchanged. AC8 = test_yaml_strict_load passes against the dest path manually |
| AC9 | Inventory scan finds ejected | `inventory.enumerate_skill_paths(home=<home>)` returns list including `<home>/.claude/skills/idea-shaper/SKILL.md` |
| AC10 | Inventory marks ejected as `bundled=False` | scan output entry for ejected has `bundled=False` (not under `assemble/bundled/`) |
| AC11 | Source still appears in inventory as `bundled=True` | scan output entry for source has `bundled=True` (still under `assemble/bundled/`) |
| AC12 | dry_run does not mutate FS | `dry_run_plan` followed by NOT calling `apply_eject` leaves dest non-existent; recompute file list of src → unchanged |

### Wall-time budget

≤30s for all 12 AC. Reference: Spike XI B-16 = 0.422s, Spike X B-15 =
0.26s. eject is even simpler (copytree benchmarks) — projecting ≤2s.

### Self-execute mode

B-17 is invoked as a single Python subprocess (no real /assemble
invocation needed — the goal is to verify the eject *module*, not the
slash-command UX). UX validation is deferred to Spike XIII (blank-Mac
dogfood will exercise SKILL.md routing path).

```bash
cd ~/.claude/skills/assemble && \
  python3 -m pytest tests/unit/test_eject.py -v && \
  python3 -m tests.dogfood.spike_xii_b17  # NEW dogfood probe
```

---

## V4 정체성 보호 (변경 X)

- ✅ Spike I~XI core contracts unchanged
- ✅ canonical preamble v3 sha unchanged: `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9`
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged
- ✅ V3 concierge menu layer unchanged (sub-command router is additive — default flow unchanged)
- ✅ ALLOWED_PROMPT_FILES = 42 entries unchanged (no new prompts)
- ✅ _PROMPT_TO_STAGE = 42 entries unchanged
- ✅ STAGE_CATEGORY_PRIORITY 10-stage map unchanged
- ✅ _BUNDLES / _BUNDLED_DIR_TO_STAGE unchanged (no new bundles)
- ✅ 7 ★ bundle prompts unchanged (plan-pack/debugger/builder/reviewer/verifier/shipper/keeper)
- ✅ 3 표준 bundle prompts unchanged (idea-shaper/design-pack/guardian)
- ✅ orchestrator-only V4 #9 — eject is V4 #9 explicit exception (main IO + AskUserQuestion only)
- ✅ scope_parser deterministic helper unchanged
- ✅ universal-defense convention unchanged
- ✅ harness.py / inventory.py public API unchanged (no signature changes; eject lives in its own module)

---

## Surgical change boundary (harness 4원칙 #3)

| File | Change kind | Lines |
|---|---|---|
| `server/eject.py` | NEW | ~150 |
| `server/__init__.py` | facade re-export of `eject_bundle` namespace? | **NO** — eject does not need facade access; orchestrator imports `from server.eject import ...` directly. Skip facade for now. |
| `tests/unit/test_eject.py` | NEW | ~250 |
| `tests/dogfood/spike_xii_b17.py` | NEW | ~120 |
| `docs/eject-flow.md` | NEW | ~80 |
| `SKILL.md` | INSERT § Sub-commands | ~30 LoC inserted |
| `CHANGELOG.md` | append entry under [Unreleased] | ~15 LoC |
| `docs/specs/2026-05-05-v4-spike-xii-design.md` | NEW (this file) | — |
| `docs/plans/2026-05-05-v4-spike-xii.md` | NEW | — |

**Total touched files**: 9 (8 NEW + 1 EDIT). Surgical scope honored.
No edits to existing server/* modules (harness.py, inventory.py,
learnings.py, scope_parser.py, etc.) — eject is a pure additive
module that other code does not import.

---

## Reasoning — Codex retro skip (standard-grade decision)

Per V4 결정 #7, standard-grade work has Codex retro **선택**. Spike XI
skipped Codex retro for all 3 standard bundles. eject is a single
small utility (~150 LoC + tests + 1 doc), simpler than any standard
bundle. Codex retro skip rationale:

- Bash surface = **0** in main code (apply_eject uses `shutil.copytree`,
  not `subprocess`). Lower threat surface than any ★ bundle.
- No SCOPE.md / parsed_scope.json consumption.
- No ledger / learnings interaction.
- No subprocess / streaming-cap / killpg / process-group concerns.
- Trust model: SCOPE author = user invoking eject. They already chose
  to copy a bundle. No external attack surface.

If E1 superpowers:code-reviewer flags any of: (a) atomic-rename TOCTOU
race, (b) backup-name collision, (c) shutil.copy2 metadata
preservation gaps on macOS APFS — promote to Codex retro for
adversarial second-opinion. Otherwise standard E1-only review is
sufficient.

---

## Phase mapping (commit prefixes for plan)

| Phase | Scope | Task count | Commit prefix |
|---|---|---|---|
| A | server/eject.py + facade decision | 1 | `feat(v4-spike-xii-A)` |
| B | tests/unit/test_eject.py (17 cases) | 1 | `test(v4-spike-xii-B)` |
| C | docs/eject-flow.md + SKILL.md branch | 1 | `feat(v4-spike-xii-C)` |
| D | tests/dogfood/spike_xii_b17.py + ship gate run | 1 | `test(v4-spike-xii-D)` |
| E | overall review (superpowers:code-reviewer) | 1 | `fix(v4-spike-xii-E)` (필요시) |
| F | CHANGELOG flip + ship | 1 | `docs(v4-spike-xii)` |

Sequential ordering. A/B can in principle parallel-author (server +
tests independent) but TDD discipline (B follows A green) keeps them
serial. Phase C touches SKILL.md AND docs/eject-flow.md atomically
(sub-command keyword and its flow doc must land together to avoid
broken router).

Total: **6 tasks**, ~6 atomic commits + 1 ship commit + spec/plan
prelude commit = ~8 commits including reconciliation/cleanup.

---

## Carryforward openness

After ship, these candidates inherit to Spike XIII (blank-Mac dogfood)
or beyond:

- Symlink mode (`/assemble eject --link <bundle>`) — instead of copy,
  ln -s for live-track of bundle updates. Decision: V5 candidate.
  Conflicts with "free customization" semantic.
- Auto-rename on conflict (`--name auto` → `<bundle>-1`, `<bundle>-2`,
  ...). Decision: V5.
- `eject --list` to print available bundles without ejecting. Maybe
  Spike XIII bundles. Decision: deferred (`/assemble list` already
  shows installed skills; redundant for V4).
- Frontmatter rewrite on copy (e.g., flip `name:` to dest name).
  Decision: V5; pure-copy semantic preserved for V4.
- Trace ledger entry for eject events (so keeper ★ can audit who
  ejected what when). Decision: V5; keeper currently audits run-dir
  artifacts, not admin commands.

---

## Source

- Spec: this file
- Plan: `docs/plans/2026-05-05-v4-spike-xii.md`
- Parent: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
- Sibling: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_xi.md`
- Pre-scan: master `10e2810`, pytest 789, ALLOWED_PROMPT_FILES count 42, STAGE_CATEGORY_PRIORITY 10 stages
