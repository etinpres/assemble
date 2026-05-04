# tests/unit/test_wrote_parser.py
from server.harness import extract_wrote_paths


def test_returns_empty_when_no_wrote_line():
    assert extract_wrote_paths("just prose\nno path here") == []


def test_returns_single_path():
    assert extract_wrote_paths("WROTE: /tmp/a.json") == ["/tmp/a.json"]


def test_returns_paths_in_order_with_multiple():
    out = "WROTE: /old\nClassification ok\nWROTE: /new\n"
    paths = extract_wrote_paths(out)
    assert paths == ["/old", "/new"]
    # Last-match semantic the caller relies on
    assert paths[-1] == "/new"


def test_ignores_inline_wrote_in_prose():
    out = "Note: WROTE: literal in prose\nWROTE: /real/path\n"
    assert extract_wrote_paths(out) == ["/real/path"]


def test_strips_trailing_whitespace():
    assert extract_wrote_paths("WROTE: /tmp/a.json   ") == ["/tmp/a.json"]


def test_handles_b11_real_dispatch_pattern():
    """B-11 real-dispatch Step 3 emitted prose THEN WROTE:."""
    out = (
        "Classification correct: 2 allow-hits, 0 deny, 0 unrelated.\n"
        "WROTE: /Users/y/.claude/channels/assemble/runs/abc/classification.json\n"
    )
    paths = extract_wrote_paths(out)
    assert len(paths) == 1
    assert paths[0].endswith("/classification.json")
