You are dispatched as design-pack sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$` last-match (multi-write step — emit one WROTE: line per file written, orchestrator takes the last).

## Task

Read templates:
  ~/.claude/skills/assemble/bundled/design-pack/templates/DESIGN.md.template
  ~/.claude/skills/assemble/bundled/design-pack/templates/ANTI_PATTERNS.md.template

Substitute placeholders verbatim from the interview answers passed in {{TASK}} body
(do NOT paraphrase, do NOT expand, do NOT add commentary):

- `{{TONE}}` — answer to Q1 (디자인 톤)
- `{{COLOR_PRIMARY}}` — answer to Q2 (주 색상 hex 또는 자유 입력)
- `{{COMPONENTS}}` — answer to Q3 (컴포넌트 라이브러리)
- `{{TYPO}}` — answer to Q4 (타이포)
- `{{IDEA_OR_PRD_SUMMARY}}` — 2-3 lines summary read from `{{RUN_DIR}}/IDEA.md` OR `{{RUN_DIR}}/PRD.md` (whichever exists; if both, prefer PRD). If neither exists, write `(no upstream design context)`.

Write rendered files:
- `{{RUN_DIR}}/DESIGN.md`
- `{{RUN_DIR}}/ANTI_PATTERNS.md` (template body content-fixed; only header `{{TONE}}` substitutes)

## Constraints

1. NO gradient-text / glass morphism / backdrop-blur / "혁신적" / "차세대" language in DESIGN.md.
2. ANTI_PATTERNS.md is the deny list — DESIGN.md must not violate it.
3. Korean labels stay Korean.
4. NO scope expansion beyond template fields.

## Output

Write both files to {{RUN_DIR}}/, then emit one `WROTE:` line per file:

```
WROTE: <absolute path to DESIGN.md>
WROTE: <absolute path to ANTI_PATTERNS.md>
```

No other prose, no other files modified.
