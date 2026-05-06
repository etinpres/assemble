"""V4 Spike XIV Phase A — ASSEMBLE_HOME body-region auto-prepend.

When `os.environ['ASSEMBLE_HOME']` is set at `wrap_with_preamble` call time,
the dispatch *body* (NOT the preamble) is prepended with a `[ENV]` hint line
so sub-agents that import `server.*` modules inherit the same home directory
as the orchestrator.

Critical invariants pinned by this test file:
  - canonical preamble v3 sha256 (`8d22a29c…089a9`) is preserved byte-for-byte
    in both env-set and env-unset cases.
  - When ASSEMBLE_HOME is not set, `wrap_with_preamble(prompt)` body equals
    `prompt` (no leak of the [ENV] line).
  - When ASSEMBLE_HOME is set, the body's first line begins with
    `[ENV] 이 dispatch는 ASSEMBLE_HOME=<value>`.
  - `record_dispatch` + `verify_dispatches` continue to validate green —
    the audit trail compares the preamble portion only, so body-region
    injection is invisible to the audit constant.
"""

import hashlib
import importlib
import json
import os
from pathlib import Path

import pytest


CANONICAL_V3_SHA = (
    "8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9"
)


def _reload_harness():
    import server.harness as h
    importlib.reload(h)
    return h


def _stage_real_assemble(tmp_path: Path) -> Path:
    """Stage the real assemble dir under tmp via symlink so `_load_preamble`
    finds the canonical v3 preamble while runs/ stays isolated.
    """
    real_home = Path.home()
    bundled_link = tmp_path / ".claude/skills/assemble"
    bundled_link.parent.mkdir(parents=True, exist_ok=True)
    bundled_link.symlink_to(real_home / ".claude/skills/assemble")
    return tmp_path


def test_assemble_home_unset_no_injection(tmp_path, monkeypatch):
    """When ASSEMBLE_HOME is absent from os.environ, `wrap_with_preamble`
    must NOT inject the [ENV] line — body == prompt unchanged.

    The preamble is loaded from a stub under tmp_path (set via monkeypatch
    over HOME, since ASSEMBLE_HOME itself is absent). After loading we
    `delenv` ASSEMBLE_HOME so the wrap path takes the "no env" branch.
    """
    # Stub preamble under HOME (not ASSEMBLE_HOME — we want the env unset).
    monkeypatch.setenv("HOME", str(tmp_path))
    pre_path = (
        tmp_path / ".claude/skills/assemble/bundled/_shared/harness-preamble.md"
    )
    pre_path.parent.mkdir(parents=True, exist_ok=True)
    pre_path.write_text("[HARNESS]\n1. r1\n2. r2\n")
    monkeypatch.delenv("ASSEMBLE_HOME", raising=False)
    h = _reload_harness()

    prompt = "hello world"
    out = h.wrap_with_preamble(prompt)
    pre, body = h._split_preamble_body(out)
    assert body == prompt, (
        f"ASSEMBLE_HOME unset must not inject any [ENV] line; got body={body!r}"
    )
    # And the preamble portion is the loaded preamble bytes, byte-for-byte.
    # `_load_preamble` returns rstripped-content + "\n"; `_split_preamble_body`
    # peels off the `\n[TASK]\n` delimiter, leaving the same trailing newline.
    assert pre == pre_path.read_text(encoding="utf-8").rstrip() + "\n"


def test_assemble_home_set_injects_first_body_line(tmp_path, monkeypatch):
    """When ASSEMBLE_HOME is set, the body's first line must start with
    `[ENV] 이 dispatch는 ASSEMBLE_HOME=<value>`."""
    _stage_real_assemble(tmp_path)
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h = _reload_harness()

    prompt = "hello world"
    out = h.wrap_with_preamble(prompt)
    pre, body = h._split_preamble_body(out)
    expected_prefix = f"[ENV] 이 dispatch는 ASSEMBLE_HOME={tmp_path}"
    assert body.startswith(expected_prefix), (
        f"ASSEMBLE_HOME set must inject [ENV] line as first body line; "
        f"got body[:160]={body[:160]!r}"
    )
    # The original prompt body must still appear after the [ENV] line
    # (i.e. it's prepended, not replaced).
    assert prompt in body, (
        f"original prompt must still appear in body after injection; "
        f"got body={body!r}"
    )


def test_preamble_portion_byte_identity(tmp_path, monkeypatch):
    """Preamble portion of the wrapped output hashes to canonical v3 sha
    in both env-set and env-unset cases. This guarantees the audit
    invariant (record_dispatch preamble_sha256) is unchanged.
    """
    _stage_real_assemble(tmp_path)

    # Case 1: ASSEMBLE_HOME unset — fall back to HOME (which we point at
    # tmp_path so the staged preamble resolves).
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ASSEMBLE_HOME", raising=False)
    h = _reload_harness()
    out_unset = h.wrap_with_preamble("payload-unset")
    pre_unset, _ = h._split_preamble_body(out_unset)
    sha_unset = hashlib.sha256(pre_unset.encode("utf-8")).hexdigest()
    assert sha_unset == CANONICAL_V3_SHA, (
        f"preamble sha drift (env unset): got {sha_unset}, want {CANONICAL_V3_SHA}"
    )

    # Case 2: ASSEMBLE_HOME set — preamble portion must still hash to v3 sha.
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h = _reload_harness()
    out_set = h.wrap_with_preamble("payload-set")
    pre_set, body_set = h._split_preamble_body(out_set)
    sha_set = hashlib.sha256(pre_set.encode("utf-8")).hexdigest()
    assert sha_set == CANONICAL_V3_SHA, (
        f"preamble sha drift (env set): got {sha_set}, want {CANONICAL_V3_SHA}"
    )
    # And canonical_preamble_sha256() agrees.
    assert h.canonical_preamble_sha256() == CANONICAL_V3_SHA
    # The [ENV] injection landed in body, not preamble.
    assert body_set.startswith("[ENV] 이 dispatch는 ASSEMBLE_HOME=")


def test_record_dispatch_audit_still_green(tmp_path, monkeypatch):
    """record_dispatch + verify_dispatches must remain green after the
    [ENV] body-region injection. Audit compares preamble_sha256 only —
    body changes are invisible to the audit.
    """
    _stage_real_assemble(tmp_path)
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    h = _reload_harness()

    rid = "rid-spike-xiv-A"
    prompt = h.wrap_with_preamble("body content")
    h.record_dispatch(
        rid,
        "stepA.spike-xiv",
        prompt,
        subagent_type="general-purpose",
        description="Spike XIV Phase A audit smoke",
        prompt_file="prd_step2.md",
    )

    # Confirm row landed under the expected runs root.
    runs_root = tmp_path / ".claude/channels/assemble/runs" / rid
    jsonl = runs_root / "dispatches.jsonl"
    assert jsonl.exists(), f"dispatches.jsonl not created at {jsonl}"
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line]
    assert len(rows) == 1
    # The recorded preamble_sha must equal the canonical v3 sha.
    assert rows[0]["preamble_sha256"] == CANONICAL_V3_SHA

    # verify_dispatches must report ok=True / no mismatches.
    res = h.verify_dispatches(rid)
    assert res["ok"] is True, (
        f"verify_dispatches must be green after [ENV] injection; "
        f"mismatches={res.get('mismatches')}"
    )
    assert res["total"] == 1
    assert res["mismatches"] == []
    assert res["canonical_preamble_sha256"] == CANONICAL_V3_SHA
