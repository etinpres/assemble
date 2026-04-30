---
name: debugger
description: Debug stage ★ bundle — systematic hypothesis → reproducer → bisect → root cause → fix workflow with audit trail. (V4 Spike IV: parallel to plan-pack ★, sub-agent path-only return contract.)
---

[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
5. 사용자에게 표시되는 한국어 라벨·옵션은 자연스러운 한국어로 정제. 영문 기술용어 한글화 시 정확한 외래어 표기 사용.
6. task scope은 seed이지 contract가 아니다 — BUG_REPORT.md 5섹션 모두 작성
7. 다른 스킬 인프라 코드 read·grep 금지 — 자기 task 무관 분석은 우회 시도 신호

## CRITICAL — orchestrator-only enforcement

This skill is **orchestrator-only**. Main Claude (you) dispatches sub-agents
and parses their `WROTE: <path>` stdout. You MUST NOT fall back to
Bash/Edit/Write/python3 to write artifacts directly under `runs/<rid>/`.
The hook `guard_run_dir.sh` blocks such bypass attempts.

If a sub-agent dispatch fails (no `WROTE:` line, `ERROR:` line, timeout, or
empty stdout):
1. Surface the failure to the user via `AskUserQuestion`:
   "Step N failed. Retry / abort / report?"
2. Wait for user choice. Do not auto-recover.
3. NEVER attempt to write the artifact yourself, even "just to unblock the
   user". Sub-agent ownership is the contract.

# debugger — systematic hypothesis → fix workflow

(Steps + dispatch contract filled in Task C7. This skeleton exists so
inventory tests pass while Tasks C2-C6 add prompts and templates.)
