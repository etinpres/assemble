"""Phase A guard — every {{...}} in PRD.md.template appears as a literal
.replace("{{...}}", ...) call in prd_step2.md or prd_step3.md, with no leftover
PRD_BODY-style sentinel that doesn't exist in the template."""

import re
from pathlib import Path

ASSEMBLE = Path.home() / ".claude/skills/assemble"
TEMPLATE = ASSEMBLE / "bundled/plan-pack/templates/PRD.md.template"
STEP2 = ASSEMBLE / "bundled/plan-pack/prompts/subagent/prd_step2.md"
STEP3 = ASSEMBLE / "bundled/plan-pack/prompts/subagent/prd_step3.md"

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
REPLACE_LITERAL_RE = re.compile(
    r'\.replace\(\s*["\'](\{\{[A-Z_]+\}\})["\']\s*,'
)


def _placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(text))


def _replace_literals(text: str) -> set[str]:
    return set(REPLACE_LITERAL_RE.findall(text))


def test_template_placeholders_all_replaced():
    template_phs = _placeholders(TEMPLATE.read_text())
    step2_replaces = _replace_literals(STEP2.read_text())
    step3_replaces = _replace_literals(STEP3.read_text())
    covered = step2_replaces | step3_replaces
    missing = template_phs - covered
    assert not missing, (
        f"PRD.md.template placeholders never replaced: {sorted(missing)}\n"
        f"step2 replaces: {sorted(step2_replaces)}\n"
        f"step3 replaces: {sorted(step3_replaces)}"
    )


def test_step2_does_not_reference_phantom_prd_body():
    """{{PRD_BODY}} was the broken pre-Spike-III sentinel — it must not return."""
    step2_text = STEP2.read_text()
    assert "{{PRD_BODY}}" not in step2_text, (
        "prd_step2.md still references {{PRD_BODY}} — pre-Spike-III bug."
    )


def test_step3_does_not_double_fence_ac_bash():
    """PRD.md.template wraps {{AC_BASH}} in ```bash ... ```. step3 must
    substitute a raw command, not another fenced block."""
    step3_text = STEP3.read_text()
    # Forbid f"```bash\n...\n```" wrap around ac_bash inside the save block.
    assert '"```bash\\n{ac_bash}\\n```"' not in step3_text.replace(" ", "")
    assert "ac_block = " not in step3_text, (
        "prd_step3.md still constructs an ac_block fenced wrap — "
        "PRD.md.template already provides the fence."
    )
