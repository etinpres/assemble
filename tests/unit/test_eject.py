"""Unit tests for ``server.eject`` — V4 Spike XII Phase B.

Covers 17 cases from spec § Tests + 1 carryforward (M2 unreadable file).
All tests are tempdir-rooted; no mutation of real ``~/.claude/skills/`` ever.
"""

import hashlib
import os
import shutil
from pathlib import Path

import pytest

from server.eject import (
    EjectError,
    EjectPlan,
    apply_eject,
    assemble_root,
    available_bundles,
    dry_run_plan,
    resolve_dest,
    resolve_source,
    validate_dest_name,
)


# ---------------------------------------------------------------------------
# Shared fixture — never touches the real ~/.claude tree.
# ---------------------------------------------------------------------------


@pytest.fixture
def tempdir_assemble_home(tmp_path, monkeypatch):
    """Scaffold ``<tmp_path>/.claude/skills/assemble/bundled/{a,b,c}/`` with
    a SKILL.md + 1 template per bundle, plus an excluded ``_shared`` dir.

    Sets ``ASSEMBLE_HOME`` env var to ``tmp_path`` so all eject helpers
    resolve into the tempdir without explicit ``home=`` arg.
    """
    home = tmp_path
    bundled = home / ".claude/skills/assemble/bundled"
    for name in ("a", "b", "c"):
        d = bundled / name
        (d / "templates").mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f'---\nname: "{name}"\ndescription: "test"\n---\n'
        )
        (d / "templates" / "x.md.template").write_text("# X\n")
    (bundled / "_shared").mkdir()  # excluded by available_bundles
    (bundled / ".git").mkdir()  # excluded (hidden)
    monkeypatch.setenv("ASSEMBLE_HOME", str(home))
    return home


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1-3: assemble_root resolution
# ---------------------------------------------------------------------------


def test_assemble_root_default_home(monkeypatch):
    """``assemble_root()`` with no env var → ``~/.claude/skills/assemble``."""
    monkeypatch.delenv("ASSEMBLE_HOME", raising=False)
    expected = Path.home() / ".claude/skills/assemble"
    assert assemble_root() == expected


def test_assemble_root_with_explicit_home(monkeypatch):
    """Explicit ``home=`` argument wins over env var."""
    monkeypatch.setenv("ASSEMBLE_HOME", "/tmp/should-be-ignored")
    assert assemble_root(home=Path("/tmp/x")) == Path("/tmp/x/.claude/skills/assemble")


def test_assemble_root_respects_env_var(monkeypatch):
    """``ASSEMBLE_HOME`` env var is honored when no explicit ``home=``."""
    monkeypatch.setenv("ASSEMBLE_HOME", "/tmp/y")
    assert assemble_root() == Path("/tmp/y/.claude/skills/assemble")


# ---------------------------------------------------------------------------
# 4-5: available_bundles disk listing
# ---------------------------------------------------------------------------


def test_available_bundles_lists_disk_dirs(tempdir_assemble_home):
    """3 bundle dirs + ``_shared`` + ``.git`` → only ``[a, b, c]`` (sorted)."""
    assert available_bundles() == ["a", "b", "c"]


def test_available_bundles_returns_empty_when_no_bundled_dir(tmp_path, monkeypatch):
    """No ``bundled/`` subdir → ``[]`` (no exception)."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    # bundled/ does not exist under tmp_path
    assert available_bundles() == []


# ---------------------------------------------------------------------------
# 6-7: resolve_source
# ---------------------------------------------------------------------------


def test_resolve_source_known_bundle(tempdir_assemble_home):
    """Known bundle name → returns absolute Path that exists."""
    p = resolve_source("a")
    assert p.is_absolute()
    assert p.is_dir()
    assert p.name == "a"


def test_resolve_source_unknown_raises_with_available_list(tempdir_assemble_home):
    """Unknown bundle name → EjectError mentioning the unknown name and
    the available list (per impl: ``available=[...]`` substring)."""
    with pytest.raises(EjectError) as exc_info:
        resolve_source("nonexistent-bundle")
    msg = str(exc_info.value)
    assert "nonexistent-bundle" in msg
    assert "available=" in msg


# ---------------------------------------------------------------------------
# 8-11: validate_dest_name
# ---------------------------------------------------------------------------


def test_validate_dest_name_accepts_canonical():
    """Canonical lower+digit+dash+underscore → returned verbatim."""
    assert validate_dest_name("foo-bar_2") == "foo-bar_2"


def test_validate_dest_name_rejects_reserved_assemble():
    """``'assemble'`` is reserved → EjectError."""
    with pytest.raises(EjectError):
        validate_dest_name("assemble")


@pytest.mark.parametrize("bad_name", ["foo/bar", "..", "foo\\bar"])
def test_validate_dest_name_rejects_path_separator(bad_name):
    """Path separators / traversal sequences → EjectError."""
    with pytest.raises(EjectError):
        validate_dest_name(bad_name)


@pytest.mark.parametrize("bad_name", ["Foo", "foo bar", "1foo", ""])
def test_validate_dest_name_rejects_uppercase_or_invalid_chars(bad_name):
    """Uppercase, space, leading digit, empty → EjectError."""
    with pytest.raises(EjectError):
        validate_dest_name(bad_name)


# ---------------------------------------------------------------------------
# 12-13: dry_run_plan
# ---------------------------------------------------------------------------


def test_dry_run_plan_lists_files_and_size(tempdir_assemble_home):
    """Bundle with 3 files (SKILL.md + template + prompt) → ``files`` len 3,
    ``total_bytes > 0``, ``dest_exists=False``."""
    # Add a 3rd file (prompt) to bundle 'a'
    bundle_a = tempdir_assemble_home / ".claude/skills/assemble/bundled/a"
    (bundle_a / "prompts").mkdir()
    (bundle_a / "prompts" / "p1.md.prompt").write_text("# Prompt 1\n")

    plan = dry_run_plan("a", "my-skill")
    assert isinstance(plan, EjectPlan)
    assert len(plan.files) == 3
    assert plan.total_bytes > 0
    assert plan.dest_exists is False
    assert plan.bundle_name == "a"


def test_dry_run_plan_warns_on_dest_collision(tempdir_assemble_home):
    """Dest dir already exists with SKILL.md → ``dest_exists=True`` + warnings non-empty."""
    # Pre-create dest with a SKILL.md
    dest = tempdir_assemble_home / ".claude/skills/my-skill"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("# pre-existing\n")

    plan = dry_run_plan("a", "my-skill")
    assert plan.dest_exists is True
    assert len(plan.warnings) > 0


# ---------------------------------------------------------------------------
# 14-17: apply_eject
# ---------------------------------------------------------------------------


def test_apply_eject_creates_dest_skill_and_preserves_source(tempdir_assemble_home):
    """Apply on tempdir bundle → dest tree matches src (sha-equal); source unchanged."""
    src = tempdir_assemble_home / ".claude/skills/assemble/bundled/a"
    src_files_before = sorted(p for p in src.rglob("*") if p.is_file())
    src_shas_before = {p.relative_to(src): _sha256(p) for p in src_files_before}

    plan = dry_run_plan("a", "ejected-a")
    apply_eject(plan)

    dest = tempdir_assemble_home / ".claude/skills/ejected-a"
    assert dest.is_dir()
    assert (dest / "SKILL.md").is_file()

    # Dest tree sha-matches src tree
    dest_shas = {
        p.relative_to(dest): _sha256(p)
        for p in dest.rglob("*") if p.is_file()
    }
    assert dest_shas == src_shas_before

    # Source unmodified
    src_shas_after = {
        p.relative_to(src): _sha256(p)
        for p in src.rglob("*") if p.is_file()
    }
    assert src_shas_after == src_shas_before


def test_apply_eject_overwrite_creates_backup(tempdir_assemble_home):
    """Dest exists + overwrite=True → backup ``<dest>.bak.<ts>`` exists,
    dest replaced cleanly."""
    # Pre-create a dest with different content
    dest = tempdir_assemble_home / ".claude/skills/ejected-a"
    dest.mkdir(parents=True)
    sentinel = dest / "OLD_FILE.md"
    sentinel.write_text("# pre-existing content\n")

    plan = dry_run_plan("a", "ejected-a")
    apply_eject(plan, overwrite=True)

    # Backup directory must exist somewhere alongside dest
    parent = dest.parent
    backups = list(parent.glob("ejected-a.bak.*"))
    assert len(backups) >= 1, f"no backup found in {parent}"
    # Old sentinel should be in the backup, not the new dest
    assert (backups[0] / "OLD_FILE.md").is_file()
    # Backup must preserve the EXACT pre-overwrite content (not stale/empty).
    assert (backups[0] / "OLD_FILE.md").read_text() == "# pre-existing content\n"
    assert not (dest / "OLD_FILE.md").exists()
    # New dest should have SKILL.md from bundle
    assert (dest / "SKILL.md").is_file()


def test_apply_eject_atomic_failure_no_partial_state(tempdir_assemble_home, monkeypatch):
    """Monkeypatched ``shutil.copytree`` raises mid-tree → dest does NOT
    exist after exception (no half-copied state).

    NOTE: server/eject.py imports ``shutil`` at module level, so we patch
    ``server.eject.shutil.copytree``.
    """
    def boom(*args, **kwargs):
        raise RuntimeError("simulated copytree failure")

    monkeypatch.setattr("server.eject.shutil.copytree", boom)

    plan = dry_run_plan("a", "doomed-eject")
    with pytest.raises(RuntimeError, match="simulated copytree failure"):
        apply_eject(plan)

    dest = tempdir_assemble_home / ".claude/skills/doomed-eject"
    assert not dest.exists(), "dest left in partial state after failure"
    # Also confirm no leaked temp dir
    parent = dest.parent
    if parent.exists():
        leftovers = [p for p in parent.iterdir() if p.name.startswith("doomed-eject.tmp.")]
        assert leftovers == [], f"leaked temp dir: {leftovers}"


def test_apply_eject_atomic_failure_with_overwrite_preserves_dest(
    tempdir_assemble_home, monkeypatch
):
    """copytree failure with ``overwrite=True`` must preserve dest, emit no
    backup, and clean up any temp leftovers.

    Per the 7-step atomicity contract, ``copytree`` (step 2) runs BEFORE
    the backup rename (step 4). So when copytree raises, the original dest
    must remain untouched and no backup directory should appear.
    """
    dest_parent = tempdir_assemble_home / ".claude/skills"
    dest = dest_parent / "ejected-a"

    # Pre-create dest with sentinel content
    dest.mkdir(parents=True)
    (dest / "OLD_FILE.md").write_text("# original content\n")

    plan = dry_run_plan("a", "ejected-a")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated copy failure")

    monkeypatch.setattr("server.eject.shutil.copytree", boom)

    with pytest.raises(RuntimeError, match="simulated copy failure"):
        apply_eject(plan, overwrite=True)

    # Dest preserved (original content intact)
    assert (dest / "OLD_FILE.md").read_text() == "# original content\n"
    # No backup was created (copytree failed BEFORE step 4)
    backups = list(dest_parent.glob("ejected-a.bak.*"))
    assert backups == [], f"unexpected backup: {backups}"
    # No temp leftovers
    temps = list(dest_parent.glob("ejected-a.tmp.*"))
    assert temps == [], f"unexpected temp dir: {temps}"


def test_apply_eject_inventory_integration(tempdir_assemble_home):
    """Apply via ``ASSEMBLE_HOME=<tempdir>``; ``inventory.enumerate_skill_paths(home=tempdir)``
    must include the ejected SKILL.md."""
    from server.inventory import enumerate_skill_paths

    plan = dry_run_plan("a", "inv-skill")
    apply_eject(plan)

    paths = enumerate_skill_paths(home=tempdir_assemble_home)
    expected = (tempdir_assemble_home / ".claude/skills/inv-skill/SKILL.md").resolve()
    assert expected in paths


# ---------------------------------------------------------------------------
# 18: M2 carryforward — race-condition simulation for OSError swallow branch
# ---------------------------------------------------------------------------


def test_dry_run_plan_swallows_stat_oserror_in_race_condition(
    tempdir_assemble_home, monkeypatch
):
    """The ``except OSError: pass`` branch in ``dry_run_plan`` swallows
    stat() failures *between* the ``is_file()`` check and the
    ``p.stat().st_size`` accumulator — i.e., a genuine race condition
    where the file's permission/existence changes mid-walk.

    Why monkeypatch instead of chmod:

    * ``pathlib.Path.is_file()`` calls ``self.stat()`` internally and
      propagates ``PermissionError`` (EACCES) — pathlib's _IGNORED_ERROS
      set is ``{ENOENT, ENOTDIR, EBADF, ELOOP}``. EACCES is NOT in that
      set on Python 3.10/3.11/3.12. Verified:
      ``pathlib._IGNORED_ERROS == (2, 20, 9, 62)`` — no EACCES (13).
    * Therefore ``chmod 0o400`` on a parent directory makes ``is_file()``
      raise PermissionError BEFORE ``p.stat().st_size`` is reached, and
      the swallow branch is unreachable via that attack. (Confirmed
      empirically on macOS APFS Python 3.10.)
    * The swallow branch IS still defensive code for genuine races
      (e.g., file unlinked or permission flipped between ``is_file()``'s
      stat and the accumulator's stat). To exercise it
      deterministically, we monkeypatch ``Path.stat`` so that the FIRST
      call on a target file (driven by ``is_file()``) succeeds but the
      SECOND call (driven by ``p.stat().st_size`` inside the try block)
      raises ``PermissionError``.

    This pins the swallow branch's behavior: file appears in
    ``plan.files`` but its bytes are excluded from ``total_bytes``.
    """
    bundle_a = tempdir_assemble_home / ".claude/skills/assemble/bundled/a"
    target_file = bundle_a / "race.bin"
    target_file.write_bytes(b"Y" * 2048)  # 2KB known size

    # Baseline: total_bytes WITH the target stat-able both calls
    plan_before = dry_run_plan("a", "race-skill-baseline")
    bytes_with_readable = plan_before.total_bytes
    assert target_file in plan_before.files
    assert bytes_with_readable >= 2048

    # Patch Path.stat so the SECOND call on target_file raises.
    # First call (driven by is_file) succeeds → file enters plan.files.
    # Second call (driven by p.stat().st_size) raises → swallow branch fires.
    from pathlib import Path

    original_stat = Path.stat
    target_key = str(target_file)
    call_counts: dict[str, int] = {}

    def stat_with_race(self, *args, **kwargs):
        # Plain str(self) — using self.exists() / self.resolve() would call
        # stat() recursively and blow the stack.
        key = str(self)
        if key == target_key:
            call_counts[key] = call_counts.get(key, 0) + 1
            if call_counts[key] >= 2:
                raise PermissionError(
                    "simulated race: target became unreadable between is_file() and stat()"
                )
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_with_race)

    plan = dry_run_plan("a", "race-skill")

    # File listed (is_file's stat call passed) but bytes excluded (swallow fired)
    assert target_file in plan.files
    assert plan.total_bytes == bytes_with_readable - 2048
    # Sanity: the second-call-and-beyond stat on target_file actually fired
    assert call_counts.get(target_key, 0) >= 2
