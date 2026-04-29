# Test anchoring on SKILL.md prose

This doc captures the testing pattern that contributors MUST follow when adding `tests/unit/test_plan_pack_skill.py` (or similar SKILL.md text-shape regression tests).

## The rule

**Do NOT use `body[:N]` or `step_x[:N]` window slices to grep SKILL.md prose.** Always anchor on heading boundaries via the `_section()` helper at the top of `test_plan_pack_skill.py`.

## Why

SKILL.md grows over time as the workflow gains steps and sub-sections. Window slices like `step6[:3500]` encode an assumption that the asserted phrase appears within the first 3500 characters of a section. As soon as a contributor adds 1.7KB of new prose to that section (B-4 retro #1 — exactly the iter-scope-fix incident), the prior `[:3500]` window misses the target and the test fails for an irrelevant offset reason — not because the contract was actually violated.

Three observed failure modes from B-2 / B-3 / B-4:

- Task 2 (B-4): `body.index("Step 13")` matched a NOTE block before the actual `### Step 13` heading. Window picked the wrong region.
- Task 3 (B-4): test required exact `"design direction"` but spec used `"design-direction"` (hyphen). Spec-vs-test mismatch.
- iter-scope-fix (B-4 fix-up): 1.7KB new content pushed prior `[:2000]` / `[:2500]` windows out. 2 prior tests broke; widened to `[:5000]`.

In B-5 the `[:3500]` window for the `Iteration write order` test broke again when the multi-iteration loop block was added; the wholesale refactor finally landed in this quality pass (Items C + D).

## How to anchor

Use the `_section()` helper:

```python
from tests.unit.test_plan_pack_skill import _section  # or import from a shared util

body = SKILL.read_text()
step6 = _section(body, "### Step 6")     # "### Step 6" through next sibling-or-shallower heading
assert "iteration" in step6.lower()
assert "AskUserQuestion" in step6
```

The helper:

1. Finds the heading line (must include leading hash markers, e.g. `### Step 6`).
2. Scans forward and stops at the first heading line of equal-or-shallower depth.
3. Returns the bounded slice from heading to next sibling/parent.

### Acceptable patterns

- `_section(body, "### Step N")` — bounded section by heading anchor (PREFERRED).
- `body[body.index("### Step 2"):body.index("### Step 4")]` — bounded between two heading anchors (acceptable; `_section()` is preferred but explicit boundary is also fine when the next heading isn't a sibling).
- `assert "X" in body` — full-document substring presence (acceptable for skill-level invariants like "orchestrator-only").

### Forbidden patterns

- `body[:N]` — arbitrary character window on the full document.
- `body[body.index("X"):][:N]` — heading-anchored start with arbitrary tail window.
- `step_X[:N]` — window slice on a heading-anchored variable.
- `body.index("Step N")` (no hashes) — matches role-table cells or other text. Use `### Step N` form.

## Helper code

The helper lives at the top of `tests/unit/test_plan_pack_skill.py` (lines ~20-47). If you add another test file that needs the same pattern, copy the helper. (Promoting it to a shared `tests/_util.py` is queued for a future quality pass.)

```python
def _section(body: str, heading: str) -> str:
    """Return the body block from `heading` through the next sibling-or-shallower heading line.

    `heading` must include leading hash markers, e.g. "### Step 6". The
    function locates the heading, then scans forward and stops at the first
    heading line of equal-or-shallower depth.
    """
    start = body.index(heading)
    depth = len(heading) - len(heading.lstrip("#"))
    nl = body.find("\n", start)
    if nl == -1:
        return body[start:]
    cursor = nl + 1
    while cursor < len(body):
        next_nl = body.find("\n", cursor)
        line_end = next_nl if next_nl != -1 else len(body)
        line = body[cursor:line_end]
        if line.startswith("#"):
            line_depth = len(line) - len(line.lstrip("#"))
            if line_depth <= depth and not line.startswith(heading):
                return body[start:cursor]
        if next_nl == -1:
            break
        cursor = next_nl + 1
    return body[start:]
```

## When in doubt

If the assertion you want needs to land in a sub-section (e.g. `#### Step 4b` inside `### Step 4`), prefer the deeper heading anchor:

```python
step4b = _section(body, "#### Step 4b")
assert "verify before appending" in step4b.lower()
```

Heading depth flexibility is built into the helper — `####` slices stop at the next `####` / `###` / `##` / `#` heading.
