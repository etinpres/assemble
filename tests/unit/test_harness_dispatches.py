"""Unit tests for record_dispatch + verify_dispatches (gate B5.7 evidence upgrade).

These pin the contract that the orchestrator's "preamble byte-identity" claim
moves from self-report into a replayable on-disk audit
(`runs/<rid>/dispatches.jsonl`).
"""

import hashlib
import importlib
import json
from pathlib import Path

import pytest


def _reload_harness():
    import server.harness as h
    importlib.reload(h)
    return h


def _stub_preamble(home: Path, body: str = "[HARNESS]\n1. r1\n2. r2\n"):
    p = home / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _runs_root(home: Path) -> Path:
    return home / ".claude/channels/assemble/runs"


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_record_dispatch_creates_run_dir_and_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    prompt = h.wrap_with_preamble("body content")
    out = h.record_dispatch("rid-001", "step6.iter2.PRD", prompt,
                             subagent_type="general-purpose",
                             description="iter2 PRD re-draft",
                             prompt_file="prd_step2.md")
    assert out.exists()
    assert out == _runs_root(tmp_path) / "rid-001" / "dispatches.jsonl"
    rows = _read_jsonl(out)
    assert len(rows) == 1
    rec = rows[0]
    assert rec["step"] == "step6.iter2.PRD"
    assert rec["subagent_type"] == "general-purpose"
    assert rec["description"] == "iter2 PRD re-draft"
    # B1 (Spike III §1.2): prompt_file is recorded in the audit trail.
    assert rec["prompt_file"] == "prd_step2.md"


def test_record_dispatch_preamble_sha_matches_canonical(tmp_path, monkeypatch):
    """The recorded preamble_sha256 must equal canonical_preamble_sha256().
    This is the entire point of B5.7 — the audit constant.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    prompt = h.wrap_with_preamble("payload")
    h.record_dispatch("rid-002", "step", prompt)
    rows = _read_jsonl(_runs_root(tmp_path) / "rid-002" / "dispatches.jsonl")
    assert rows[0]["preamble_sha256"] == h.canonical_preamble_sha256()


def test_record_dispatch_body_sha_correct(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    body = "the body content"
    prompt = h.wrap_with_preamble(body)
    h.record_dispatch("rid-003", "s", prompt)
    rows = _read_jsonl(_runs_root(tmp_path) / "rid-003" / "dispatches.jsonl")
    assert rows[0]["body_sha256"] == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert rows[0]["body_bytes"] == len(body.encode("utf-8"))


def test_record_dispatch_appends_multiple(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    for i in range(5):
        h.record_dispatch("rid-multi", f"step{i}", h.wrap_with_preamble(f"body-{i}"))
    rows = _read_jsonl(_runs_root(tmp_path) / "rid-multi" / "dispatches.jsonl")
    assert len(rows) == 5
    assert [r["step"] for r in rows] == [f"step{i}" for i in range(5)]


def test_record_dispatch_unwrapped_prompt_records_with_empty_preamble(
    tmp_path, monkeypatch
):
    """If caller passes a prompt without the [TASK] delimiter, the dispatch
    is still recorded (degraded mode). preamble_sha is sha256 of empty bytes;
    body holds the raw prompt. verify_dispatches will catch this as a mismatch.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    h.record_dispatch("rid-bare", "step.bare", "no preamble at all")
    rows = _read_jsonl(_runs_root(tmp_path) / "rid-bare" / "dispatches.jsonl")
    empty_sha = hashlib.sha256(b"").hexdigest()
    assert rows[0]["preamble_sha256"] == empty_sha
    assert rows[0]["preamble_bytes"] == 0
    assert rows[0]["body_bytes"] == len("no preamble at all".encode("utf-8"))


def test_record_dispatch_rejects_unsafe_run_id(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    prompt = h.wrap_with_preamble("x")
    for bad in ["", "../escape", "/abs", "a/b", "a\\b", ".hidden"]:
        with pytest.raises(ValueError):
            h.record_dispatch(bad, "step", prompt)


def test_record_dispatch_requires_step(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    prompt = h.wrap_with_preamble("x")
    with pytest.raises(ValueError):
        h.record_dispatch("rid-x", "", prompt)


def test_canonical_preamble_sha256_returns_none_if_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # Do NOT create the preamble file.
    h = _reload_harness()
    assert h.canonical_preamble_sha256() is None


def test_verify_dispatches_green_when_all_match(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    for i in range(3):
        h.record_dispatch("rid-ok", f"step{i}", h.wrap_with_preamble(f"b{i}"))
    res = h.verify_dispatches("rid-ok")
    assert res["ok"] is True
    assert res["total"] == 3
    assert res["mismatches"] == []
    assert res["missing_file"] is False


def test_verify_dispatches_red_on_mismatch(tmp_path, monkeypatch):
    """Manually corrupt one record to simulate a sub-agent dispatched with
    a wrong-preamble prompt. verify_dispatches should flag it.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    h.record_dispatch("rid-bad", "good", h.wrap_with_preamble("a"))
    h.record_dispatch("rid-bad", "good", h.wrap_with_preamble("b"))
    # Corrupt second line
    p = _runs_root(tmp_path) / "rid-bad" / "dispatches.jsonl"
    rows = _read_jsonl(p)
    rows[1]["preamble_sha256"] = "0" * 64  # bad sha
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    res = h.verify_dispatches("rid-bad")
    assert res["ok"] is False
    assert res["total"] == 2
    assert len(res["mismatches"]) == 1
    assert res["mismatches"][0]["line"] == 2
    assert res["mismatches"][0]["got"] == "0" * 64
    assert res["mismatches"][0]["want"] == h.canonical_preamble_sha256()


def test_verify_dispatches_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    res = h.verify_dispatches("never-recorded")
    assert res["ok"] is False
    assert res["missing_file"] is True
    assert res["total"] == 0


def test_verify_dispatches_empty_file_is_ok(tmp_path, monkeypatch):
    """A run where dispatches.jsonl exists but has no entries (e.g. created
    but never written into) is ok=True with total=0. The audit stance is:
    "no records to falsify" rather than "no records means broken."
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    p = _runs_root(tmp_path) / "rid-empty" / "dispatches.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    res = h.verify_dispatches("rid-empty")
    assert res["ok"] is True
    assert res["total"] == 0
    assert res["missing_file"] is False


# v1 sha256 (pre-Spike I): kept here as fallback for dogfood data written
# before 2026-04-30. v2 is the live value. See
# docs/research/2026-04-30-preamble-v2-cutoff.md for the cutoff memo.
EXPECTED_PREAMBLE_V3_SHA = "8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9"
EXPECTED_PREAMBLE_V2_SHA = "df27450513c019a9dd395d8f62c99b445e7a16b4fcdbb5cba52c352397993549"  # noqa: ALLOW_LIST
EXPECTED_PREAMBLE_V1_SHA = "858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159"  # noqa: ALLOW_LIST


def test_record_dispatch_full_byte_identity_with_real_canonical_preamble(monkeypatch):
    """Smoke test against the actual repo preamble file (sha 8d22a29c... v3).

    Live preamble is v3 after Spike II §3.1 F12 cutoff. v1/v2 stay in
    ALLOW_LIST for backward compat with old dogfood data.
    """
    import os
    real_preamble = Path(os.path.expanduser(
        "~/.claude/skills/assemble/bundled/_shared/harness-preamble.md"
    ))
    if not real_preamble.exists():
        pytest.skip("real preamble not present")
    expected_sha = hashlib.sha256(real_preamble.read_bytes()).hexdigest()
    import server.harness as h
    importlib.reload(h)
    assert h.canonical_preamble_sha256() == expected_sha
    assert expected_sha == EXPECTED_PREAMBLE_V3_SHA


def test_record_dispatch_wrote_path_optional(tmp_path, monkeypatch):
    """Spike I §8.1: record_dispatch accepts optional `wrote_path` kwarg.

    Default (omitted) → record's `wrote_path` is None (back-compat).
    Provided → record's `wrote_path` is the supplied string.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _stub_preamble(tmp_path)
    h = _reload_harness()
    prompt = h.wrap_with_preamble("wrapped prompt")
    # call without wrote_path (back-compat)
    h.record_dispatch(
        "rid-wrote",
        "step8",
        prompt,
        subagent_type="general-purpose",
        description="test",
    )
    # call with wrote_path (new)
    h.record_dispatch(
        "rid-wrote",
        "step8",
        prompt,
        subagent_type="general-purpose",
        description="test",
        wrote_path="/tmp/foo/PRD.md",
    )
    rows = _read_jsonl(_runs_root(tmp_path) / "rid-wrote" / "dispatches.jsonl")
    assert len(rows) == 2
    assert rows[0]["wrote_path"] is None
    assert rows[1]["wrote_path"] == "/tmp/foo/PRD.md"


def test_verify_dispatches_accepts_v1_v2_sha(tmp_path, monkeypatch):
    """Spike I §8.3: verify_dispatches must accept both v1 and v2 preamble sha
    so pre-cutoff dogfood data (written before 2026-04-30 with v1 preamble)
    still verifies green when read back under the v2 canonical preamble.
    """
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # Stub the v2 preamble on disk (canonical_preamble_sha256 returns v2 sha).
    # Then write a dispatches.jsonl record by hand whose preamble_sha256 is
    # the v1 sha — simulating data persisted under the old preamble.
    _stub_preamble(tmp_path)
    h = _reload_harness()
    rid = "rid-v1-data"
    runs_dir = _runs_root(tmp_path) / rid
    runs_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": "2026-04-29T00:00:00Z",
        "step": "legacy.step",
        "subagent_type": "general-purpose",
        "description": "pre-cutoff data",
        "preamble_sha256": EXPECTED_PREAMBLE_V1_SHA,
        "preamble_bytes": 256,
        "body_sha256": hashlib.sha256(b"body").hexdigest(),
        "body_bytes": 4,
        "wrote_path": None,
    }
    (runs_dir / "dispatches.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    res = h.verify_dispatches(rid)
    assert res["ok"] is True, (
        f"verify_dispatches must accept v1 sha for back-compat, "
        f"got mismatches={res['mismatches']}"
    )
    assert res["total"] == 1
    assert res["mismatches"] == []


def test_v2_dogfood_data_still_verifies_under_v3_canonical(tmp_path, monkeypatch):
    """Spike II §3.1 F12: v2 sha256 (Spike I dogfood era) must verify ok=True
    under v3 canonical. ALLOW_LIST = v1 + v2 + canonical.
    """
    import json
    from server.harness import verify_dispatches, _PREAMBLE_V2_SHA256
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    rid = "20260430-test"
    rd = tmp_path / ".claude/channels/assemble/runs" / rid
    rd.mkdir(parents=True)
    rec = {
        "ts": "2026-04-30T12:00:00Z",
        "step": "step6.iter0.PRD",
        "subagent_type": "general-purpose",
        "description": "v2-era dispatch",
        "preamble_sha256": _PREAMBLE_V2_SHA256,
        "preamble_bytes": 1024,
        "body_sha256": "deadbeef" * 8,
        "body_bytes": 200,
        "wrote_path": None,
    }
    (rd / "dispatches.jsonl").write_text(json.dumps(rec) + "\n")
    result = verify_dispatches(rid)
    assert result["ok"], f"v2 ALLOW_LIST regression: {result}"
    assert result["total"] == 1
    assert result["mismatches"] == []


def test_record_dispatch_new_schema_fields_default(tmp_path, monkeypatch):
    """Spike IV: every new row carries `status` (default 'dispatched')
    and `note` (default None) in addition to existing fields."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    monkeypatch.setenv("ASSEMBLE_DISPATCH_STRICT", "0")
    rid = "test-spike-iv-default"
    (tmp_path / ".claude/channels/assemble/runs" / rid).mkdir(parents=True)
    from server.harness import record_dispatch
    record_dispatch(
        rid,
        step="unit",
        prompt_text="body",
        prompt_file="prd_step2.md",
    )
    log = tmp_path / ".claude/channels/assemble/runs" / rid / "dispatches.jsonl"
    import json
    row = json.loads(log.read_text().splitlines()[0])
    assert row["status"] == "dispatched"
    assert row["note"] is None
