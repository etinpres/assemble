# /assemble eject — flow

> **Routing guard (메인 Claude 전용):** This file is reached ONLY via the
> SKILL.md § Sub-commands router after the `eject` keyword matches. Once
> you start reading this flow, **do NOT fall through to §2~§7 of the V3
> concierge default flow.** Execute Steps 1–5 below in order and stop.
> If the user types `/assemble <free-form task>` (no `eject` keyword),
> the SKILL.md router never lands here in the first place.

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

## Limitations

The eject command performs a byte-faithful copy. The ejected SKILL.md may contain references that only resolve inside the assemble harness:

- Ejected SKILL.md may reference `from server.harness import wrap_with_preamble` or `~/.claude/skills/assemble/bundled/_shared/harness-preamble.md` — these paths only resolve inside the assemble harness. User must adapt.
- ★ bundles' Bash-grant subagent prompts assume `dispatch_and_record` routing — outside assemble these are just .md files.
- Templates with `{{PLACEHOLDER}}` pattern still work; user just substitutes manually or via their own subagent.
- contracts.json and SECURITY.md are copied verbatim but contain references to V4 spike documentation paths that won't resolve outside the assemble repo.

This is documentation, not enforcement. eject's job is to produce a faithful copy, not to lobotomize the bundle.

Backup-name collision: if a user runs `apply_eject(..., overwrite=True)` twice within the same wall-second, the second backup attempt will raise OSError(ENOTEMPTY) on the rename to `<dest>.bak.<int(time.time())>` because the prior backup still exists. Acceptable failure mode (loud, not silent). Workaround: wait one second between consecutive overwrite ejects, or remove the prior `.bak.<ts>` directory manually.

`.bak.<timestamp>` survivors are NOT auto-cleaned. User must remove manually.

### Default-name `inventory.scan()` collapse (verified Spike XII cleanup)

If the user accepts the default destination name (`--name` omitted, so `dest_name == bundle_name`), `inventory.scan()` will report ONLY the source bundled copy under that name — the ejected user copy is silently shadowed. Verified empirically for `/assemble eject idea-shaper` against master `b03e29b`:

```
disk:
  ~/.claude/skills/assemble/bundled/idea-shaper/SKILL.md   (source)
  ~/.claude/skills/idea-shaper/SKILL.md                    (ejected)

scan()['skills']['idea-shaper'] →
  path=~/.claude/skills/assemble/bundled/idea-shaper/SKILL.md
  bundled=True
  (ejected user copy NOT visible)
```

Root cause: `enumerate_skill_paths()` returns both SKILL.md files in alphabetical order — `assemble/bundled/idea-shaper/...` sorts BEFORE `idea-shaper/...`. `scan()` then applies first-wins dedupe by `name:` frontmatter (`server/inventory.py:470`). Both files share `name: "idea-shaper"`, so the bundled wins.

**Workarounds (recommended order):**

1. **Pass `--name <custom>` on eject** — easiest; e.g., `eject idea-shaper --name my-idea-shaper`. The ejected copy is then dedupe-distinct and appears in `scan()` with `bundled=False`.
2. **Edit ejected SKILL.md frontmatter** post-eject — change `name: "idea-shaper"` → `name: "<custom>"` so the dedupe sees a different key. Filesystem path can stay the same.
3. **(Not implemented for V4)** Override the bundled copy by removing/renaming `assemble/bundled/<bundle>/`. Discouraged because it breaks the V4 결정 #1 자급자족 보증. V5 may expose `--shadow-bundled` for power users.

Step 5 post-eject hint should mention this whenever `dest_name == bundle_name`. Step 1 parse SHOULD log a `notice:` line if `--name` was omitted, suggesting custom-name workaround so the user is not surprised by a missing entry on the next `/assemble` run.
