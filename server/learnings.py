"""Learnings ledger — selection + fence rendering (pure functions).

Spike X Track B injects top-K relevant prior-run learnings into every
dispatched sub-agent prompt as a body-prefix fence so future iterations
inherit the audit trail of past violations. This module owns the *selection*
and *render* halves of that pipeline; ledger I/O (read/write/prune of
`learnings.jsonl`) lands in Spike X Task A3 and extends this module.

Pure-function contract: no globals are mutated, no disk I/O happens here.
The ledger is passed in via `ledger=[...]` parameter so unit tests don't
need filesystem fixtures.

Each ledger entry is a dict matching the Spike X spec schema::

    {"ts": "2026-05-04T...Z", "run_id": "...", "rule_id": "R2",
     "category": "scope-deviation", "summary": "...",
     "evidence_hash": "<sha256>", "evidence": {...}}
"""

from typing import Optional


MAX_K_DEFAULT = 5
MAX_SUMMARY_CHARS = 200


# Stage → ordered list of categories the keeper considers most relevant for
# that stage. Earlier categories rank higher. Entries whose category is *not*
# in the list still rank below all listed categories (effectively "infinity"
# priority index). Spec §"Stage→category priority map".
STAGE_CATEGORY_PRIORITY: dict[str, list[str]] = {
    "plan":    ["scope-deviation", "ac-failure", "todo-leakage", "rule-violation", "dispatch-failure"],
    "execute": ["scope-deviation", "todo-leakage", "rule-violation", "ac-failure", "dispatch-failure"],
    "debug":   ["ac-failure", "rule-violation", "scope-deviation", "todo-leakage", "dispatch-failure"],
    "review":  ["scope-deviation", "todo-leakage", "rule-violation", "ac-failure", "dispatch-failure"],
    "verify":  ["ac-failure", "rule-violation", "scope-deviation", "todo-leakage", "dispatch-failure"],
    "ship":    ["scope-deviation", "ac-failure", "rule-violation", "todo-leakage", "dispatch-failure"],
    "meta":    ["scope-deviation", "ac-failure", "todo-leakage", "rule-violation", "dispatch-failure"],
}


def select_relevant(
    stage: str,
    k: int = MAX_K_DEFAULT,
    ledger: Optional[list[dict]] = None,
) -> list[dict]:
    """Return up to `k` ledger entries ranked for `stage`.

    Ranking is deterministic, in order of:
      1. category priority — entries whose `category` appears earlier in
         `STAGE_CATEGORY_PRIORITY[stage]` rank higher; categories absent
         from the list (or unknown stages) all share the lowest priority
         and fall through to the next tiebreaker.
      2. recency — `ts` descending (newer first).
      3. rule_id — alpha ascending (`R1` before `R2`).

    For an unknown `stage` (not a key in `STAGE_CATEGORY_PRIORITY`) the
    priority tier collapses, so the result is purely recency-then-rule_id.

    `ledger=None` returns `[]`. Task A3 will swap the disk-read in front
    of this function; until then the caller is expected to inject the
    list explicitly (also useful for testing).
    """
    if ledger is None:
        return []
    if k <= 0:
        return []

    priority = STAGE_CATEGORY_PRIORITY.get(stage, [])
    # Categories not in the priority list (or every category when stage is
    # unknown) share a sentinel rank larger than any valid index. This keeps
    # listed-category entries strictly above unlisted ones without forking
    # the sort key shape.
    fallback_rank = len(priority)

    def sort_key(entry: dict) -> tuple:
        category = entry.get("category", "")
        try:
            cat_rank = priority.index(category)
        except ValueError:
            cat_rank = fallback_rank
        ts = entry.get("ts", "")
        rule_id = entry.get("rule_id", "")
        # ts descending → invert by negating via a comparator that pairs
        # well with tuple sort. Strings can't be negated, so we wrap with
        # a class that reverses comparison; simpler: sort by ts ASC then
        # reverse just the ts dimension by sorting twice. Python's stable
        # sort lets us do (cat_rank ASC, -ts via reverse-string trick).
        # Simplest portable form: use a tuple of (cat_rank, neg_ts_key,
        # rule_id) where neg_ts_key flips lexical order.
        return (cat_rank, _reverse_string(ts), rule_id)

    sorted_entries = sorted(ledger, key=sort_key)
    return sorted_entries[:k]


def _reverse_string(s: str) -> tuple:
    """Return a key that sorts strings in reverse lexical order via tuple.

    Python tuples sort element-wise; negating each codepoint inverts the
    comparison. ISO-8601 timestamps are pure ASCII so this is exact and
    cheap. Used by `select_relevant` to express "ts DESC" inside a single
    `sorted(key=...)` call without a second pass.
    """
    return tuple(-ord(c) for c in s)


def render_learnings_fence(entries: list[dict]) -> str:
    """Render the `[PRIOR LEARNINGS — 우선 회피]` block.

    Empty input returns `""` (no fence emitted at all). Otherwise:

        [PRIOR LEARNINGS — 우선 회피]
        1. (R2) Edited src/auth.py despite deny pattern auth/* — ...
        2. (R3) Verify command exited 1 — check pytest path before declaring AC pass.
        [/PRIOR LEARNINGS]

    Pre-render guards on each entry's `summary`:
      - newline characters are collapsed to a single space (the fence is a
        flat numbered list — multi-line summaries break the format).
      - summaries longer than `MAX_SUMMARY_CHARS` are truncated to
        `MAX_SUMMARY_CHARS - 3` characters plus an ellipsis "…".
    """
    if not entries:
        return ""

    lines = ["[PRIOR LEARNINGS — 우선 회피]"]
    for index, entry in enumerate(entries, start=1):
        rule_id = entry.get("rule_id", "")
        summary = _flatten_summary(entry.get("summary", ""))
        lines.append(f"{index}. ({rule_id}) {summary}")
    lines.append("[/PRIOR LEARNINGS]")
    return "\n".join(lines)


def _flatten_summary(summary: str) -> str:
    """Strip newlines + truncate to `MAX_SUMMARY_CHARS` with ellipsis."""
    flat = summary.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    if len(flat) > MAX_SUMMARY_CHARS:
        # 197 chars + "…" (1 char) = 198 visible chars; well under 200 cap
        # and the ellipsis makes truncation explicit to readers.
        return flat[: MAX_SUMMARY_CHARS - 3] + "…"
    return flat
