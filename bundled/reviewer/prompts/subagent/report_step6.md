# reviewer Step 6 — REVIEW_REPORT.md write
You are dispatched as reviewer Step 6 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Inputs

- run_id: `{{RUN_ID}}`
- parsed_scope_path: `runs/{{RUN_ID}}/parsed_scope.json`
- diff_inventory_path: `runs/{{RUN_ID}}/diff_inventory.json`
- classification_path: `runs/{{RUN_ID}}/classification.json`
- rule3_audit_path: `runs/{{RUN_ID}}/rule3_audit.json`
- severity_grid_path: `runs/{{RUN_ID}}/severity_grid.json`
- template_path: `bundled/reviewer/templates/REVIEW_REPORT.md.template`

## Goal

Read all 5 input JSONs + template; render `runs/{{RUN_ID}}/REVIEW_REPORT.md` by substituting placeholders.

## Placeholder substitutions

| Placeholder | Source |
|---|---|
| `{{RUN_ID}}` | input arg |
| `{{VERDICT}}` | `severity_grid.verdict` |
| `{{VERDICT_REASON}}` | `severity_grid.verdict_reason` |
| `{{SCOPE_ALLOW}}` | `parsed_scope.allow` formatted as bullet list |
| `{{SCOPE_DENY}}` | `parsed_scope.deny` formatted as bullet list |
| `{{COMPLETION_CRITERION}}` | `parsed_scope.completion` |
| `{{DIFF_FILES}}` | `diff_inventory.files` formatted as table (path / status / +added / -removed) |
| `{{CLASSIFICATION_BODY}}` | `classification.files` formatted as bullet list (path → verdict → matched_rule) + `allow_misses` section |
| `{{RULE3_BODY}}` | `rule3_audit.files` formatted as bullet list (path → verdict → severity → evidence) |
| `{{SEVERITY_BODY}}` | severity_grid critical/major/minor counts + bullet lists |
| `{{RECOMMENDATIONS}}` | derived from severity_grid: ordered fix-actions OR "ready to merge" |

## Recommendations derivation

If verdict == `merge-ready`:
```
- ✅ Ready to merge. Run completion criterion to confirm: `<completion>`.
```

Else, list fixes in priority order:
1. For each deny-violation: `- ❌ Resolve deny-violation: revert changes to <path> (<rule>).`
2. For each critical Rule 3: `- ❌ Critical Rule 3: <path> — <evidence>. Either expand SCOPE allow list or revert.`
3. For each allow-miss: `- ⚠️ Allow-miss: <path> — expected change not present. Verify SCOPE.md is current.`
4. For major Rule 3: `- ⚠️ Cosmetic drift: <path> — confirm intentional or revert.`

## Constraints

- Use template literally — do not regenerate the section structure.
- Use stdlib only.
- Output written via file write; print `WROTE: <abs path>` last.
