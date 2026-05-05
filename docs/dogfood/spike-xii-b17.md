# V4 Spike XII B-17 Dogfood Report

**Date**: 2026-05-05
**Mode**: self-execute (Spike VIII/IX/X/XI B-13/B-14/B-15/B-16 pattern — tempdir-rooted ASSEMBLE_HOME, real bundles untouched)
**Master HEAD pre-D**: `75144ff` (Phase A+B+C green)
**pytest baseline**: 812 passed, 1 skipped

## Summary

V4 Spike XII ship gate — `/assemble eject` validates pure-copy bundle-to-user-skill module against `idea-shaper` (smallest standard-grade bundle, no Bash-grant complexity).

**Verdict: 12/12 AC PASS — SHIP**
**Wall-time**: 0.018s (budget ≤30s — 1666× under, well under projected ≤2s)

## 12 AC Results

| # | AC | Status | Evidence |
|---|---|---|---|
| 1 | Source unmodified | PASS | source SHA-256 invariant (3 files) |
| 2 | Dest tree exists | PASS | `<tempdir>/.claude/skills/idea-shaper-ejected/` is dir with SKILL.md |
| 3 | File count match | PASS | src=3 dest=3 |
| 4 | Per-file SHA match | PASS | all 3 files SHA-256 byte-identical |
| 5 | mtime preservation | PASS | SKILL.md mtime delta = 0.000000s (≤ 1s, copy2 contract) |
| 6 | Frontmatter still parses | PASS | `yaml.safe_load` → dict (keys: description, grade, name, stages) |
| 7 | strict-yaml round-trip clean | PASS | mirrors `test_yaml_strict_load` semantics against dest path |
| 8 | bundled-scope count unchanged | PASS | bundled-scope `*/SKILL.md` count = 1 (ejected dest OUTSIDE bundled) |
| 9 | Inventory enumerate finds ejected | PASS | `enumerate_skill_paths` includes ejected (3 total entries) |
| 10 | scan: ejected `bundled=False` | PASS | `scan()['idea-shaper-ejected'].bundled = False` |
| 11 | scan: source `bundled=True` | PASS | `scan()['idea-shaper'].bundled = True` (still under `assemble/bundled/`) |
| 12 | dry_run does not mutate FS | PASS | pre-apply dest absent + src SHA snapshot unchanged |

## Raw probe output

```
[setup] tempdir = /var/folders/.../spike-xii-b17-_s8jwv3n
[AC1]  PASS: source SHA-256 invariant (3 files)
[AC2]  PASS: dest tree at <tempdir>/.claude/skills/idea-shaper-ejected has SKILL.md
[AC3]  PASS: file count src=3 dest=3
[AC4]  PASS: all 3 files SHA-256 byte-identical
[AC5]  PASS: SKILL.md mtime delta = 0.000000s (≤ 1s)
[AC6]  PASS: yaml.safe_load → dict (keys=['description', 'grade', 'name', 'stages'])
[AC7]  PASS: strict yaml round-trip clean (mirrors test_yaml_strict_load)
[AC8]  PASS: bundled-scope SKILL.md count = 1 (ejected dest is OUTSIDE bundled)
[AC9]  PASS: enumerate_skill_paths includes ejected (3 total)
[AC10] PASS: scan()['idea-shaper-ejected'].bundled = False
[AC11] PASS: scan()['idea-shaper'].bundled = True
[AC12] PASS: dry_run pre-apply: dest_absent=True src_unchanged=True

Wall-time: 0.018s (budget ≤30s)
12/12 AC PASS
VERDICT: SHIP
```

## Tempdir layout sketch

```
<tempdir>/
└── .claude/
    └── skills/
        ├── assemble/
        │   ├── SKILL.md                        # stub (so scan recognizes assemble itself)
        │   └── bundled/
        │       ├── _shared/                    # mirrored real preamble for identity check
        │       │   └── harness-preamble.md
        │       └── idea-shaper/                # SOURCE — copy of real bundled/idea-shaper
        │           ├── SKILL.md
        │           ├── prompts/subagent/idea_shape_step1.md
        │           └── templates/IDEA.md.template
        └── idea-shaper-ejected/                # DEST — written by apply_eject
            ├── SKILL.md                        # name field rewritten post-eject (see below)
            ├── prompts/subagent/idea_shape_step1.md
            └── templates/IDEA.md.template
```

## Source SHA-256 samples (pre/post invariant)

| File | SHA-256 (first 16 hex) |
|---|---|
| `idea-shaper/SKILL.md` | `b299ee3ec46abb04` |
| `idea-shaper/prompts/subagent/idea_shape_step1.md` | `a0e37bc2d236678f` |
| `idea-shaper/templates/IDEA.md.template` | `5af77144cade2f6e` |

Source SHAs measured pre-eject + post-eject — identical (AC1 PASS).
Dest SHAs match source 1:1 (AC4 PASS).

## mtime delta evidence (AC5)

```
src SKILL.md mtime  = T₀ (captured pre-eject)
dest SKILL.md mtime = T₀ (preserved by shutil.copy2)
delta              = 0.000000s
```

`shutil.copytree(..., copy_function=shutil.copy2)` preserves mtime to nanosecond precision on macOS/Linux. The 1s window in AC5 is a defensive tolerance for filesystems with second-only mtime resolution (e.g., FAT32); APFS easily clears it.

## V4 identity invariants snapshot (informational)

| Invariant | Value | Status |
|---|---|---|
| `ALLOWED_PROMPT_FILES` count | **42** | unchanged ✓ |
| `ORCHESTRATOR_ONLY_PROMPTS` count | **3** | unchanged ✓ |
| canonical preamble v3 sha | `8d22a29c9712d2c0…` | unchanged ✓ |

(eject is V4 #9 IO exception — additive module that does not touch the
allowlist / dispatch surface. Spec § "V4 정체성 보호" lists 13 invariants;
all preserved.)

## Implementation notes / deviations from spec

### 1. Dest name = `idea-shaper-ejected` (not `idea-shaper`)

The spec § B-17 sketches `dry_run_plan('idea-shaper', 'idea-shaper')` with
matching dest name, and notes "Both entries may have the same `name`
value (idea-shaper) but different paths and different `bundled` flags."

In practice, `inventory.scan()` keys its skills bucket by SKILL.md
``name:`` field (with dir-name fallback). With both source and ejected
sharing `name: "idea-shaper"`, scan's user-priority dedupe collapses
the two into one bucket entry, so AC10 (ejected bundled=False) and AC11
(source bundled=True) **cannot both** be observed through `scan()`
output simultaneously when names collide.

Resolution: eject to `dest_name = "idea-shaper-ejected"`. After
`apply_eject` returns (and AFTER all file-fidelity AC1-AC8 captures),
the probe rewrites the ejected SKILL.md's `name:` field from
`"idea-shaper"` → `"idea-shaper-ejected"`. This emulates real-world
post-eject user customization without violating eject's byte-faithful
contract (the rewrite happens outside the eject module's responsibility).

This matches the existing `tests/unit/test_eject.py::test_apply_eject_inventory_integration`
pattern (line 311), which ejects bundle `'a'` to dest `'inv-skill'` for
the same reason.

### 2. pytest count decision: standalone (812 unchanged)

Per task description, the "Bonus" question was whether to wire the
B-17 probe into pytest discovery (count → 813) or keep it standalone
(count stays 812).

**Decision: standalone**, invoked as `python3 -m tests.dogfood.spike_xii_b17`.

Rationale:
- Mirrors the spec § B-17 invocation contract verbatim.
- B-17 is a ship gate that validates the live filesystem path (real
  `bundled/idea-shaper` copy) rather than an isolated unit. Coupling
  to pytest would either (a) require fixtures that obscure the
  standalone runnable contract, or (b) duplicate the probe logic.
- `tests/dogfood/__init__.py` is created (empty) so the `-m` invocation
  resolves the package, but no `test_*.py` discovery target lives there
  — pytest's collector skips the `spike_xii_b17.py` filename.

Final pytest baseline: **812 passed, 1 skipped** (unchanged from pre-D HEAD `75144ff`).

### 3. Tempdir setup completeness

`scan()` requires:
- `<tempdir>/.claude/skills/assemble/SKILL.md` — stub written by the probe so the
  assemble skill itself is recognized (otherwise scan returns an empty
  skills bucket and AC10/AC11 trivially fail).
- `<tempdir>/.claude/skills/assemble/bundled/_shared/harness-preamble.md` —
  mirrored from the real shared dir so `canonical_preamble_sha256()` (called
  for the identity-snapshot evidence) returns the canonical hash rather
  than `None`.

Both auxiliary files are unrelated to AC1-AC12 themselves but are
needed for the identity-snapshot section of this report to render
meaningful values.

## Files added by Phase D

| File | Purpose |
|---|---|
| `tests/dogfood/__init__.py` | empty — package marker for `-m` invocation |
| `tests/dogfood/spike_xii_b17.py` | the B-17 probe (this run's source) |
| `docs/dogfood/spike-xii-b17.md` | this report |

No other files modified. `server/eject.py`, `server/inventory.py`,
existing tests, SKILL.md, CHANGELOG — all untouched.

## Carryforwards / observations

None blocking. Ship-ready.

Optional future improvements (not Spike XII scope):

- **C1 (V5 candidate)**: Add a `scan()` `home=` keyword argument so callers
  can override `ASSEMBLE_HOME` resolution without env-var mutation. Would
  let the dogfood probe avoid `os.environ` mutation. Low priority — the
  current env-var contract is documented in `_home_for_scan()` and works.
- **C2 (V5 candidate)**: Optional `eject` flag to rewrite SKILL.md `name:`
  field to match dest dir name when they differ. Would mean callers don't
  have to do the post-eject rewrite themselves for inventory-distinct
  visibility. Punt — current byte-faithful contract is the simpler default.

## Reproduction

```bash
cd ~/.claude/skills/assemble
python3 -m tests.dogfood.spike_xii_b17
# Expected: exit 0, 12/12 AC PASS, wall-time well under 1s
```
