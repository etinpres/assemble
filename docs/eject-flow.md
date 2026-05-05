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

## Limitations

The eject command performs a byte-faithful copy. The ejected SKILL.md may contain references that only resolve inside the assemble harness:

- Ejected SKILL.md may reference `from server.harness import wrap_with_preamble` or `~/.claude/skills/assemble/bundled/_shared/harness-preamble.md` — these paths only resolve inside the assemble harness. User must adapt.
- ★ bundles' Bash-grant subagent prompts assume `dispatch_and_record` routing — outside assemble these are just .md files.
- Templates with `{{PLACEHOLDER}}` pattern still work; user just substitutes manually or via their own subagent.
- contracts.json and SECURITY.md are copied verbatim but contain references to V4 spike documentation paths that won't resolve outside the assemble repo.

This is documentation, not enforcement. eject's job is to produce a faithful copy, not to lobotomize the bundle.

Backup-name collision: if a user runs `apply_eject(..., overwrite=True)` twice within the same wall-second, the second backup attempt will raise OSError(ENOTEMPTY) on the rename to `<dest>.bak.<int(time.time())>` because the prior backup still exists. Acceptable failure mode (loud, not silent). Workaround: wait one second between consecutive overwrite ejects, or remove the prior `.bak.<ts>` directory manually.

`.bak.<timestamp>` survivors are NOT auto-cleaned. User must remove manually.
