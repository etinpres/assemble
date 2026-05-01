"""Spike V Phase A — M1/M2/M3 debugger prompt polish guards."""
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
REPRO = ASSEMBLE / "bundled/debugger/prompts/subagent/repro_step2.md"
FIX5 = ASSEMBLE / "bundled/debugger/prompts/subagent/fix_step5.md"


def test_m1_dart_heredoc_anti_pattern():
    """A1: ## Anti-patterns section warns about non-bash heredoc (Dart etc.)."""
    text = REPRO.read_text()
    idx = text.find("## Anti-patterns")
    assert idx != -1, "## Anti-patterns section missing from repro_step2.md"
    section = text[idx:]
    assert "dart run" in section or "dart - <<EOF" in section, (
        "No Dart heredoc warning in ## Anti-patterns — add 'dart run <file>' guidance"
    )


def test_m2_behavioral_verifier_cue():
    """A2: fix_step5 ## Constraints section prefers behavioral verifiers."""
    text = FIX5.read_text()
    assert "behavioral" in text, (
        "fix_step5.md missing behavioral verifier preference cue in constraints"
    )


def test_m3_symptom_sentinel_substitution():
    """A3: repro_step2 save block has explicit ## Symptom sentinel substitution."""
    text = REPRO.read_text()
    assert '.replace("## Symptom' in text, (
        'repro_step2.md save block missing explicit .replace("## Symptom...") call'
    )
