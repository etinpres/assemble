---
name: assemble
description: Tool concierge — scan installed Claude Code skills/plugins/agents, recommend a per-stage workflow, and let the user pick which tool to use at each stage. Use when the user types `/assemble <task description>` or `/assemble resume`.
---

# /assemble — Tool Concierge

When invoked, follow this 5-phase loop. Every step is mandatory unless explicitly marked optional.

## 0. Prerequisites
- `~/.claude/skills/assemble/server/{state_store,inventory,classify,sequence,menu,progress}.py` must exist
- Python 3 (stdlib only)

## 1. Boot

Strip the trailing `assemble`/`어셈블`/leading `/assemble` token to extract the task.

If the user typed `/assemble resume [<run_id>]`, jump to §5 Resume.

## 2. Inventory refresh

```bash
cd ~/.claude/skills/assemble && python3 -c "
from server.inventory import scan, unclassified_names
inv = scan()
print(f'INV_OK skills={len(inv[\"skills\"])} agents={len(inv[\"agents\"])} unclassified={len(unclassified_names())}')
"
```

If `unclassified > 0`, for each unclassified skill:
1. Read its frontmatter via `parse_skill_frontmatter`
2. Build the classification prompt (`server.classify.build_prompt`)
3. Reply to the prompt yourself in this conversation (you ARE the LLM — no separate API call needed). Output strictly the JSON block.
4. Pass your output back to `parse_response` to validate.
5. If `confidence == "high"` → call `apply_classification` directly.
6. If `confidence in {"medium","low"}` → use `AskUserQuestion`:
   ```
   "<skill>를 [stage]/[role]로 분류했어 (확신도 <c>). 이대로 갈까?"
   options: ["yes — 적용", "no — 직접 정해줄게", "skip — 일단 미분류로 두기"]
   ```
   - yes → apply_classification
   - no → AskUserQuestion follow-up to choose stage/role
   - skip → do nothing, leave as unclassified

## 3. Sequence recommendation

```bash
cd ~/.claude/skills/assemble && python3 -c "
from server.sequence import build_prompt
import sys
print(build_prompt(task=sys.argv[1]))
" "<task>"
```

Reply yourself with the JSON sequence. Validate via `parse_response`. Then `AskUserQuestion`:
```
"이 시퀀스로 갈까? <stage1> → <stage2> → ..."
options: ["approve", "edit", "cancel"]
```

- approve → continue
- edit → AskUserQuestion to pick which stages to add/remove (multi-select, options = 8 sequential stages)
- cancel → STOP

Then create the run:
```bash
python3 -c "
from server.progress import create_run
print(create_run(task='<task>', sequence=<approved sequence>))
"
```

## 4. Stage loop

For each stage in the approved sequence:
1. Build menu options:
   ```bash
   python3 -c "
   import json
   from server.menu import build_stage_options
   print(json.dumps(build_stage_options('<stage>')))
   "
   ```
2. Render those options via `AskUserQuestion`. Up to 4 options per `AskUserQuestion` call — if more, paginate (call multiple times) OR group: tools first, meta actions second, helpers third.
3. Based on user pick:
   - **tool** → invoke that tool (prefer `Skill` for SKILL.md skills, `Agent` for `.md` agents). Mark stage `in_progress` then `done` with `tool_used=<name>`.
   - **helper** → invoke immediately, mark only the helper invocation, stay in the same stage menu after it returns.
   - **물어보기** → reply with a paragraph recommending one of the listed tools given the task context, then re-render the menu.
   - **skip** → mark stage `skipped`, advance.
   - **직접** → mark stage `manual`, advance.
   - **back** → mark `back`, decrement `current_stage_index`.
   - **done** → break out of stage loop.

After every transition: `python3 -c "from server.progress import mark_stage; mark_stage('<rid>', '<stage>', '<status>', tool_used='<name>')"`.

## 5. Resume

When `/assemble resume`:
- If `<run_id>` given → use it directly.
- Else: `find_resumable()`. If empty, say so and STOP. If 1 → use it. If many → `AskUserQuestion` to pick.
- Load progress, announce: `"이어서: <task>. 현재 stage: <s> (<idx+1>/<total>)"`.
- Re-enter the §4 stage loop from `current_stage_index`.

## 6. Wrap-up

After last stage `done` (or user picks `done`):
- Print: `"완료. run_id=<id>. 진행 기록: <progress_path>"`.
- (Optional) If `learn` is installed, suggest invoking it for a retro.
