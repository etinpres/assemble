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
    git_diff_name_only,
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
# git_diff_name_only — empty / one file / multi file / invalid range
# ---------------------------------------------------------------------------

def test_git_diff_name_only_empty_when_no_second_commit(repo):
    """Single-commit repo — `HEAD~..HEAD` is invalid (no parent). git's own
    error path should bubble through: ok=False, rc!=0, empty stdout. The
    helper does NOT raise — caller inspects the dict.
    """
    result = git_diff_name_only(repo, "HEAD~..HEAD")
    # git rev-parse rejects HEAD~ on root commit → non-zero rc, ok=False
    assert result["ok"] is False
    assert result["stdout"] == ""


def test_git_diff_name_only_one_file_changed(repo):
    """Two-commit repo with one file changed in the latest commit."""
    (repo / "README.md").write_text("v2\n")
    _git(["add", "README.md"], repo)
    _git(["commit", "-q", "-m", "second"], repo)
    result = git_diff_name_only(repo, "HEAD~..HEAD")
    assert result["ok"] is True
    assert result["rc"] == 0
    assert result["stdout"].strip() == "README.md"


def test_git_diff_name_only_multiple_files(repo):
    """Two-commit repo with multiple files changed."""
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    (repo / "nested" ).mkdir()
    (repo / "nested" / "c.txt").write_text("c\n")
    _git(["add", "."], repo)
    _git(["commit", "-q", "-m", "multi"], repo)
    result = git_diff_name_only(repo, "HEAD~..HEAD")
    assert result["ok"] is True
    assert result["rc"] == 0
    files = sorted(line for line in result["stdout"].splitlines() if line)
    assert files == ["a.txt", "b.txt", "nested/c.txt"]


def test_git_diff_name_only_rejects_invalid_range(repo):
    """range_spec with shell metacharacters is rejected before subprocess."""
    result = git_diff_name_only(repo, "HEAD; rm -rf /")
    assert result["ok"] is False
    assert result["rc"] == -1
    assert "invalid range_spec" in result["stderr"]


def test_git_diff_name_only_rejects_empty_range(repo):
    result = git_diff_name_only(repo, "")
    assert result["ok"] is False
    assert result["rc"] == -1


def test_git_diff_name_only_accepts_default(repo):
    """Default range_spec=`HEAD~..HEAD` is accepted by the validator
    (even when the repo has only one commit, the validator still passes —
    only git's actual diff fails).
    """
    # Add a second commit so the default invocation succeeds end-to-end.
    (repo / "x.txt").write_text("x\n")
    _git(["add", "x.txt"], repo)
    _git(["commit", "-q", "-m", "x"], repo)
    result = git_diff_name_only(repo)  # default arg
    assert result["ok"] is True
    assert "x.txt" in result["stdout"]


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


# Spike IX Codex retro F3 — extended fail-fast validation against full git
# check-ref-format forbidden character class.
@pytest.mark.parametrize("bad_char", ["~", "^", ":", "?", "*", "[", "\\"])
def test_git_create_tag_rejects_forbidden_chars(repo, bad_char):
    with pytest.raises(ValueError, match="forbidden character"):
        git_create_tag(repo, f"v1.0.0{bad_char}rc1", "msg")


def test_git_create_tag_rejects_control_character(repo):
    with pytest.raises(ValueError, match="control character"):
        git_create_tag(repo, "v1.0\x01.0", "msg")


def test_git_create_tag_rejects_lock_suffix(repo):
    with pytest.raises(ValueError, match=r"\.lock"):
        git_create_tag(repo, "v1.0.0.lock", "msg")


def test_git_create_tag_rejects_leading_slash(repo):
    with pytest.raises(ValueError, match="slash"):
        git_create_tag(repo, "/v1.0.0", "msg")


def test_git_create_tag_rejects_double_slash(repo):
    with pytest.raises(ValueError, match="slash"):
        git_create_tag(repo, "release//v1.0.0", "msg")


def test_git_create_tag_rejects_at_brace_refspec(repo):
    with pytest.raises(ValueError, match="refspec"):
        git_create_tag(repo, "v1.0.0@{0}", "msg")


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


# ---------------------------------------------------------------------------
# Spike IX cleanup F4 — Popen + killpg pattern audit (process-group SIGKILL)
# ---------------------------------------------------------------------------

def test_git_helpers_run_git_popen_pattern():
    """Source-level audit: `_run_git` uses Popen + start_new_session + killpg.

    Codex F4 carryforward: the previous `subprocess.run(timeout=...)` path
    left forked git children (gpg, fsmonitor) alive after timeout. Migrating
    to Popen with `start_new_session=True` plus `os.killpg(..., SIGKILL)`
    ensures the entire process group dies on timeout. This grep gate locks
    the pattern in source so a future refactor can't silently regress.
    """
    src_path = Path(__file__).resolve().parents[2] / "server" / "git_helpers.py"
    src = src_path.read_text(encoding="utf-8")
    # Must NOT use the timeout= keyword on subprocess.run (the old pattern).
    # subprocess.run is still allowed elsewhere, but _run_git itself must use Popen.
    assert "subprocess.Popen(" in src, (
        "_run_git must use subprocess.Popen for process-group control"
    )
    assert "start_new_session=True" in src, (
        "_run_git must spawn git in a fresh session (process group)"
    )
    assert "os.killpg" in src, (
        "_run_git must SIGKILL the entire process group on timeout"
    )
    assert "signal.SIGKILL" in src, (
        "_run_git must use SIGKILL (not SIGTERM) for hung git children"
    )
    # And the timeout still flows through .communicate(), not .run().
    assert "proc.communicate(timeout=" in src, (
        "_run_git must apply the timeout to communicate(), not run()"
    )
