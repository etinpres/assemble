# keeper quick mode — single-dispatch fallback
You are dispatched as keeper quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Bash tool access GRANTED

keeper full mode Steps 1/2/4 와 동일하게 quick mode 도 read-only git probes (`server.git_helpers`) + canned scripts (`extract_rules.py`, `ledger_update.py`) 호출을 위해 Bash 사용. argv-list, no shell=True.

**Forbidden**:
- write-side git ops (`git tag`, `git commit`, `git push`, `git checkout`, etc.)
- `shell=True`, backtick interpolation, OR any path that lets caller-controlled strings reach a shell

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`

## Goal

full mode 의 4-step (+iter) keeper pipeline (Step 1 audit inventory → Step 2 deterministic rule extraction → Step 3 bounded LLM summarization → Step 4 ledger append + prune + report) 을 단일 dispatch 로 압축. `KEEPER_REPORT.md` 1 doc 에 7 sections 모두 inline + ledger 업데이트.

산출물 schema 는 full mode 와 동일 — 단일 pass 안에서 audit inventory + 5-rule extraction + summarization + ledger update + report rendering.

## Output sections (must include all)

`KEEPER_REPORT.md` 안에 다음 sections 모두 포함 (full mode happy path schema 보존):

- 헤더: `**Run ID**`, `**Verdict**` (audit-clean / audit-flagged / audit-skipped), `**Generated**`
- `## 1. Run summary` — 1~3 줄 run summary
- `## 2. Audit inventory` — bundles_observed / artifacts_present_count / verdicts_collected / clean_tree / branch / head_sha / git_diff_files_count
- `## 3. Rules fired` — 5 rules (R1~R5) table: rule / category / fired_count
- `## 4. Learnings emitted` — emit 된 learning entries list
- `## 5. Ledger state delta` — before_prune / after_prune / appended / dropped (TTL/skip/dedup/cap)
- `## 6. Prune summary` — 4-stage prune note
- `## 7. Next-run recall preview` — top-K relevant learnings preview
- `## Mode usage` — full mode 가 T3 에서 채울 section. quick mode 는 stage / mode / dispatches / rationale 1-row 추가
- `## Mode usage note` — `mode=quick` 1-line marker

Verdict logic (deterministic, full mode 와 동일):
```python
verdict = (
    "audit-clean"   if (audit_ready AND total_emitted == 0)
    else "audit-flagged" if (audit_ready AND total_emitted >= 1)
    else "audit-skipped"
)
```

## Save block

```python
python3 << 'EOF'
import json
import subprocess
from datetime import datetime
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")
ts = datetime.now().isoformat()

# Sub-agent: 동일 dispatch 안에서 다음 모두 처리
# 1. audit inventory — parsed_scope sanity + run_dir scan + git probes
# 2. 5-rule extraction — invoke `python3 ~/.claude/skills/assemble/bundled/keeper/scripts/extract_rules.py {run_dir}`
# 3. summarization — bounded LLM (≤200 chars per learning); fallback templates per rule_id
# 4. ledger update — invoke `python3 ~/.claude/skills/assemble/bundled/keeper/scripts/ledger_update.py {run_dir}`
# 5. KEEPER_REPORT.md render — 7 sections + Mode usage section + mode=quick marker
# 모든 <TBD: ...> 는 concrete 으로 채워야 함.

body = f"""# KEEPER_REPORT

**Run ID**: {run_id}
**Verdict**: <TBD: audit-clean | audit-flagged | audit-skipped> — <TBD reason>
**Generated**: {ts}
**Mode**: quick (single-dispatch fallback — V4 Spike XIV paradigm hybrid)

## 1. Run summary

<TBD: 1~3 line run summary>

## 2. Audit inventory

- Bundles observed: <TBD>
- Artifacts present: <TBD count> files
- Verdicts collected: <TBD>
- Repo state: <TBD clean | dirty> on <TBD branch> (<TBD short_sha>)
- Diff files: <TBD count>

## 3. Rules fired

| Rule | Category | Fired count |
|---|---|---|
| R1 | rule-violation | <TBD> |
| R2 | scope-deviation | <TBD> |
| R3 | ac-failure | <TBD> |
| R4 | todo-leakage | <TBD> |
| R5 | dispatch-failure | <TBD> |

## 4. Learnings emitted

<TBD: list of learning entries with summaries (≤200 chars each), or "(none — audit-clean)">

## 5. Ledger state delta

- Before prune: <TBD> entries
- After prune: <TBD> entries
- Net delta: <TBD> (appended <TBD>, dropped by TTL <TBD> / skiplist <TBD> / dedup <TBD> / cap <TBD>)

## 6. Prune summary

<TBD: 4-stage prune note (TTL 30d → skiplist → dedup → FIFO cap 100)>

## 7. Next-run recall preview

<TBD: top-K relevant learnings preview, stage→category priority>

## Mode usage

| stage | mode | dispatches | rationale |
|---|---|---|---|
| meta | quick | 1 | <TBD: user-supplied or "—"> |

## Mode usage note

mode=quick — full mode 의 6-step keeper pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. 다음 run 에서 시간 확보 권장.
"""

out = run_dir / "KEEPER_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to KEEPER_REPORT.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
