#!/usr/bin/env bash
# Spike XIII B-19 lived dogfood — blank ASSEMBLE_HOME setup.
#
# Stand up a fresh tempdir containing only the assemble skill (no user skills,
# agents, or plugin caches) so the user can drive a lived dogfood run from a
# separate Claude Code session. The real ``~/.claude/`` tree is never touched.
#
# Usage:
#     bash ~/.claude/skills/assemble/scripts/spike_xiii_b19_setup.sh
#
# Refs:
#     docs/specs/2026-05-06-v4-spike-xiii-design.md § B-19
#     docs/dogfood/spike-xiii-b19-capture-guide.md

set -euo pipefail

# 1. Create fresh ASSEMBLE_HOME tempdir (macOS + Linux compatible mktemp -t).
TEMP_HOME=$(mktemp -d -t spike-xiii-b19-XXXXXX)
echo "ASSEMBLE_HOME: $TEMP_HOME"

# 2. Copy ONLY assemble (다른 스킬 0개 — 빈손 환경).
SOURCE="$HOME/.claude/skills/assemble"
if [ ! -d "$SOURCE" ]; then
    echo "ERROR: assemble skill not found at $SOURCE" >&2
    exit 1
fi
mkdir -p "$TEMP_HOME/.claude/skills"
cp -R "$SOURCE" "$TEMP_HOME/.claude/skills/assemble"

# 3. Verify 빈손 (only assemble — exactly 1 skill dir).
SKILL_COUNT=$(ls -1 "$TEMP_HOME/.claude/skills/" | wc -l | tr -d ' ')
if [ "$SKILL_COUNT" != "1" ]; then
    echo "ERROR: 빈손 환경 검증 실패 — $SKILL_COUNT skills present (expected 1)" >&2
    exit 1
fi

# Confirm the lone entry is assemble.
LONE=$(ls -1 "$TEMP_HOME/.claude/skills/")
if [ "$LONE" != "assemble" ]; then
    echo "ERROR: unexpected skill name '$LONE' (expected 'assemble')" >&2
    exit 1
fi

# 4. Print clear next-step instructions.
cat <<EOF

✅ Setup 완료 — 빈손 환경 ASSEMBLE_HOME=$TEMP_HOME

다음 단계 (별도 터미널에서):

  1. 별도 Claude Code 세션 진입:
       ASSEMBLE_HOME=$TEMP_HOME claude

  2. 캡쳐 가이드 확인:
       cat ~/.claude/skills/assemble/docs/dogfood/spike-xiii-b19-capture-guide.md

  3. 시작 명령 (예시):
       /assemble 작은 CLI 도구 만들고 싶어

  4. 가이드 따라 10 stages 진행하면서 4항목씩 캡쳐 (총 40)

종료 후 cleanup:
  rm -rf $TEMP_HOME

EOF
