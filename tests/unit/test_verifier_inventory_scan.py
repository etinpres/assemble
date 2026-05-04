"""Spike VIII A1 — verifier bundle scaffold: inventory + harness wiring tests."""
from pathlib import Path

from server.inventory import scan, parse_skill_frontmatter
from server.harness import ALLOWED_PROMPT_FILES, _BUNDLES, _BUNDLED_DIR_TO_STAGE

ASSEMBLE = Path.home() / ".claude/skills/assemble"
VERIFIER_SKILL = ASSEMBLE / "bundled/verifier/SKILL.md"


def _touch(p: Path, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _make_verifier_skill(home: Path):
    body = (
        '---\n'
        'name: "verifier"\n'
        'description: "Verify-stage ★ bundle. Executes parsed_scope.json completion bash'
        ' and emits deterministic exit-code verdict. Sub-agents own all reads/writes/Bash;'
        ' main Claude orchestrates only."\n'
        'stages: ["verify"]\n'
        '---\n\n'
        '# verifier ★ — completion criterion runner\n'
    )
    _touch(
        home / ".claude/skills/assemble/bundled/verifier/SKILL.md",
        body,
    )


def test_verifier_in_inventory_scan(tmp_path, monkeypatch):
    """scan() returns an entry with name='verifier', bundled=True, stages=["verify"]."""
    monkeypatch.setenv("ASSEMBLE_HOME", str(tmp_path))
    _make_verifier_skill(tmp_path)
    inv = scan(force=True)

    assert "verifier" in inv["skills"], "verifier not found in inventory scan"
    entry = inv["skills"]["verifier"]
    assert entry["bundled"] is True, "verifier should be marked bundled=True"
    # stages: ["verify"] in frontmatter → frontmatter-declared mappings
    stages_found = [m["stage"] for m in entry["mappings"]]
    assert "verify" in stages_found, (
        f"verifier mappings should contain stage='verify', got: {stages_found}"
    )


def test_verifier_allowlist_added():
    """All 4 verifier prompt filenames are present in ALLOWED_PROMPT_FILES."""
    assert "verifier_extract_step1.md" in ALLOWED_PROMPT_FILES
    assert "verifier_execute_step2.md" in ALLOWED_PROMPT_FILES
    assert "verifier_classify_step3.md" in ALLOWED_PROMPT_FILES
    assert "verifier_report_step4.md" in ALLOWED_PROMPT_FILES


def test_verifier_stage_route():
    """_BUNDLED_DIR_TO_STAGE maps 'verifier' → 'verify'."""
    assert _BUNDLED_DIR_TO_STAGE["verifier"] == "verify"


def test_existing_bundles_unchanged():
    """Regression guard: existing _BUNDLES entries + ALLOWED_PROMPT_FILES are intact."""
    # All 4 pre-verifier bundles still present
    for name in ("plan-pack", "debugger", "builder", "reviewer"):
        assert name in _BUNDLES, f"existing bundle '{name}' missing from _BUNDLES"
    # New verifier entry also present
    assert "verifier" in _BUNDLES, "'verifier' missing from _BUNDLES"

    # Spot-check existing ALLOWED_PROMPT_FILES entries (one from each bundle)
    assert "parse_scope_step1.md" in ALLOWED_PROMPT_FILES, \
        "reviewer parse_scope_step1.md missing — ALLOWED_PROMPT_FILES corrupted"
    assert "scope_step2.md" in ALLOWED_PROMPT_FILES, \
        "builder scope_step2.md missing — ALLOWED_PROMPT_FILES corrupted"
    assert "repro_step2.md" in ALLOWED_PROMPT_FILES, \
        "debugger repro_step2.md missing — ALLOWED_PROMPT_FILES corrupted"
    assert "prd_step2.md" in ALLOWED_PROMPT_FILES, \
        "plan-pack prd_step2.md missing — ALLOWED_PROMPT_FILES corrupted"
