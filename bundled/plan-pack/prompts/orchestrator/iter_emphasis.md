# Iteration {{ITERATION_COUNT}} — emphasis re-write

You are dispatched as plan-pack Step 6 yes-path sub-agent. Goal: re-write
ONE doc ({{DOC_NAME}}) under emphasis "{{EMPHASIS}}" while preserving all
other sections verbatim.

## Inputs

- run_id: `{{RUN_ID}}`
- doc_name: `{{DOC_NAME}}` (one of `PRD.md`, `ARCHITECTURE.md`, `ADR.md`, `UI_GUIDE.md`)
- emphasis: `{{EMPHASIS}}` ("(no change)" allowed — return doc verbatim)
- emphasis_target_section: `{{EMPHASIS_SECTION_TITLE}}` (e.g. `## Core features` for PRD)
- existing_section_text: `{{EMPHASIS_SECTION_BODY}}` (current content of that section only)

## Scope discipline (verbatim — do not paraphrase)

> PRD `## Core features` is the authoritative scope.
> Do not introduce new features, modules, components, screens, or token
> sets that have no counterpart in the existing PRD `## Core features`.
> Items the ADR has explicitly deferred (`> **Future ADRs**`) MUST NOT
> be pre-emptively decided. Existing sections that are not the explicit
> target of the iteration emphasis MUST be returned verbatim — do not
> reword Reasoning/Tradeoffs/Rejected-alternatives blocks. Pre-existing
> identifiers (variable, token, module, component names) MUST NOT be
> renamed unless the rename IS the requested change.

## Required behavior

1. If `{{EMPHASIS}}` == `(no change)`: read `{{DOC_NAME}}` via
   `read_run_artifact`, write it back unchanged via `write_run_artifact`.
   Return `WROTE: <path>`. Do NOT touch other sections, do NOT re-read
   other docs, do NOT inspect infrastructure code (rule 7).
2. Else: locate `{{EMPHASIS_SECTION_TITLE}}` in the doc, replace its body
   with an emphasis-aware rewrite. ALL other sections (incl. headings,
   ordering, whitespace, tables) MUST be byte-identical to input.
3. The "VERBATIM SENTINEL" sections (PRD `## Acceptance criteria` bash
   block, ADR `## Decision N` Reasoning/Tradeoffs/Rejected-alternatives
   sub-blocks) MUST be re-emitted byte-for-byte.

## Final step (canonical save block — DO NOT MODIFY THE STRUCTURE)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
doc_name = "{{DOC_NAME}}"
new_text = """<your re-written doc body — see Required behavior above>"""

path = write_run_artifact(rid, doc_name, new_text)
print(f"WROTE: {path}")
```

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
