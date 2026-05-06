# Spike XIV B-20a — Automated Blank-Environment Sanity Probe

**Date**: 2026-05-06T14:57:29+0900
**Verdict**: SHIP
**Wall-time**: 0.531s
**Pytest baseline (host)**: 833 passed (T7)

## ACs (18 total)

| # | Name | Status | Evidence |
|---|------|--------|----------|
| AC1 | tempdir setup | PASS | assemble + 10 bundles + _shared (_shared exists=True) |
| AC2 | inventory.scan ≥10 | PASS | scan() returned 11 skills |
| AC3 | bundled=True flag | PASS | all 10 bundled entries flagged bundled=True |
| AC4 | menu render + fallback hint | PASS | 1 ★ tool(s) + 1 fallback hint(s) |
| AC5 | frontmatter strict-load | PASS | 10/10 bundle frontmatter parsed |
| AC6 | bidirectional integrity | PASS | 49 ALLOWED == 49 on-disk |
| AC7 | _PROMPT_TO_STAGE ⊆ STAGE_KEYS | PASS | 9 prompt stages all in 10 known stages |
| AC8 | WROTE: contract on dispatchable prompts | PASS | 45 prompts have WROTE:, 4 helper-exempt (iter_revisit/iter_emphasis), total 49/49 |
| AC9 | canonical preamble v3 sha invariant | PASS | sha = 8d22a29c9712d2c0… (expected 8d22a29c9712d2c0…) |
| AC10 | ALLOW_LIST sha values valid | PASS | v1/v2/canonical all 64-char sha (v1_ok=True, v2_ok=True, v3_ok=True) |
| AC11 | ALLOWED_PROMPT_FILES == 49 | PASS | actual = 49 (expected 49 after Phase B added 7 quick prompts) |
| AC12 | _BUNDLES & _BUNDLED_DIR_TO_STAGE = 10/10 | PASS | _BUNDLES=10, _BUNDLED_DIR_TO_STAGE=10 |
| AC13 | Phase A: ASSEMBLE_HOME body injection | PASS | set→[ENV] line present, unset→no [ENV] line |
| AC14 | Phase B: ★ mode-gate (7 bundles) | PASS | 7/7 ★ bundles have 3 grep markers |
| AC15 | Phase C: plan-pack Recommendation policy | PASS | section + iter≤3 algorithm + forbidding wording all present |
| AC16 | Phase D: mark_orthogonal_stage runtime | PASS | import OK + safety/meta marked → orthogonal_stages populated |
| AC17 | Phase E: dispatch_prompt signature drift | PASS | pytest returncode=0 — drift 0 |
| AC18 | preamble v3 sha preserved (cross-check) | PASS | sha=8d22a29c9712d2c0… == expected, stable across Phase A round-trip |

**Pass count**: 18/18

## Identity snapshot

```json
{
  "ALLOWED_PROMPT_FILES_count": 49,
  "ORCHESTRATOR_ONLY_PROMPTS_count": 3,
  "STAGE_CATEGORY_PRIORITY_count": 10,
  "_BUNDLED_DIR_TO_STAGE_count": 10,
  "_BUNDLES_count": 10,
  "_PROMPT_TO_STAGE_count": 49,
  "canonical_preamble_v3_sha": "8d22a29c9712d2c0",
  "preamble_v1_sha": "858e9ff1cdc05ca7",
  "preamble_v2_sha": "df27450513c019a9"
}
```

## Phase A~E fix coverage

| Phase | AC | Status |
|-------|----|--------|
| A (C1 — ASSEMBLE_HOME injection) | AC13, AC18 | PASS |
| B (C2/I2 — mode-gate) | AC14 | PASS |
| C (I1 — Recommendation policy) | AC15 | PASS |
| D (I3 — orthogonal stage marker) | AC16 | PASS |
| E (I4 — dispatch_prompt signature drift) | AC17 | PASS |

## Evidence (full)

```json
{
  "_BUNDLED_DIR_TO_STAGE_count": 10,
  "_BUNDLES_count": 10,
  "ac8_helper_exempt": 4,
  "ac8_wrote_count": 45,
  "allow_list_shas": {
    "v1": "858e9ff1cdc05ca7",
    "v2": "df27450513c019a9",
    "v3": "8d22a29c9712d2c0"
  },
  "allowed_prompt_files_count": 49,
  "bundle_count": 10,
  "bundle_names": [
    "builder",
    "debugger",
    "design-pack",
    "guardian",
    "idea-shaper",
    "keeper",
    "plan-pack",
    "reviewer",
    "shipper",
    "verifier"
  ],
  "canonical_preamble_sha": "8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9",
  "identity_snapshot": {
    "ALLOWED_PROMPT_FILES_count": 49,
    "ORCHESTRATOR_ONLY_PROMPTS_count": 3,
    "STAGE_CATEGORY_PRIORITY_count": 10,
    "_BUNDLED_DIR_TO_STAGE_count": 10,
    "_BUNDLES_count": 10,
    "_PROMPT_TO_STAGE_count": 49,
    "canonical_preamble_v3_sha": "8d22a29c9712d2c0",
    "preamble_v1_sha": "858e9ff1cdc05ca7",
    "preamble_v2_sha": "df27450513c019a9"
  },
  "mode_gate_per_bundle": {
    "builder": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    },
    "debugger": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    },
    "keeper": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    },
    "plan-pack": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    },
    "reviewer": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    },
    "shipper": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    },
    "verifier": {
      "mode_gate": true,
      "no_shortcut": true,
      "quick_mode_flow": true
    }
  },
  "on_disk_prompt_count": 49,
  "plan_options_sample": [
    {
      "bundled": true,
      "kind": "tool",
      "label": "★ plan-pack"
    },
    {
      "bundled": null,
      "kind": "ask",
      "label": "ask"
    },
    {
      "bundled": null,
      "kind": "skip",
      "label": "skip"
    },
    {
      "bundled": null,
      "kind": "manual",
      "label": "manual"
    },
    {
      "bundled": null,
      "kind": "back",
      "label": "back"
    },
    {
      "bundled": null,
      "kind": "done",
      "label": "done"
    }
  ],
  "scan_skill_count": 11,
  "scan_skill_names": [
    "assemble",
    "builder",
    "debugger",
    "design-pack",
    "guardian",
    "idea-shaper",
    "keeper",
    "plan-pack",
    "reviewer",
    "shipper",
    "verifier"
  ],
  "stage_keys": [
    "debug",
    "design",
    "discover",
    "execute",
    "meta",
    "plan",
    "review",
    "safety",
    "ship",
    "verify"
  ],
  "tempdir": "/var/folders/0b/8dkyz1_j11dg6vfrrd0rk4fc0000gn/T/spike-xiv-b20a-gjx8796p"
}
```

## Tempdir layout sketch

```
/var/folders/0b/8dkyz1_j11dg6vfrrd0rk4fc0000gn/T/spike-xiv-b20a-gjx8796p/
└── .claude/
    └── skills/
        └── assemble/      # only skill present (blank env)
            ├── SKILL.md
            ├── bundled/   # 10 bundles + _shared
            └── server/
```
