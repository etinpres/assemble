---
name: assemble
description: Tool concierge — scan installed Claude Code skills/plugins/agents, recommend a per-stage workflow, and let the user pick which tool to use at each stage. Use when the user types `/assemble <task description>` or `/assemble resume` or `/assemble list`.
---

# /assemble — Tool Concierge

When invoked, follow this 6-phase loop. Every step is mandatory unless explicitly marked optional.

## 0. Prerequisites
- `~/.claude/skills/assemble/server/{state_store,inventory,classify,sequence,menu,progress,i18n}.py` must exist
- `~/.claude/skills/assemble/server/__init__.py` exposes the full facade — **always import from `server`**, never from submodules
- Python 3 (stdlib only)

### Facade convention (important)

All Python snippets must use `from server import …` — never reference submodules (`server.progress`, `server.inventory`, etc.) directly. This removes guesswork about where each function lives and keeps the next LLM from tripping over ImportError when a module gets refactored.

Exported symbols:

```
scan, apply_classification,
unclassified_names, unclassified_entries,
parse_skill_frontmatter, load_stages, load_stage_roles,
create_run, load_progress, mark_stage, list_runs, find_resumable,
build_stage_options, tools_for_stage, contextual_helpers,
build_classify_prompt, parse_classify_response,
build_sequence_prompt, parse_sequence_response,
```

`unclassified_entries` returns both skill + agent buckets (`{kind, name, path}`). `unclassified_names` is kept for back-compat as skills-only.

### Language

User-facing text is picked via `ASSEMBLE_LOCALE` (default `en`; `ko` ships in-tree). When you address the user directly, match their conversation language. The menu labels and stage descriptions rendered by `build_stage_options` / `load_stages` already respect the locale — don't translate those manually.

## 1. Boot

Strip the trailing `assemble`/leading `/assemble` token to extract the task.

Routing:
- `/assemble resume [<run_id>]` → §5 Resume
- `/assemble list` → §7 List
- otherwise → §2

## 2. Inventory refresh

```bash
cd ~/.claude/skills/assemble && python3 -c "
from server import scan, unclassified_names
inv = scan()
print(f'INV_OK skills={len(inv[\"skills\"])} agents={len(inv[\"agents\"])} unclassified={len(unclassified_names())}')
"
```

**Classification policy (pre_mapping retired, 2026-04-21 rework):**

Earlier builds shipped `config/pre_mapping.json` — a name→stage table. That approach had a fundamental flaw: you can't pre-map tools you don't know are installed. A fresh user's Mac dumped most skills into `unclassified` because the table only covered the original author's toolchain.

**Current approach:** every skill self-describes via its own `SKILL.md` frontmatter (`description` + first 500 chars of body). `scan()` reads that and classifies.

1. **Heuristic (first pass)** — `_classify_heuristic` in `inventory.py` requires ≥2 stage-keyword hits in the description to mark a skill `heuristic-classified`. Safety/meta skills also get a role hint so `contextual_helpers` picks them up.
2. **Heuristic miss → `unclassified`** — the skill isn't visible in any stage menu yet.
3. **Task-relevance inline (LLM, second pass)** — score unclassified entries against the `/assemble <task>` string by token overlap on name/description. For the **top 2** only, build the classify prompt, reply with JSON yourself (you are the LLM — no external call), then:
   - `confidence == high` → call `apply_classification` directly
   - `confidence in {medium, low}` → one `AskUserQuestion` to confirm
4. **Everything else is left alone.** If a tie or zero-score set means nothing qualified, tell the user once:

   > "{n} skill(s) are unclassified and won't appear in this run's menus. To bulk-classify, run:\n  `~/.claude/skills/assemble/bin/classify-inventory`"

   Use the localized version via `t("notices.unclassified_hint", n=<n>)` (the bash snippet below prints it for you).
5. **User override wins** — anything stored as `llm-classified` via `apply_classification()` is preserved across scans, and heuristic cannot overwrite it.

Outcome: classification is driven entirely by what's installed in front of you. No global table to maintain.

## 3. Sequence recommendation

```bash
cd ~/.claude/skills/assemble && python3 -c "
from server import build_sequence_prompt
import sys
print(build_sequence_prompt(task=sys.argv[1]))
" "<task>"
```

Reply with a JSON sequence yourself. Validate with `parse_sequence_response`. Then ask via `AskUserQuestion`:
```
question: "Does this sequence look right? <stage1> → <stage2> → ..."
options:  ["approve", "edit", "cancel"]
```

- approve → continue
- edit → follow-up `AskUserQuestion` to add/remove stages (multi-select, options = 8 sequential stages)
- cancel → STOP

Then create the run:
```bash
python3 -c "
from server import create_run
print(create_run(task='<task>', sequence=<approved sequence>))
"
```

## 4. Stage loop

**Bundling policy (revised after 2026-04-21 review).** An earlier version batched up to 4 stages into a single `AskUserQuestion`. Problem: stages aren't really independent (plan shapes design; execute failure drives debug), so pre-selected later-stage picks got stale. Current rules are conservative:

### 4a. When to bundle

- **Default:** surface exactly one stage at a time. User answers → tool runs → mark done → advance → open next menu.
- **Preload exception:** bundle at most 2 stages into one `AskUserQuestion` (2 questions) *iff* those stages are clearly independent. Independence check:
  - Stage A's outcome doesn't affect Stage B's tool choice (e.g. `verify` + `ship` is often independent; `plan` + `design` is not)
  - Both stages' tool candidates are already `heuristic-classified` or `llm-classified` (no `unclassified` mixed in)
- Never bundle 3+ stages. Selection quality beats perceived speed.

### 4b. Build the menu

```bash
python3 -c "
import json
from server import build_stage_options
for s in ['<s1>','<s2>','<s3>']:
    print(s, json.dumps(build_stage_options(s), ensure_ascii=False))
"
```

Each stage becomes one `AskUserQuestion` question:
- `header`: stage name (lowercase, ≤12 chars)
- `options`: up to 3 tools + whichever of `skip / manual / done` fits the context. If there are more than 4, paginate: show top-3 recommended + one "more options" entry that reveals the rest on the next turn.

### 4c. Handle each response

As soon as a stage answer arrives:
1. Invoke the picked tool (Skill/Agent, or invoke the helper directly)
2. `mark_stage('<rid>','<stage>','in_progress',tool_used='<name>')`
3. When the tool finishes: `mark_stage('<rid>','<stage>','done',tool_used='<name>')`

**Note:** `done` alone auto-backfills `started_at` if missing (2026-04-21 guard). Still, calling `in_progress` before `done` is the canonical pattern.

### 4d. Menu option semantics

- **tool** → invoke the skill/agent; `done` when the tool returns.
- **helper** → a meta/safety assist. Invoke it, mark only the helper, then re-open the same stage menu.
- **ask** (`물어보기` in `ko`) → reply with a paragraph recommending one of the listed tools given the task context, then re-render the menu.
- **skip** → `status='skipped'`, advance.
- **manual** (`직접` in `ko`) → `status='manual'`, advance.
- **back** → `mark_stage(rid, cur_stage, status='back')`. This moves the cursor only; **it does not overwrite the stage's recorded status** (pending/in_progress/done stay intact). Earlier versions persisted `status='back'`, which broke wrap-up counts and `find_resumable`.
- **done** → break out of the stage loop.

## 5. Resume

When `/assemble resume`:
- If `<run_id>` given → use it directly.
- Else: `find_resumable()`. Empty → say so and STOP. 1 → use it. Many → `AskUserQuestion` to pick.
- Load progress, then announce using `progress.resume_announce` (see below for the localized template). Example output (`en`): `"Resuming: <task>. Current stage: <s> (<idx+1>/<total>)"`.
- Re-enter §4 from `current_stage_index`.

```bash
python3 -c "
from server import load_progress
from server.i18n import t
p = load_progress('<rid>')
idx = p['current_stage_index']
print(t('progress.resume_announce', task=p['task'],
        stage=p['stages'][idx]['id'], idx=idx+1, total=len(p['stages'])))
"
```

## 6. Wrap-up

After the last stage hits `done` (or the user picks `done`):

```bash
python3 -c "
from server import load_progress
from server.i18n import t
from datetime import datetime
p = load_progress('<rid>')
created = datetime.fromisoformat(p['created_at'])
updated = datetime.fromisoformat(p['updated_at'])
duration = int((updated - created).total_seconds())
done    = sum(1 for s in p['stages'] if s['status'] == 'done')
skipped = sum(1 for s in p['stages'] if s['status'] == 'skipped')
manual  = sum(1 for s in p['stages'] if s['status'] == 'manual')
tools = sorted({s['tool_used'] for s in p['stages'] if s['tool_used']})
m, s = divmod(duration, 60)
tools_out = ', '.join(tools) or t('progress.no_tools')
print(t('progress.wrap_up', rid=p['run_id'], m=m, s=s,
        done=done, skipped=skipped, manual=manual, tools=tools_out))
print(t('progress.progress_path',
        path=f'~/.claude/channels/assemble/runs/{p[\"run_id\"]}/progress.json'))
"
```

(Optional) If the `learn` skill is installed, offer a retro.

## 7. List (past runs)

When `/assemble list`:

```bash
python3 -c "
from server import list_runs, load_progress
for rid in list_runs()[-10:]:
    p = load_progress(rid) or {}
    done = sum(1 for s in p.get('stages',[]) if s.get('status')=='done')
    total = len(p.get('stages',[]))
    status = 'done' if done == total else f'{done}/{total}'
    print(f'{rid}  [{status}]  {p.get(\"task\",\"\")[:60]}')
"
```

Show the output verbatim, then mention they can resume any line with `/assemble resume <run_id>`.

## 8. Troubleshooting

- **`ImportError: cannot import 'X' from 'server.Y'`** — don't reach into submodules. Use `from server import X`. See §0.
- **`started_at: NULL`** — pre-2026-04-21 build. Current `mark_stage` guards against this.
- **Classifications keep disappearing** — the scan merge preserves `llm-classified` entries; `heuristic-classified` recomputes on every scan when the description changes (by design).
- **Lots of unclassified on a fresh install** — expected after pre_mapping retirement. The heuristic catches descriptions with enough stage keywords; the rest land in `unclassified` until the user runs `bin/classify-inventory --apply` or the inline LLM pass covers them.
- **I've seen a `pre-mapped` source** — legacy label. Current sources are `heuristic-classified`, `llm-classified`, `unclassified`.
- **`inventory.json.bad-<ts>` appeared** — cache was corrupt, scan auto-quarantined + rebuilt. `llm-classified` entries survive unless the cache was destroyed mid-write; check with `bin/classify-inventory --status`.
- **User skill was overwritten by a plugin skill** — pre-2026-04-21 precedence bug. Current `enumerate_skill_paths` returns user → plugin, so first-wins dedupe always keeps user.
- **Concurrent `classify-inventory` + `/assemble` lost a classification** — pre-2026-04-21 race. Current `apply_classification` and `scan` share `update_json_locked`.
- **`illegal transition: stage 'X' already 'done'`** — trying to drive `done` back into `in_progress`. Use `back` to move the cursor; don't call `mark_stage` again.

## 9. Internals: lazy-load policy

- Each option returned by `build_stage_options()` is `{label, kind, description(≤80), tool_path}`. The skill body is never loaded until the user picks and the `Skill` tool actually invokes it.
- The cache at `~/.claude/channels/assemble/inventory.json` stores a 500-char `body_excerpt` per skill, used for classification only — it never reaches the user menu.
- Audit: confirmed 2026-04-21. Skill bodies don't leak into context.

## 10. Known noise: vercel-plugin injection

A plugin hook matches by filename alone and prepends an "MANDATORY: open official docs" preamble to unrelated skills (`next-forge`, `vercel-cli`, etc.). Mitigations:

- **Soft:** `~/.claude/settings.json` → `env.VERCEL_PLUGIN_INJECTION_BUDGET=1` caps the injection payload body at 1 byte. The preamble itself may still attach.
- **Hard:** on projects unrelated to Vercel/Next.js, drop `vercel-vercel-plugin` from `enabledPlugins`. Project-scoped via `.claude/settings.local.json`.
- Patching the plugin's `hooks.json` directly is not recommended — plugin upgrades revert it.
