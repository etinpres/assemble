"""Unit tests for `server.git_helpers` (V4 Spike IX, Task A3).

Tests use real `git init` repos in `tempfile.TemporaryDirectory` rather than
mocking subprocess. The cost is ~10ms per test; the gain is that we exercise
the actual argv-list invocation path (T8 mitigation surface) instead of a
mock that could mask shell-injection regressions.

Argv-list grep gate (`test_module_has_no_shell_true_or_os_system`) is the
load-bearing security assertion — it reads `server/git_helpers.py` and fails
if `shell=True` or `os.system(` ever appear in the source.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from server.git_helpers import (
    git_branch,
    git_create_tag,
    git_head_sha,
    git_status_porcelain,
    git_tag_exists,
    git_tag_sha,
)


# ---------------------------------------------------------------------------
# Test fixtures — real git repos via tempfile + subprocess
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: Path) -> None:
    """Run a git command directly (test-side helper). NOT the SUT."""
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(cwd: Path) -> None:
    """Initialize a fresh git repo with one commit and a known branch."""
    _git(["init", "-q", "-b", "main"], cwd)
    _git(["config", "user.email", "test@example.com"], cwd)
    _git(["config", "user.name", "Test"], cwd)
    _git(["config", "commit.gpgsign", "false"], cwd)
    _git(["config", "tag.gpgsign", "false"], cwd)
    (cwd / "README.md").write_text("hello\n")
    _git(["add", "README.md"], cwd)
    _git(["commit", "-q", "-m", "initial"], cwd)


@pytest.fixture
def repo():
    """Yield a Path to a freshly initialized git repo with one commit."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        _init_repo(p)
        yield p


# ---------------------------------------------------------------------------
# git_status_porcelain — clean / dirty
# ---------------------------------------------------------------------------

def test_git_status_porcelain_clean_tree(repo):
    result = git_status_porcelain(repo)
    assert result["ok"] is True
    assert result["rc"] == 0
    assert result["stdout"] == ""  # clean = empty porcelain output


def test_git_status_porcelain_dirty_tree(repo):
    (repo / "README.md").write_text("modified\n")
    result = git_status_porcelain(repo)
    assert result["ok"] is True
    assert result["rc"] == 0
    # porcelain marks modified tracked file with " M <path>"
    assert "README.md" in result["stdout"]
    assert result["stdout"].strip().startswith("M") or \
        result["stdout"].strip().startswith("M") or \
        " M " in result["stdout"]


# ---------------------------------------------------------------------------
# git_head_sha
# ---------------------------------------------------------------------------

def test_git_head_sha_returns_sha(repo):
    result = git_head_sha(repo)
    assert result["ok"] is True
    assert result["rc"] == 0
    sha = result["stdout"].strip()
    # 40-char hex SHA-1 (or 64-char SHA-256 if repo configured so; default = 40)
    assert len(sha) in (40, 64)
    assert all(c in "0123456789abcdef" for c in sha)


# ---------------------------------------------------------------------------
# git_branch
# ---------------------------------------------------------------------------

def test_git_branch_returns_branch_name(repo):
    result = git_branch(repo)
    assert result["ok"] is True
    assert result["rc"] == 0
    assert result["stdout"].strip() == "main"


# ---------------------------------------------------------------------------
# git_tag_exists
# ---------------------------------------------------------------------------

def test_git_tag_exists_absent(repo):
    assert git_tag_exists(repo, "v1.0.0") is False


def test_git_tag_exists_present(repo):
    _git(["tag", "-a", "v1.0.0", "-m", "msg"], repo)
    assert git_tag_exists(repo, "v1.0.0") is True
    # And a different name returns False (no false-positive on prefix match).
    assert git_tag_exists(repo, "v1") is False


# ---------------------------------------------------------------------------
# git_create_tag — happy path
# ---------------------------------------------------------------------------

def test_git_create_tag_success(repo):
    result = git_create_tag(repo, "v0.1.0", "release v0.1.0")
    assert result["ok"] is True
    assert result["rc"] == 0
    # Confirm via git tag -l
    listing = subprocess.run(
        ["git", "tag", "-l", "v0.1.0"],
        cwd=str(repo), capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert listing == "v0.1.0"


# ---------------------------------------------------------------------------
# git_create_tag — validation rejects unsafe names BEFORE subprocess
# ---------------------------------------------------------------------------

def test_git_create_tag_rejects_empty_name(repo):
    with pytest.raises(ValueError):
        git_create_tag(repo, "", "msg")


def test_git_create_tag_rejects_whitespace_name(repo):
    with pytest.raises(ValueError):
        git_create_tag(repo, "v 1.0.0", "msg")


def test_git_create_tag_rejects_leading_dash(repo):
    with pytest.raises(ValueError):
        git_create_tag(repo, "-v1.0.0", "msg")


def test_git_create_tag_rejects_double_dot(repo):
    with pytest.raises(ValueError):
        git_create_tag(repo, "v1..0", "msg")


# ---------------------------------------------------------------------------
# git_tag_sha
# ---------------------------------------------------------------------------

def test_git_tag_sha_after_creation(repo):
    git_create_tag(repo, "v0.2.0", "release v0.2.0")
    result = git_tag_sha(repo, "v0.2.0")
    assert result["ok"] is True
    assert result["rc"] == 0
    sha = result["stdout"].strip()
    assert len(sha) in (40, 64)
    assert all(c in "0123456789abcdef" for c in sha)


# ---------------------------------------------------------------------------
# Argv-list audit — the load-bearing security gate
# ---------------------------------------------------------------------------

def test_module_has_no_shell_true_or_os_system():
    """Source-level audit: `shell=True` and `os.system(` MUST NOT appear in
    `server/git_helpers.py`. This is the canonical T8 mitigation grep gate.
    """
    src_path = Path(__file__).resolve().parents[2] / "server" / "git_helpers.py"
    src = src_path.read_text(encoding="utf-8")
    assert "shell=True" not in src, \
        "git_helpers.py must use argv-list invocation only (no shell=True)"
    assert "os.system(" not in src, \
        "git_helpers.py must not use os.system()"
