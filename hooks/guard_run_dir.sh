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
#   warn            — exit 2 + stderr message (디버깅용 — production 차단 무력화 X)
#
# Spike II F13: `off` mode 제거. B-6 dogfood에서 sub-agent가
# `ASSEMBLE_GUARD=warn python3 << EOF` 로 ENV 명시 + magic marker 동시 사용
# (이중 우회) 시도. warn은 stderr만 추가될 뿐 차단은 유지.
#
# v0 limitation: does NOT distinguish main vs sub-agent. If sub-agent
# dispatch is observed to be blocked during dogfood, v1 must add
# transcript_path-based caller detection.

set -u

# ASSEMBLE_GUARD env var is documented in header; no runtime branching needed
# since Spike II F13 (warn==block, off removed).

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
    # v2 (Spike IV §1.3 C1): context-aware marker matcher delegated to
    # hooks/_guard_bash_matcher.py. The helper returns 0 iff the magic
    # marker appears inside a python3 body (canonical save block).
    if command -v jq >/dev/null 2>&1; then
      cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)"
    else
      cmd="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || echo "")"
    fi
    [[ -z "$cmd" ]] && exit 0  # 명령 파싱 불가 → 통과

    # Trigger: python3/python/sh -c/bash -c invocation
    #   AND (runs/<rid>/<f>.{md,json,txt} OR write_run_artifact OR runs_dir)
    if echo "$cmd" | grep -qE '(python3|python|sh -c|bash -c)' \
       && echo "$cmd" | grep -qE '(runs/[^/]+/(PRD|ARCHITECTURE|ADR|UI_GUIDE|BUG_REPORT)\.md|write_run_artifact|runs_dir)'; then
      # Passthrough: marker present in python3 body → canonical save
      hook_dir="$(dirname "$0")"
      if printf '%s' "$cmd" | python3 "$hook_dir/_guard_bash_matcher.py" >/dev/null 2>&1; then
        exit 0
      fi
      # Block
      bash_template='[V4 GUARD — Item B-prime] Bash → plan-pack artifact 직접 write 차단
메인 Claude의 python3/sh -c 우회로 plan-pack/debugger artifact 쓰기 시도 감지.
명령 일부: __CMD__
이유: Spike I 후 ★ bundle 본문은 sub-agent 가 자체 write 책임 — 메인은 dispatch + path 수령만.
복구: sub-agent dispatch 로 재시도하세요. (canonical save block 에 magic marker 포함됨)
참고: orchestrator 메타파일 (iteration_state.json, dispatches.jsonl) 은 main 직접 write 허용 (server 함수 사용 권장).
디버깅: ASSEMBLE_GUARD=warn 으로 stderr 추가 정보 확인 (차단은 유지). off 모드 없음.
v2 (Spike IV §1.3): magic marker 는 python3 -c 또는 heredoc body 안에서만 인정 — Bash 코멘트 prefix 우회 차단.'
      cmd_excerpt="$(printf '%s' "$cmd" | head -c 200)"
      bash_msg="${bash_template//__CMD__/$cmd_excerpt}"
      printf '%s\n' "$bash_msg" >&2
      # warn/block 모두 exit 2 (Spike II F13).
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
디버깅: ASSEMBLE_GUARD=warn 으로 stderr 추가 정보 확인 (차단은 유지). off 모드 없음.'
msg="${template//__TOOL__/$tool}"
msg="${msg//__FILE__/$file}"

printf '%s\n' "$msg" >&2

# warn/block 모두 exit 2 (Spike II F13).
exit 2
