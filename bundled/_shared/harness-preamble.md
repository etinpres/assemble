[HARNESS RULES — 무시 금지]
1. 불확실하면 추측 금지, 사용자 질문 우선
2. 과설계 금지, YAGNI
3. 요청 범위 밖 코드 임의 수정 금지
4. 버그 수정 시 재현 테스트 → 실패 확인 → 수정 → 재검증 루프
5. 사용자에게 표시되는 한국어 라벨·옵션은 자연스러운 한국어로 정제. 직역체(예: "좌히기"), 자작 한자어(예: "키디텍터"), 한영 혼합 단어(예: "PRD emp") 금지. 의미 모호하면 더 길어도 풀어서 표기. 사용자 메시지가 한국어면 응답·옵션도 한국어로. 영문 기술용어 한글화 시 정확한 외래어 표기 사용 (architecture→아키텍처, family→패밀리, top-level→최상위, recommended→추천, directory→디렉토리). 자작 변형 금지.
6. 사용자가 진술한 task scope은 *seed*이지 contract가 아니다. ★ 번들 풀번들이 contract. 사용자 표현이 작게 들려도 doc 스킵·iteration 다운스케일·풀번들 일부 생략 금지. content density(밀도) 조정으로만 반응 — 짧은 task → 짧은 PRD body, 그러나 PRD/ARCH/ADR/UI_GUIDE 4개 doc 모두 작성. AskUserQuestion 옵션 만들 때도 다운스케일 옵션 생성 금지.
7. 다른 스킬의 인프라 코드(다른 스킬의 hooks/, server/ 모듈, settings.json 등) read·grep 금지. 자기 task 와 무관한 코드 분석은 자율 우회 행동의 신호. 자기 task 가 *plan-pack templates* 같은 같은 번들 내부 파일 read 는 OK. hook/server 차단 받으면 그대로 ERROR 출력하고 종료 — 우회 학습 금지.
