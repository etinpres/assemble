# /assemble — Tool Concierge for Claude Code

A Claude Code skill that scans your installed skills / plugins / agents, recommends a per-stage workflow for a task, and lets you pick which tool runs at each stage.

## What it does

1. **Scans** every `SKILL.md` (user + plugin) and every agent `.md` on your machine.
2. **Classifies** each one into stages (`discover / plan / design / execute / debug / review / verify / ship` + orthogonal `safety / meta`) via a frontmatter-keyword heuristic. Anything the heuristic isn't confident about is left as `unclassified` and filled in on demand by an inline LLM pass.
3. **Recommends a stage sequence** for the task you typed.
4. **Runs a per-stage menu loop** — at each stage you see the tools that fit + meta actions (`ask / skip / manual / back / done`) + contextual safety/meta helpers. Pick one, run it, advance.
5. **Persists a run log** so `/assemble resume` picks up where you stopped.

## Install

```bash
git clone https://github.com/<your-fork>/assemble ~/.claude/skills/assemble
# Python 3, stdlib only — no pip install required.
```

Reload Claude Code and run:

```
/assemble build a small CLI for parsing CSV files
```

## Language / locale

Everything is English by default. A Korean locale is bundled:

```bash
export ASSEMBLE_LOCALE=ko   # menu labels & helper text switch to Korean
```

To contribute another locale, copy `config/i18n/en.json` → `config/i18n/<code>.json`, translate the strings, and set `ASSEMBLE_LOCALE=<code>`. Missing keys fall back to English so partial translations still work.

## Requirements

- **Python 3** (stdlib only — no external packages).
- Claude Code with the `Skill` + `AskUserQuestion` tools.
- Optional: `pytest` if you want to run the test suite.

## Repository layout

```
SKILL.md                  # Claude-facing procedure (the actual skill)
server/                   # Stdlib-only Python module
  __init__.py             # Facade — always import from `server`
  inventory.py            # Skill/agent scan, heuristic classifier
  classify.py             # LLM classification prompt + parser
  sequence.py             # Stage-sequence prompt + parser
  menu.py                 # Stage-menu builder (tools + meta + helpers)
  progress.py             # Run lifecycle (create / mark / resume / list)
  state_store.py          # Atomic JSON read/write with file locking
  i18n.py                 # Locale loader (env-var driven)
bin/
  classify-inventory      # Offline bulk-classification CLI
config/
  stages.json             # Stage ids only (display text lives in i18n/)
  stage_roles.json        # Role names used by contextual_helpers
  i18n/
    en.json               # English (default)
    ko.json               # Korean
tests/                    # 56 pytest cases (unit + e2e)
```

## Running tests

```bash
cd ~/.claude/skills/assemble
python3 -m pytest tests
```

Expected: `56 passed` in under a second.

## Design notes worth knowing

- **No global skill-name table.** The earlier design shipped `pre_mapping.json` with a baked-in list of known skills. It was retired because you can't pre-map what isn't installed. Classification now reads each skill's own `SKILL.md` frontmatter.
- **User > plugin precedence.** If two skills share a name, the user-installed one wins via path-priority first-wins dedupe.
- **Corrupt cache is quarantined, not silently destroyed.** A bad `inventory.json` is renamed `inventory.json.bad-<ts>` and rebuilt. You can inspect the bad file later.
- **Concurrent writers are safe.** `scan()` and `apply_classification()` share `update_json_locked`, so an `/assemble` run and a background `classify-inventory` don't clobber each other.
- **No skill bodies in the menu.** `build_stage_options()` returns only `{label, kind, description(≤80), tool_path}` — bodies load lazily when `Skill` actually invokes the tool.

## Contributing

- Write all code comments in English.
- User-visible strings go in `config/i18n/*.json`, never hardcoded.
- `from server import ...` only — don't reach into submodules.
- Run `python3 -m pytest tests` before opening a PR.

## License

MIT.
