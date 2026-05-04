"""Unit tests for `bundled/keeper/scripts/extract_rules.py`
(V4 Spike X, Task B3).

The script is stdlib-only and invokable as a CLI; tests exercise both
its module-level entry points (importable for fast unit-style cases)
and its full CLI surface (subprocess invocation for the determinism
+ exit-code contract).

Filesystem isolation: every fixture seeds artifacts in a fresh
``tmp_path`` run_dir. R4 uses a real git fixture repo so the rule's
``git diff --unified=0 HEAD~..HEAD`` probe is exercised end-to-end
(per project convention — real git over subprocess monkeypatching).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Module loading — script lives outside the importable `server.*` tree.
# ---------------------------------------------------------------------------

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "bundled"
    / "keeper"
    / "scripts"
    / "extract_rules.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("keeper_extract_rules", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def extract_rules():
    return _load_module()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_audit_inventory(run_dir: Path, *, run_id: str = "run-test",
                           git_diff_files: list[str] | None = None) -> None:
    inv = {
        "run_id": run_id,
        "verdict": "audit-ready",
        "bundles_observed": [],
        "artifacts_present": {},
        "dispatch_row_count": 0,
        "verdicts_collected": {},
        "git_probes": {
            "clean_tree": True,
            "dirty_files": [],
            "head_sha": "abc123",
            "branch": "master",
            "git_diff_files": git_diff_files or [],
        },
        "scope_summary": "",
        "errors": [],
    }
    (run_dir / "audit_inventory.json").write_text(
        json.dumps(inv, sort_keys=True), encoding="utf-8"
    )


def _write_parsed_scope(run_dir: Path, *, deny: list[str] | None = None) -> None:
    scope = {"task_summary": "x", "deny": deny or []}
    (run_dir / "parsed_scope.json").write_text(
        json.dumps(scope), encoding="utf-8"
    )


def _write_dispatches(run_dir: Path, rows: list[dict]) -> None:
    lines = [json.dumps(r) for r in rows]
    (run_dir / "dispatches.jsonl").write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )


def _write_verify_result(run_dir: Path, payload: dict) -> None:
    (run_dir / "verify_result.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _make_git_repo_with_todo(repo: Path, marker: str = "TODO") -> None:
    """Create a real git repo with an initial commit + a follow-up commit
    that *adds* a line containing ``marker``. Used to exercise R4's
    ``git diff --unified=0 HEAD~..HEAD`` probe end-to-end.
    """
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True
    )
    (repo / "f.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=repo, check=True,
    )
    # Second commit adds a marker line.
    (repo / "f.py").write_text(
        f"def hello():\n    return 1\n    # {marker}: clean this up\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "add marker"],
        cwd=repo, check=True,
    )


def _make_git_repo_no_marker_change(repo: Path) -> None:
    """Two-commit repo where neither commit adds a TODO/FIXME/XXX line.

    The initial file already contains ``TODO`` (so a naive ``grep TODO``
    would false-positive) but the diff between HEAD~ and HEAD only
    *changes a comment*, never adds a marker line — R4 must not fire.
    """
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True
    )
    # Initial commit already has a TODO, but it's *not added in the diff
    # we'll inspect* (HEAD~..HEAD).
    (repo / "f.py").write_text(
        "# TODO: existing\ndef hello():\n    return 1\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=repo, check=True,
    )
    # Second commit modifies the function body — does not add a TODO line.
    (repo / "f.py").write_text(
        "# TODO: existing\ndef hello():\n    return 2\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "bump return value"],
        cwd=repo, check=True,
    )


# ---------------------------------------------------------------------------
# 1 — exit code 1 when audit_inventory.json missing
# ---------------------------------------------------------------------------

def test_missing_audit_inventory_exits_1(tmp_path):
    """Script must exit non-zero (1) and emit no WROTE line when the
    Step 1 artifact is absent.
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "WROTE:" not in proc.stdout
    assert "audit_inventory.json" in proc.stderr


# ---------------------------------------------------------------------------
# 2 — empty run still writes candidates with empty list
# ---------------------------------------------------------------------------

def test_empty_run_writes_candidates_with_empty_list(extract_rules, tmp_path):
    """audit_inventory.json present, no other artifacts, no diff —
    extract still emits a well-formed file with candidates: [].
    """
    _write_audit_inventory(tmp_path)
    # Pass cwd to a fresh non-git tmpdir so R4 returns []
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    assert result["run_id"] == "run-test"
    assert result["candidates"] == []
    out = extract_rules.write_candidates(tmp_path, result)
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["candidates"] == []


# ---------------------------------------------------------------------------
# 3-4 — R1 dispatch failures (per row)
# ---------------------------------------------------------------------------

def test_R1_dispatch_failure_emits_per_row(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    _write_dispatches(tmp_path, [
        {"step": "step1", "subagent_type": "general-purpose",
         "status": "failed", "note": "boom"},
        {"step": "step2", "subagent_type": "general-purpose",
         "status": "ok"},
        {"step": "step3", "subagent_type": "general-purpose",
         "status": "failed", "note": "kapow"},
    ])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r1s = [c for c in result["candidates"] if c["rule_id"] == "R1"]
    assert len(r1s) == 2
    notes = sorted(c["evidence"]["note"] for c in r1s)
    assert notes == ["boom", "kapow"]
    for c in r1s:
        assert c["category"] == "rule-violation"
        assert "evidence_hash" in c


def test_R1_no_failed_dispatches_no_candidates(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    _write_dispatches(tmp_path, [
        {"step": "step1", "status": "ok"},
        {"step": "step2", "status": "ok"},
    ])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    assert all(c["rule_id"] != "R1" for c in result["candidates"])


# ---------------------------------------------------------------------------
# 5-7 — R2 scope deviation (deny ∩ diff)
# ---------------------------------------------------------------------------

def test_R2_deny_pattern_matches_diff_file(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path, git_diff_files=["src/auth.py", "README.md"])
    _write_parsed_scope(tmp_path, deny=["src/auth.py"])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 1
    assert r2s[0]["category"] == "scope-deviation"
    assert r2s[0]["evidence"] == {
        "file": "src/auth.py", "deny_pattern": "src/auth.py"
    }


def test_R2_deny_pattern_fnmatch_wildcard(extract_rules, tmp_path):
    _write_audit_inventory(
        tmp_path,
        git_diff_files=["auth/login.py", "billing/index.py"],
    )
    _write_parsed_scope(tmp_path, deny=["auth/*"])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 1
    assert r2s[0]["evidence"]["file"] == "auth/login.py"


def test_R2_no_overlap_no_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path, git_diff_files=["docs/readme.md"])
    _write_parsed_scope(tmp_path, deny=["src/auth.py"])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    assert all(c["rule_id"] != "R2" for c in result["candidates"])


# ---------------------------------------------------------------------------
# 7a-7e — R2 deny shape tolerance (Codex retro F1, V4 fix)
#
# The production parser (server/scope_parser.py) emits deny entries as
# list[{"path": str, "note": str}] but legacy / hand-authored fixtures
# use list[str]. _load_deny_patterns must accept both shapes; otherwise
# R2 silently false-negatives on real V4 parsed_scope.json files.
# ---------------------------------------------------------------------------

def _write_parsed_scope_raw(run_dir: Path, deny: list) -> None:
    """Variant of _write_parsed_scope that writes any list shape verbatim
    (does not enforce list[str]). Used for production-schema fixtures.
    """
    scope = {"task_summary": "x", "deny": deny}
    (run_dir / "parsed_scope.json").write_text(
        json.dumps(scope), encoding="utf-8"
    )


def test_R2_deny_object_form_matches_diff_file(extract_rules, tmp_path):
    """Production parser schema: deny entries are {"path": str, "note": str}."""
    _write_audit_inventory(tmp_path, git_diff_files=["src/auth.py", "README.md"])
    _write_parsed_scope_raw(
        tmp_path,
        deny=[{"path": "src/auth.py", "note": "auth code"}],
    )
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 1
    assert r2s[0]["category"] == "scope-deviation"
    assert r2s[0]["evidence"] == {
        "file": "src/auth.py", "deny_pattern": "src/auth.py"
    }


def test_R2_deny_object_form_with_glob_pattern(extract_rules, tmp_path):
    """Production-schema deny with fnmatch glob pattern."""
    _write_audit_inventory(
        tmp_path,
        git_diff_files=["auth/login.py", "billing/index.py"],
    )
    _write_parsed_scope_raw(
        tmp_path,
        deny=[{"path": "auth/*", "note": "auth tree"}],
    )
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 1
    assert r2s[0]["evidence"]["file"] == "auth/login.py"
    assert r2s[0]["evidence"]["deny_pattern"] == "auth/*"


def test_R2_deny_string_form_still_works(extract_rules, tmp_path):
    """Regression-proof: legacy string-only fixture still produces R2.

    Guards against breaking the back-compat path while fixing the
    object-form path.
    """
    _write_audit_inventory(tmp_path, git_diff_files=["src/legacy.py"])
    _write_parsed_scope_raw(tmp_path, deny=["src/legacy.py"])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 1
    assert r2s[0]["evidence"] == {
        "file": "src/legacy.py", "deny_pattern": "src/legacy.py"
    }


def test_R2_deny_mixed_form_handled(extract_rules, tmp_path):
    """Mixed list of strings and dicts — both yield R2 candidates."""
    _write_audit_inventory(
        tmp_path,
        git_diff_files=["src/x.py", "src/y.py"],
    )
    _write_parsed_scope_raw(
        tmp_path,
        deny=[
            "src/x.py",
            {"path": "src/y.py", "note": "y is denied"},
        ],
    )
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 2
    files = sorted(c["evidence"]["file"] for c in r2s)
    assert files == ["src/x.py", "src/y.py"]


def test_R2_deny_malformed_object_skipped_silently(extract_rules, tmp_path):
    """Forward-compat: dict without 'path' key, or wrong types, are
    silently skipped (keeper is observational, never raises)."""
    _write_audit_inventory(tmp_path, git_diff_files=["src/auth.py"])
    _write_parsed_scope_raw(
        tmp_path,
        deny=[
            {"description": "missing path key"},
            {"path": 12345},          # path is not a string
            {"note": "no path"},
            None,                     # not str, not dict
        ],
    )
    non_git = tmp_path / "ng"; non_git.mkdir()
    # Must not raise.
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert r2s == []


# ---------------------------------------------------------------------------
# 8-10 — R3 ac-failure
# ---------------------------------------------------------------------------

def test_R3_verify_fail_emits_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    _write_verify_result(tmp_path, {
        "verdict": "fail",
        "command_executed": "pytest -q",
        "reason": "2 tests failed",
    })
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r3s = [c for c in result["candidates"] if c["rule_id"] == "R3"]
    assert len(r3s) == 1
    assert r3s[0]["category"] == "ac-failure"
    assert r3s[0]["evidence"] == {
        "command": "pytest -q", "reason": "2 tests failed"
    }


def test_R3_verify_pass_no_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    _write_verify_result(tmp_path, {"verdict": "pass"})
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    assert all(c["rule_id"] != "R3" for c in result["candidates"])


def test_R3_verify_missing_no_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    # No verify_result.json
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    assert all(c["rule_id"] != "R3" for c in result["candidates"])


# ---------------------------------------------------------------------------
# 11-14 — R4 TODO/FIXME/XXX leakage (real git fixture)
# ---------------------------------------------------------------------------

def test_R4_added_TODO_line_emits_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo_with_todo(repo, marker="TODO")
    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert len(r4s) >= 1
    assert any(c["evidence"]["marker"] == "TODO" for c in r4s)
    assert all(c["category"] == "todo-leakage" for c in r4s)


def test_R4_unchanged_TODO_no_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo_no_marker_change(repo)
    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert r4s == []


def test_R4_FIXME_marker_recognized(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo_with_todo(repo, marker="FIXME")
    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert any(c["evidence"]["marker"] == "FIXME" for c in r4s)


def test_R4_XXX_marker_recognized(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo_with_todo(repo, marker="XXX")
    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert any(c["evidence"]["marker"] == "XXX" for c in r4s)


# ---------------------------------------------------------------------------
# 15-16 — R5 aggregate dispatch failure
# ---------------------------------------------------------------------------

def test_R5_failed_dispatches_aggregated(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    _write_dispatches(tmp_path, [
        {"step": "step1", "status": "failed"},
        {"step": "step2", "status": "ok"},
        {"step": "step3", "status": "failed"},
    ])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r5s = [c for c in result["candidates"] if c["rule_id"] == "R5"]
    assert len(r5s) == 1
    assert r5s[0]["category"] == "dispatch-failure"
    assert r5s[0]["evidence"]["failed_count"] == 2
    assert sorted(r5s[0]["evidence"]["steps"]) == ["step1", "step3"]


def test_R5_no_failures_no_candidate(extract_rules, tmp_path):
    _write_audit_inventory(tmp_path)
    _write_dispatches(tmp_path, [
        {"step": "step1", "status": "ok"},
    ])
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    assert all(c["rule_id"] != "R5" for c in result["candidates"])


# ---------------------------------------------------------------------------
# 17 — evidence_hash determinism
# ---------------------------------------------------------------------------

def test_evidence_hash_deterministic(extract_rules):
    """Same evidence (regardless of dict ordering) → same hash;
    different evidence → different hash. Canonical-form JSON guarantee.
    """
    e1 = {"file": "a.py", "deny_pattern": "a*"}
    e1_reordered = {"deny_pattern": "a*", "file": "a.py"}
    e2 = {"file": "b.py", "deny_pattern": "a*"}
    h1 = extract_rules._hash_evidence(e1)
    h1b = extract_rules._hash_evidence(e1_reordered)
    h2 = extract_rules._hash_evidence(e2)
    assert h1 == h1b
    assert h1 != h2
    assert len(h1) == 64  # sha256 hex


# ---------------------------------------------------------------------------
# 18 — full-script idempotency (byte-identical output across two runs)
# ---------------------------------------------------------------------------

def test_script_idempotent(tmp_path):
    """Running the CLI twice on the same run_dir must produce
    byte-identical learning_candidates.json (sorted, canonical JSON).
    """
    _write_audit_inventory(
        tmp_path,
        git_diff_files=["src/auth.py", "src/billing.py"],
    )
    _write_parsed_scope(tmp_path, deny=["src/auth.py", "src/billing.py"])
    _write_dispatches(tmp_path, [
        {"step": "step3", "status": "failed", "note": "z"},
        {"step": "step1", "status": "failed", "note": "a"},
    ])
    _write_verify_result(tmp_path, {"verdict": "fail", "reason": "boom"})

    # Run #1
    proc1 = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc1.returncode == 0
    bytes1 = (tmp_path / "learning_candidates.json").read_bytes()

    # Run #2
    proc2 = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc2.returncode == 0
    bytes2 = (tmp_path / "learning_candidates.json").read_bytes()

    assert bytes1 == bytes2


# ---------------------------------------------------------------------------
# 19 — sort order: by (rule_id, evidence_hash)
# ---------------------------------------------------------------------------

def test_candidates_sorted_by_rule_then_hash(extract_rules, tmp_path):
    _write_audit_inventory(
        tmp_path,
        git_diff_files=["src/a.py", "src/b.py"],
    )
    _write_parsed_scope(tmp_path, deny=["src/a.py", "src/b.py"])
    _write_dispatches(tmp_path, [
        {"step": "stepZ", "status": "failed", "note": "n1"},
        {"step": "stepA", "status": "failed", "note": "n2"},
    ])
    _write_verify_result(tmp_path, {"verdict": "fail"})
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    cands = result["candidates"]
    # Must include R1, R2, R3, R5 (no R4 because cwd is not a git repo).
    rule_ids_seen = {c["rule_id"] for c in cands}
    assert {"R1", "R2", "R3", "R5"}.issubset(rule_ids_seen)

    # Sort key: (rule_id, evidence_hash) — verify by re-sorting and
    # comparing to the candidates list.
    keys = [(c["rule_id"], c["evidence_hash"]) for c in cands]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# F-X1 — R4 net-delta semantics (Spike X cleanup)
#
# A refactor that *moves* a pre-existing TODO line (delete from line N,
# add at line M) used to emit 1 spurious R4 candidate per addition even
# though the net marker count was unchanged. Fix: track adds and deletes
# per (marker, line excerpt) key and emit only net-positive candidates.
# ---------------------------------------------------------------------------

def _git_init(repo: Path) -> None:
    """Initialize a git repo with deterministic identity (no GPG signing)."""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True
    )


def _git_commit_all(repo: Path, msg: str) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=repo, check=True)


def test_R4_moved_TODO_line_no_candidate(extract_rules, tmp_path):
    """A pre-existing TODO line moved within the file (delete + add of
    the *identical text*) is a net zero — R4 must not emit a candidate.
    """
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    # Initial commit: TODO at line 2 of a 5-line file.
    (repo / "f.py").write_text(
        "def a():\n"
        "    # TODO: clean this up\n"
        "    return 1\n"
        "def b():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    _git_commit_all(repo, "initial")
    # Second commit: same TODO text moved to a different line. Net zero.
    (repo / "f.py").write_text(
        "def a():\n"
        "    return 1\n"
        "def b():\n"
        "    # TODO: clean this up\n"
        "    return 2\n",
        encoding="utf-8",
    )
    _git_commit_all(repo, "move TODO")

    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert r4s == [], (
        f"moved TODO with identical text must not emit R4; got {r4s!r}"
    )


def test_R4_modified_TODO_text_emits_one(extract_rules, tmp_path):
    """A TODO whose *text* changes is a net addition on the new excerpt
    (and net zero on the old excerpt). Exactly one R4 candidate, with
    the new text in evidence.
    """
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    (repo / "f.py").write_text(
        "def a():\n"
        "    # TODO: old text\n"
        "    return 1\n",
        encoding="utf-8",
    )
    _git_commit_all(repo, "initial")
    (repo / "f.py").write_text(
        "def a():\n"
        "    # TODO: new text\n"
        "    return 1\n",
        encoding="utf-8",
    )
    _git_commit_all(repo, "rephrase TODO")

    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert len(r4s) == 1, f"expected exactly 1 R4 candidate, got {len(r4s)}: {r4s!r}"
    assert "new text" in r4s[0]["evidence"]["line_excerpt"]
    assert "old text" not in r4s[0]["evidence"]["line_excerpt"]


def test_R4_added_two_removed_one_emits_one(extract_rules, tmp_path):
    """Net delta arithmetic: 2 added of identical text - 1 deleted of
    same text = 1 net candidate. Mixed-delta canary.
    """
    _write_audit_inventory(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    # Initial: one TODO.
    (repo / "f.py").write_text(
        "def a():\n"
        "    # TODO: same text\n"
        "    return 1\n",
        encoding="utf-8",
    )
    _git_commit_all(repo, "initial")
    # Second commit: delete that TODO line and add two identical-text TODOs
    # elsewhere. Net = +2 - 1 = +1.
    (repo / "f.py").write_text(
        "def a():\n"
        "    return 1\n"
        "def b():\n"
        "    # TODO: same text\n"
        "    pass\n"
        "def c():\n"
        "    # TODO: same text\n"
        "    pass\n",
        encoding="utf-8",
    )
    _git_commit_all(repo, "shuffle TODOs")

    result = extract_rules.extract_candidates(tmp_path, cwd=repo)
    r4s = [c for c in result["candidates"] if c["rule_id"] == "R4"]
    assert len(r4s) == 1, (
        f"expected 1 net R4 (added=2, deleted=1), got {len(r4s)}: {r4s!r}"
    )


# ---------------------------------------------------------------------------
# Lesson — Codex F1 carryforward: feed R2 the *production parser output*
#
# Spike X E2 surfaced that R2 tests used hand-authored ``deny: list[str]``
# fixtures even though the production parser ``server.scope_parser.parse_scope_md``
# emits ``deny: list[{"path": str, "note": str}]``. The fixture/schema
# drift was undetected for the entire B-D execution. This canary feeds
# R2 the actual parser output so any future schema change forces a
# lockstep update of ``extract_rules._load_deny_patterns``.
# ---------------------------------------------------------------------------

def test_R2_uses_production_parser_output_as_fixture(extract_rules, tmp_path):
    """End-to-end production-fixture test: real parse_scope_md output
    flows into extract_rules and produces R2 candidates."""
    from server.scope_parser import parse_scope_md

    scope_md = (
        "# SCOPE — production-fixture canary\n"
        "\n"
        "## Allow list\n"
        "\n"
        "- `src/feature.py` — main module\n"
        "\n"
        "## Deny list\n"
        "\n"
        "- `src/auth.py` — auth code untouched\n"
        "- `tests/integration/foo.py` — integration tests off-limits\n"
        "\n"
        "## Completion criterion\n"
        "\n"
        "```bash\n"
        "pytest -q\n"
        "```\n"
    )
    parsed = parse_scope_md(scope_md)

    # --- Production schema invariants (canary against drift) ---
    assert "deny" in parsed, "parser must emit a 'deny' key"
    assert len(parsed["deny"]) >= 2
    first_deny = parsed["deny"][0]
    assert isinstance(first_deny, dict), (
        "scope_parser.parse_scope_md must emit deny as list of dicts "
        "(production schema). If this changes, update "
        "extract_rules._load_deny_patterns."
    )
    assert "path" in first_deny and isinstance(first_deny["path"], str)

    # --- End-to-end: write parser output as parsed_scope.json, seed
    # audit_inventory with a matching diff file, run extract_rules,
    # assert R2 fires.
    (tmp_path / "parsed_scope.json").write_text(
        json.dumps(parsed), encoding="utf-8"
    )
    _write_audit_inventory(
        tmp_path,
        git_diff_files=["src/auth.py", "README.md"],
    )
    non_git = tmp_path / "ng"; non_git.mkdir()
    result = extract_rules.extract_candidates(tmp_path, cwd=non_git)
    r2s = [c for c in result["candidates"] if c["rule_id"] == "R2"]
    assert len(r2s) == 1, (
        f"R2 must fire on production-parser deny entries; got {r2s!r}"
    )
    assert r2s[0]["evidence"] == {
        "file": "src/auth.py", "deny_pattern": "src/auth.py"
    }
