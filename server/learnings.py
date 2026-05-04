"""Learnings ledger — selection, fence rendering, and ledger I/O.

Spike X Track B injects top-K relevant prior-run learnings into every
dispatched sub-agent prompt as a body-prefix fence so future iterations
inherit the audit trail of past violations.

This module owns three halves of that pipeline:

  * Pure selection (`select_relevant`) — A1.
  * Pure fence rendering (`render_learnings_fence`) — A1.
  * Ledger I/O + deterministic prune (`learnings_path`,
    `learnings_skip_path`, `read_ledger`, `read_skiplist`,
    `write_ledger`, `prune_ledger`) — A3.

Selection + rendering remain pure (no disk I/O). The I/O helpers below
use atomic temp-file-then-rename writes to keep concurrent in-process
crashes from leaving torn ledger files; cross-process locking is V5
scope and documented as a known limitation on `write_ledger`.

Each ledger entry is a dict matching the Spike X spec schema::

    {"ts": "2026-05-04T...Z", "run_id": "...", "rule_id": "R2",
     "category": "scope-deviation", "summary": "...",
     "evidence_hash": "<sha256>", "evidence": {...}}
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Union


MAX_K_DEFAULT = 5
MAX_SUMMARY_CHARS = 200


# Stage → ordered list of categories the keeper considers most relevant for
# that stage. Earlier categories rank higher. Entries whose category is *not*
# in the list still rank below all listed categories (effectively "infinity"
# priority index). Spec §"Stage→category priority map".
#
# Spike X cleanup F-X2: inner priority lists changed from ``list[str]`` to
# ``tuple[str, ...]`` for mutability hardening — prevents accidental global
# state pollution by a misbehaving caller (e.g. ``cats.append(...)`` on the
# returned reference). ``priority.index(category)`` is unchanged on tuples.
STAGE_CATEGORY_PRIORITY: dict[str, tuple[str, ...]] = {
    "plan":    ("scope-deviation", "ac-failure", "todo-leakage", "rule-violation", "dispatch-failure"),
    "execute": ("scope-deviation", "todo-leakage", "rule-violation", "ac-failure", "dispatch-failure"),
    "debug":   ("ac-failure", "rule-violation", "scope-deviation", "todo-leakage", "dispatch-failure"),
    "review":  ("scope-deviation", "todo-leakage", "rule-violation", "ac-failure", "dispatch-failure"),
    "verify":  ("ac-failure", "rule-violation", "scope-deviation", "todo-leakage", "dispatch-failure"),
    "ship":    ("scope-deviation", "ac-failure", "rule-violation", "todo-leakage", "dispatch-failure"),
    "meta":    ("scope-deviation", "ac-failure", "todo-leakage", "rule-violation", "dispatch-failure"),
    "discover": (
        "scope-deviation",
        "todo-leakage",
        "rule-violation",
        "ac-failure",
        "dispatch-failure",
    ),
    "design": (
        "scope-deviation",
        "rule-violation",
        "todo-leakage",
        "ac-failure",
        "dispatch-failure",
    ),
    "safety": (
        "rule-violation",
        "scope-deviation",
        "ac-failure",
        "todo-leakage",
        "dispatch-failure",
    ),
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

    priority = STAGE_CATEGORY_PRIORITY.get(stage, ())
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


# ---------------------------------------------------------------------------
# A3 — ledger I/O + deterministic prune
# ---------------------------------------------------------------------------

# Default prune knobs. Centralized here (rather than buried in the function
# signature) so the keeper bundle and any future tooling reference the same
# constants. `prune_ledger` accepts overrides for tests + future tuning.
TTL_DAYS_DEFAULT = 30
CAP_DEFAULT = 100


def learnings_path() -> Path:
    """Absolute path to the keeper ledger jsonl.

    Honors `ASSEMBLE_HOME` env var the same way `server/run_dir.py` does so
    test fixtures (and Conductor workspaces) can redirect the ledger without
    monkey-patching `Path.home`.
    """
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    return base / ".claude/channels/assemble/learnings.jsonl"


def learnings_skip_path() -> Path:
    """Absolute path to the user-managed evidence-hash skiplist.

    One sha256 per line, `#` comments + blank lines ignored. Same env var
    handling as `learnings_path`; the keeper bundle reads this file when
    pruning so a user can permanently veto a recurring "lesson" by appending
    its `evidence_hash` to the file.
    """
    base = Path(os.environ.get("ASSEMBLE_HOME", str(Path.home())))
    return base / ".claude/channels/assemble/learnings.skip"


def read_ledger(path: Optional[Path] = None) -> list[dict]:
    """Load and return ledger entries as a list of dicts.

    `path=None` falls back to `learnings_path()`. If the file is missing
    (first run on a clean machine), returns `[]`. Malformed JSON lines are
    skipped with a one-line stderr warning rather than raising — a single
    corrupt write must not bring down every future dispatch. Schema is NOT
    validated here; keeper Step 4 owns that responsibility (spec §A3).
    """
    target = path if path is not None else learnings_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    entries: list[dict] = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            print(
                f"[learnings] skipped malformed line {line_no}: "
                f"{repr(line[:80])}",
                file=sys.stderr,
            )
    return entries


def read_skiplist(path: Optional[Path] = None) -> set[str]:
    """Return the set of evidence_hash values the user has skiplisted.

    Format: one hash per line. `#` comments and blank lines are ignored
    (whitespace-only lines count as blank). Missing file returns an empty
    set so callers can pass the result straight into `prune_ledger`.
    """
    target = path if path is not None else learnings_skip_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return set()
    hashes: set[str] = set()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        hashes.add(stripped)
    return hashes


def write_ledger(entries: Iterable[dict], path: Optional[Path] = None) -> None:
    """Atomically overwrite the ledger with `entries`, one JSON dict per line.

    Writes go to a sibling `<path>.<n>.tmp` file in the same directory, then
    `os.replace` swaps it into place — readers always see either the old
    file or the new file, never a torn one. Parent directory is created if
    missing. Uses `ensure_ascii=False` so Korean (and other non-ASCII)
    summaries survive the round-trip.

    Known limitation (V5 scope): no cross-process locking. Two concurrent
    keeper invocations on the same host can clobber each other's writes —
    the second `os.replace` wins. The keeper today is invoked sequentially
    by `/assemble`, so this is acceptable for V4. Document inline rather
    than silently rely on it.

    Notes / Limitations:
        Generator inputs are materialized into a list at function entry —
        this gives a stable snapshot for the duration of the call and
        prevents weird half-iterated states if the caller's iterator has
        side effects. Pass an exhausted generator and you'll write an
        empty ledger; pass `[]` explicitly to express clear-intent.
    """
    entries = list(entries)  # defensive: stable snapshot, tolerates generator inputs
    target = path if path is not None else learnings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _coerce_now(now: Union[datetime, str, None]) -> datetime:
    """Normalize the `now` parameter accepted by `prune_ledger`.

    The keeper passes a real `datetime`; tests prefer ISO strings for
    readability. `None` -> `datetime.now(timezone.utc)`. Naive datetimes
    are assumed UTC (we never compare against a local-tz fence here).
    """
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        return now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(now)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _parse_ts(ts_value: object) -> Optional[datetime]:
    """Parse an entry `ts` into an aware datetime, or None on failure.

    Accepts ISO-8601 strings (with or without offset, with or without `Z`).
    Treats naive timestamps as UTC. Anything that fails to parse — bad
    string, missing key, wrong type — returns `None`; callers then decide
    whether the entry is kept (TTL) or stable-deduped (dedup keeps newest).
    """
    if not isinstance(ts_value, str) or not ts_value:
        return None
    candidate = ts_value
    # `datetime.fromisoformat` only accepted "Z" suffixes from 3.11+. Be
    # defensive on older interpreters too — strip a trailing Z and treat
    # the rest as UTC.
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def prune_ledger(
    entries: list[dict],
    *,
    now: Union[datetime, str, None] = None,
    ttl_days: int = TTL_DAYS_DEFAULT,
    cap: int = CAP_DEFAULT,
    skiplist: Optional[set[str]] = None,
) -> list[dict]:
    """Apply the keeper's deterministic prune rules.

    Order matters and is documented in spec §D3:

      1. **TTL**: drop entries whose `ts` is older than `now - ttl_days`.
         Entries with malformed/missing `ts` are KEPT (don't silently drop
         on parse error — surface the bug instead).
      2. **Skiplist**: drop entries whose `evidence_hash` is in `skiplist`.
      3. **Dedup**: collapse entries with the same `evidence_hash` to the
         single most-recent one (by `ts`). Ties on identical `ts` keep the
         first occurrence (stable).
      4. **FIFO cap**: if the survivor count > `cap`, drop the oldest by
         `ts` ascending until `len == cap`.

    Pure function — input list is not mutated, a new list is returned.
    `now` accepts a `datetime` or ISO string for ergonomics.
    """
    if skiplist is None:
        skiplist = set()
    fence = _coerce_now(now) - timedelta(days=ttl_days)

    # Step 1: TTL.
    after_ttl: list[dict] = []
    for entry in entries:
        parsed = _parse_ts(entry.get("ts"))
        if parsed is None:
            after_ttl.append(entry)  # malformed ts → keep (loud > silent)
            continue
        if parsed >= fence:
            after_ttl.append(entry)

    # Step 2: skiplist.
    after_skip = [
        entry for entry in after_ttl
        if entry.get("evidence_hash") not in skiplist
    ]

    # Step 3: dedup by evidence_hash, keeping the most recent ts. Stable on
    # tie: the first entry to claim the hash wins. Entries without a hash
    # bypass dedup (every such entry is its own bucket).
    deduped: list[dict] = []
    seen: dict[str, int] = {}  # evidence_hash -> index in deduped
    for entry in after_skip:
        evidence_hash = entry.get("evidence_hash")
        if not evidence_hash:
            deduped.append(entry)
            continue
        if evidence_hash not in seen:
            seen[evidence_hash] = len(deduped)
            deduped.append(entry)
            continue
        existing_idx = seen[evidence_hash]
        existing = deduped[existing_idx]
        existing_ts = _parse_ts(existing.get("ts"))
        candidate_ts = _parse_ts(entry.get("ts"))
        # Keep the entry with the later ts; ties + parse-failures fall back
        # to "keep the first one we saw" (stable).
        if candidate_ts is not None and (
            existing_ts is None or candidate_ts > existing_ts
        ):
            deduped[existing_idx] = entry

    # Step 4: FIFO cap. Drop oldest first (by ts ASC) until len == cap.
    if len(deduped) <= cap:
        return list(deduped)

    indexed = list(enumerate(deduped))
    # Sort by ts ASC; entries with unparseable ts sort *first* (they're
    # the most expendable from a recency standpoint, but keep their
    # relative order). After picking survivors we restore original order.
    def _age_key(item: tuple[int, dict]) -> tuple[int, datetime, int]:
        idx, entry = item
        parsed = _parse_ts(entry.get("ts"))
        if parsed is None:
            return (0, datetime.min.replace(tzinfo=timezone.utc), idx)
        return (1, parsed, idx)

    indexed.sort(key=_age_key)
    survivors = indexed[-cap:]
    survivors.sort(key=lambda item: item[0])  # restore insertion order
    return [entry for _, entry in survivors]
