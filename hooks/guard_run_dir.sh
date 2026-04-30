#!/usr/bin/env bash
# guard_run_dir.sh — /assemble V4 plan-pack distribution guard (Item B').
#
# Blocks Edit/Write/NotebookEdit on paths under
#   ~/.claude/channels/assemble/runs/<run_id>/
# when invoked directly. Enforces V4 decisions:
#   #9  orchestrator-only (main Claude does only IO/AskUserQuestion)
#   #12 dogfood fail criterion (main writes artifact body = fail)
#
# Triggered by V4 spec violation observed 2026-04-29 dogfood: main
# scope-reduced "todo PRD" task to inline body write, skipping ARCH/ADR/
# UI_GUIDE entirely. SKILL.md text rules cannot prevent this — system
# enforcement is the only remedy.
#
# Modes (env var ASSEMBLE_GUARD):
#   block (default) — exit 2 + stderr message → tool call blocked
#   warn            — stderr only, tool call proceeds (observation mode)
#   off             — disabled
#
# v0 limitation: does NOT distinguish main vs sub-agent. If sub-agent
# dispatch is observed to be blocked during dogfood, v1 must add
# transcript_path-based caller detection.

set -u

mode="${ASSEMBLE_GUARD:-block}"
[[ "$mode" == "off" ]] && exit 0

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  tool="$(printf '%s' "$input" | jq -r '.tool_name // ""')"
  file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')"
else
  tool="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null || echo "")"
  file="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || echo "")"
fi

case "$tool" in
  Edit|Write|NotebookEdit) ;;
  Bash)
    # v1: 메인의 Bash + python3/sh -c 우회 차단 (Spike I §6)
    if command -v jq >/dev/null 2>&1; then
      cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)"
    else
      cmd="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || echo "")"
    fi
    [[ -z "$cmd" ]] && exit 0  # 명령 파싱 불가 → 통과

    # Trigger: python3/python/sh -c/bash -c invocation
    #   AND (runs/<rid>/<f>.{md,json,txt} OR write_run_artifact OR runs_dir)
    if echo "$cmd" | grep -qE '(python3|python|sh -c|bash -c)' \
       && echo "$cmd" | grep -qE '(runs/[^/]+/[^/]+\.(md|json|txt)|write_run_artifact|runs_dir)'; then
      # Passthrough: magic marker 존재 시 sub-agent canonical save로 인정
      if echo "$cmd" | grep -q 'ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE'; then
        exit 0
      fi
      # Block
      bash_template='[V4 GUARD — Item B-prime] Bash → runs/ 직접 write 차단
메인 Claude의 python3/sh -c 우회로 plan-pack 산출물 쓰기 시도 감지.
명령 일부: __CMD__
이유: Spike I 후 plan-pack은 sub-agent 가 자체 write 책임 — 메인은 dispatch + path 수령만.
복구: sub-agent dispatch 로 재시도하세요. (canonical save block 에 magic marker 포함됨)
일시 우회: ASSEMBLE_GUARD=warn (경고만) 또는 ASSEMBLE_GUARD=off (비활성)'
      cmd_excerpt="$(printf '%s' "$cmd" | head -c 200)"
      bash_msg="${bash_template//__CMD__/$cmd_excerpt}"
      printf '%s\n' "$bash_msg" >&2
      if [[ "$mode" == "warn" ]]; then
        exit 0
      fi
      exit 2
    fi
    exit 0
    ;;
  *) exit 0 ;;
esac

[[ -z "$file" ]] && exit 0

runs_root="$HOME/.claude/channels/assemble/runs"
case "$file" in
  "$runs_root"/*) ;;
  *) exit 0 ;;
esac

template='[V4 GUARD — Item B-prime] __TOOL__ → __FILE__
plan-pack 산출물에 직접 쓰기 시도 감지. V4 결정 #9·#12 위반.
정상 경로:
  1) server.harness.wrap_with_preamble(prompt) 로 4원칙 prepend
  2) general-purpose / Plan / Explore 등 sub-agent dispatch
  3) sub-agent 가 write_run_artifact 로 기록
일시 우회: ASSEMBLE_GUARD=warn (경고만) 또는 ASSEMBLE_GUARD=off (비활성)'
msg="${template//__TOOL__/$tool}"
msg="${msg//__FILE__/$file}"

printf '%s\n' "$msg" >&2

if [[ "$mode" == "warn" ]]; then
  exit 0
fi

exit 2
