# keeper Step 3 — bounded LLM summarization

You are dispatched as keeper Step 3 sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$` last-match (Spike VII F7 inheritance — multi-write steps may emit multiple `WROTE:` lines; orchestrator takes the last).

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}` (auto-derived per Spike VII Track A)
- candidates_path: `{{RUN_DIR}}/learning_candidates.json` (REQUIRED — Step 2's output)
- parsed_scope_path: `{{RUN_DIR}}/parsed_scope.json` (used for language detection)

## Goal

Read `learning_candidates.json` (Step 2's output), read `parsed_scope.json` for language detection, compose a ≤200-character single-line human-readable `summary` for each candidate, and write `{{RUN_DIR}}/learnings_to_emit.json`. Emit a single `WROTE: <abs path>` line on stdout.

Run from the assemble repo root (the harness sets that as CWD). Use `python3` + stdlib only. NO Bash. Do NOT import `server.*` — Step 3 is pure file I/O via Python stdlib.

## Constraints (pre-write guards)

The sub-agent applies these BEFORE writing JSON:

- `summary` ≤ 200 chars (truncate at 197 + `…` if exceeded)
- `summary` single line (replace any `\n` / `\r` with single space)
- `summary` in matching language (Korean if Korean detected via Hangul scan over `task_summary`; else English)
- Preserve `evidence` + `evidence_hash` from Step 2 **verbatim** — DO NOT modify or recompute. The hash covers the canonical-form evidence object; touching it desyncs ledger dedup.

## V4: deterministic template path (LLM-future)

This is the FIRST keeper step that exercises judgment beyond pure file probing (Steps 1-2 are deterministic). For V4 ship-readiness we use **deterministic template substitution** as the primary path — LLM judgment isn't reliably testable across runs, so the "fallback templates" below ARE the actual implementation. Future iteration may swap in genuine LLM summarization once trace data validates which categories benefit from natural-language summaries beyond template variables.

This makes the step deterministic + testable + aligns with the "deterministic fallback if LLM fails" requirement (treat fallback as primary path for V4).

## Fallback templates per rule_id

### English (`language == "en"`)

- **R1** → `"Dispatch failure at step '{step}': {note or '(no note)'}"`
- **R2** → `"Edited '{file}' matches deny pattern '{deny_pattern}' — extract helper outside denied tree."`
- **R3** → `"Verify command exited fail: {reason} (cmd: {command})."`
- **R4** → `"New {marker} marker added in diff: {line_excerpt}"`
- **R5** → `"{failed_count} dispatch step(s) failed: {steps[:3]}"`

### Korean (`language == "ko"`)

- **R1** → `"디스패치 실패 ({step}): {note or '(메모 없음)'}"`
- **R2** → `"'{file}' 편집이 deny 패턴 '{deny_pattern}'에 매칭됨 — denied 영역 바깥으로 helper 분리 권장."`
- **R3** → `"검증 명령 fail: {reason} (cmd: {command})."`
- **R4** → `"diff에 새 {marker} 마커 추가: {line_excerpt}"`
- **R5** → `"{failed_count}개 디스패치 단계 실패: {steps[:3]}"`

## Output JSON shape (`learnings_to_emit.json`)

```json
{
  "run_id": "<carried from learning_candidates>",
  "language": "ko",
  "entries": [
    {
      "rule_id": "R1|R2|R3|R4|R5",
      "category": "<category from candidate>",
      "summary": "<≤200 char single line>",
      "evidence": { "...": "verbatim from candidate" },
      "evidence_hash": "<verbatim from candidate>"
    }
  ]
}
```

## Save block

```python
python3 << 'EOF'
import json
from pathlib import Path

run_dir = Path("{{RUN_DIR}}")

# 1. Load Step 2 output (required).
candidates_path = run_dir / "learning_candidates.json"
candidates_doc = json.loads(candidates_path.read_text(encoding="utf-8"))
run_id = candidates_doc.get("run_id", "")
candidates = candidates_doc.get("candidates", []) or []

# 2. Detect language from parsed_scope.task_summary (Hangul → ko, else en).
scope_path = run_dir / "parsed_scope.json"
language = "en"
try:
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    task_summary = scope.get("task_summary", "") or ""
    # Heuristic: any char in 0xAC00-0xD7A3 range (Hangul Syllables block).
    if any(0xAC00 <= ord(ch) <= 0xD7A3 for ch in task_summary):
        language = "ko"
except (FileNotFoundError, json.JSONDecodeError, OSError):
    # parsed_scope unavailable — fall back to English. Step 3 is observational.
    language = "en"


# 3. Templates (English + Korean variants).
TEMPLATES_EN = {
    "R1": "Dispatch failure at step '{step}': {note}",
    "R2": "Edited '{file}' matches deny pattern '{deny_pattern}' — extract helper outside denied tree.",
    "R3": "Verify command exited fail: {reason} (cmd: {command}).",
    "R4": "New {marker} marker added in diff: {line_excerpt}",
    "R5": "{failed_count} dispatch step(s) failed: {steps}",
}
TEMPLATES_KO = {
    "R1": "디스패치 실패 ({step}): {note}",
    "R2": "'{file}' 편집이 deny 패턴 '{deny_pattern}'에 매칭됨 — denied 영역 바깥으로 helper 분리 권장.",
    "R3": "검증 명령 fail: {reason} (cmd: {command}).",
    "R4": "diff에 새 {marker} 마커 추가: {line_excerpt}",
    "R5": "{failed_count}개 디스패치 단계 실패: {steps}",
}
FALLBACK_NOTE_EN = "(no note)"
FALLBACK_NOTE_KO = "(메모 없음)"

templates = TEMPLATES_KO if language == "ko" else TEMPLATES_EN
fallback_note = FALLBACK_NOTE_KO if language == "ko" else FALLBACK_NOTE_EN


def render_summary(rule_id: str, evidence: dict) -> str:
    """Render a deterministic summary from the rule's evidence dict.

    Returns a single-line ≤200-char string. Evidence is preserved verbatim
    upstream; this function only consumes its fields.
    """
    tmpl = templates.get(rule_id)
    if tmpl is None:
        # Unknown rule_id — emit a generic stub so downstream still parses.
        return f"[{rule_id}] (no template registered)"

    if rule_id == "R1":
        note = evidence.get("note") or fallback_note
        text = tmpl.format(step=evidence.get("step", ""), note=note)
    elif rule_id == "R2":
        text = tmpl.format(
            file=evidence.get("file", ""),
            deny_pattern=evidence.get("deny_pattern", ""),
        )
    elif rule_id == "R3":
        text = tmpl.format(
            reason=evidence.get("reason", ""),
            command=evidence.get("command", ""),
        )
    elif rule_id == "R4":
        text = tmpl.format(
            marker=evidence.get("marker", ""),
            line_excerpt=evidence.get("line_excerpt", ""),
        )
    elif rule_id == "R5":
        steps = evidence.get("steps", []) or []
        # Cap to first 3 steps for readability.
        steps_display = steps[:3]
        text = tmpl.format(
            failed_count=evidence.get("failed_count", 0),
            steps=steps_display,
        )
    else:
        text = f"[{rule_id}] (unhandled)"

    # Single-line guard: collapse any \n / \r into spaces.
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    # ≤200 char guard: truncate at 197 + "…".
    if len(text) > 200:
        text = text[:197] + "…"
    return text


# 4. Build entries — preserve evidence + evidence_hash verbatim.
entries = []
for cand in candidates:
    rule_id = cand.get("rule_id", "")
    category = cand.get("category", "")
    evidence = cand.get("evidence", {}) or {}
    evidence_hash = cand.get("evidence_hash", "")
    summary = render_summary(rule_id, evidence)
    entries.append({
        "rule_id": rule_id,
        "category": category,
        "summary": summary,
        # IMPORTANT: evidence + evidence_hash MUST be carried verbatim from
        # Step 2 — modifying either desyncs ledger dedup downstream (Step 4).
        "evidence": evidence,
        "evidence_hash": evidence_hash,
    })

# 5. Assemble + write.
result = {
    "run_id": run_id,
    "language": language,
    "entries": entries,
}
out = run_dir / "learnings_to_emit.json"
out.write_text(
    json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
    encoding="utf-8",
)
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line:

```
WROTE: <abs path to learnings_to_emit.json>
```

Orchestrator parses with regex `^WROTE: (.+)$` and takes the last match (Spike VII F7 inheritance). Do NOT print prose, banners, progress dots, or warning text on stdout.

## Error handling

If `learning_candidates.json` is missing or malformed, raise (exit non-zero). Step 2 is REQUIRED upstream — its absence is a hard error, not a silent skip. Unlike Step 1 (which writes an audit-skipped placeholder), Step 3 has nothing meaningful to summarize without Step 2's structured candidates list.

If `parsed_scope.json` is unreadable, fall back to English (`language = "en"`) and continue — language detection is best-effort, not a blocker.

Unknown `rule_id` values produce a stub summary (`[<rule_id>] (no template registered)`) rather than raising — keeper is observational and tolerates upstream additions of new rules without crashing.
