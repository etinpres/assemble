# Task — ADR.md draft + write

You are dispatched as plan-pack Step 11 (ADR sub-agent). Goal: produce ADR decisions block and write `<run_dir>/ADR.md`. Print `WROTE: <absolute path>` on stdout — main parses with regex `^WROTE: (.+)$`. No other prose.

## Inputs

- run_id: `{{RUN_ID}}`
- task: `{{TASK}}`
- adr_interview_answers (D1–D6): `{{INTERVIEW_ANSWERS}}`

## Required behavior

Load ARCH context: `arch_text = read_run_artifact("{{RUN_ID}}", "ARCHITECTURE.md")`. Synthesize Context + Reasoning sub-headings from arch_text + PRD's `## Goal` / `## Risks`. Do NOT emit stub fillers ("This decision was important.") — if synthesis cannot ground, drop the decision.

Required emitted shape (≥3 sections):

```
## Decision 1: <title>

### Context
<one paragraph>

### Decision
<one paragraph>

### Reasoning
<one paragraph — why this beats alternatives>

### Rejected alternatives
- alternative — reason

### Tradeoffs
- tradeoff — consequence

## Decision 2: ...
## Decision 3: ...
```

## Final step (canonical save block)

```python
# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE -- sub-agent legitimate dispatch
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/assemble"))
from server import write_run_artifact, read_run_artifact

rid = "{{RUN_ID}}"
task = """{{TASK}}"""
arch_text = read_run_artifact(rid, "ARCHITECTURE.md") or ""

decisions_block = """
## Decision 1: <TBD: 1-line decision title from D1 selection>
### Context
<TBD: 1 paragraph synthesized from PRD Goal/Risks + ARCH module relevant to D1 — never stub fillers>
### Decision
<TBD: 1 paragraph stating what was chosen, sourced from D1 + Call 6 sub-question (a)>
### Reasoning
<TBD: 1 paragraph — why this beats alternatives, cite the strongest rejected option from Call 6 (a)>
### Rejected alternatives
- <TBD: 1 alternative — one-line reason rejected, from Call 6 (a)>
### Tradeoffs
- <TBD: 1 tradeoff — one-line consequence, from Call 6 (b)>
""".strip()

template = (Path.home() / ".claude/skills/assemble/bundled/plan-pack/templates/ADR.md.template").read_text()
filled = template.replace("{{TASK}}", task).replace("{{DECISIONS_BLOCK}}", decisions_block)

path = write_run_artifact(rid, "ADR.md", filled)
print(f"WROTE: {path}")
```

If write fails, print `ERROR: <reason>` and exit. No fallback writes.
