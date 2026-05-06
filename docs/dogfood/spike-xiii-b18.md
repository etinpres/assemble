# Spike XIII B-18 — blank-environment sanity probe


- **Run timestamp**: 2026-05-06T09:16:56+0900
- **Wall-time**: 0.310s (budget ≤30s)
- **Pass count**: 12/12
- **Verdict**: SHIP

## Per-AC verdict

| # | Status | Message |
|---|--------|---------|
| AC1 | PASS | tempdir has assemble + 10 bundles + _shared (_shared exists=True) |
| AC2 | PASS | scan() returned 11 skills (names=['assemble', 'builder', 'debugger', 'design-pack', 'guardian', 'idea-shaper', 'keeper', 'plan-pack', 'reviewer', 'shipper', 'verifier']) |
| AC3 | PASS | all 10 bundled entries have bundled=True |
| AC4 | PASS | user skill count = 0 (non-bundled entries=['assemble']) |
| AC5 | PASS | plan stage rendered 1 ★-prefixed bundled tool(s) (labels=['★ plan-pack']) |
| AC6 | PASS | bundled-only fallback hint present on 1 option(s) |
| AC7 | PASS | 10/10 bundle frontmatter parsed |
| AC8 | PASS | 42 entries match on-disk prompts (no drift) |
| AC9 | PASS | 31 contracts loaded with required schema |
| AC10 | PASS | canonical preamble sha = 8d22a29c9712d2c0… (expected 8d22a29c9712d2c0…) |
| AC11 | PASS | ## Sub-commands section + eject keyword + flow doc all present (section=True, keyword=True, flow_doc=True) |
| AC12 | PASS | doc written to /Users/yonghaekim/.claude/skills/assemble/docs/dogfood/spike-xiii-b18.md (2906B) |

## Evidence

```json
{
  "allowed_prompt_files_count": 42,
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
  "contract_count": 31,
  "identity_snapshot": {
    "ALLOWED_PROMPT_FILES_count": 42,
    "ORCHESTRATOR_ONLY_PROMPTS_count": 3,
    "canonical_preamble_v3_sha": "8d22a29c9712d2c0"
  },
  "non_bundled_entries": [
    "assemble"
  ],
  "on_disk_prompt_count": 42,
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
  "tempdir": "/var/folders/0b/8dkyz1_j11dg6vfrrd0rk4fc0000gn/T/spike-xiii-b18-rq2yqa7p",
  "user_skills": []
}
```

## Tempdir layout sketch

```
/var/folders/0b/8dkyz1_j11dg6vfrrd0rk4fc0000gn/T/spike-xiii-b18-rq2yqa7p/
└── .claude/
    └── skills/
        └── assemble/      # only skill present (blank env)
            ├── SKILL.md
            ├── bundled/   # 10 bundles + _shared
            └── server/
```
