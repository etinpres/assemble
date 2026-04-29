# Dogfood gate regex patterns

This doc captures the gate regex pattern conventions for /assemble dogfood gates (the bash one-liners in `docs/dogfood/phase-*.md` and `docs/plans/*.md` that verify run artifacts).

## The rule

**Use line-anchored regex (`^TOKEN$`) for placeholder tokens, not word-boundary regex (`\bTOKEN\b`).**

```bash
# WRONG (B-3 Finding #1 — false positive on narrative prose)
grep -nE '\bTBD\b|\bTODO\b|미정' runs/<rid>/ADR.md

# RIGHT (line-anchored — only matches lines that ARE the token, not lines that mention it)
grep -nE '^TBD$|^TODO$|^미정$' runs/<rid>/ADR.md
```

## Why

The B-3 dogfood (run `20260428-214502-6b79`) hit a false positive: ADR Decision 3 Reasoning contained the phrase `"slug 규칙 미정" 리스크 항목이 제거되고` — a *historical reference* to a now-resolved state. The mechanical `\bTBD\b|\bTODO\b|미정` grep flagged it as a placeholder violation.

Word-boundary regex matches inside prose. Line-anchored regex only matches lines that *consist entirely* of the placeholder token (modulo leading/trailing whitespace if you anchor differently). Real placeholders look like `미정` on a line by itself or `TBD: fill in colors` — both detected by `^TBD$` or with a slight refinement to allow trailing colon-prose. Narrative quotations like `"미정"이라고 적혀 있던` don't match.

If you genuinely need to catch `TBD: fill in colors` (the canonical "real placeholder" form), use:

```bash
grep -nE '^[[:space:]]*(TBD|TODO|미정)([[:space:]:].*)?$' runs/<rid>/<doc>.md
```

This matches lines that *start* with the token (modulo leading whitespace) and optionally have a colon-prose continuation. Still excludes narrative inline mentions.

## Why not allow-list comments (e.g. `<!-- ALLOW: 미정 -->`)?

The B-3 finding's resolution discussion considered allow-list HTML comments to suppress false positives. We rejected that approach because:

1. Every contributor adding a narrative reference would need to remember the allow-list syntax — high cognitive cost.
2. Allow-list comments stay in the file forever even after the narrative reference is gone — comment rot.
3. Line-anchored regex catches the same set of *real* placeholders without per-instance bookkeeping.

## Where the pattern applies

- `docs/dogfood/phase-*.md` gate scripts
- `docs/plans/*.md` "verification" or "gate" sections
- Any future dogfood that wants a "no placeholder tokens" gate

Existing past phase-*.md / plans-*.md files are historical records — leave them as-is. New gates use the line-anchored pattern.

## Related

- B-3 Finding #1: original false-positive incident
- B-4 plan §"Lessons applied from B-3 dogfood": defers Item F (this fix) to post-B-5 hygiene track
- B-5 plan §"Out of scope": confirms Item F lands on the hygiene pass
- Hygiene pass commit: this doc + plan-pack SKILL.md ambiguity audit (Item E)
