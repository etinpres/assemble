# Preamble v2 → v3 cutoff (2026-05-01)

## Why v3

Spike II spec §3.1 F12 + §3.2 F3:
- B-6 dogfood (run `20260430-120552-6aad`) showed sub-agents reading
  unrelated infrastructure code (hooks/, server/ modules) to learn how
  to bypass guards.
- Rule 5 한국어 quality 위반 7건 — 외래어 표기 (architecture/family/
  top-level/recommended) 자작 변형.

## v3 changes

- Rule 5 본문에 외래어 표기 사례 박음.
- Rule 7 신설: 다른 스킬 인프라 코드 read 금지.

## sha256 cutoff

| version | sha256 | first run |
|---|---|---|
| v1 | `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159` | (pre-Spike I) |
| v2 | `df27450513c019a9dd395d8f62c99b445e7a16b4fcdbb5cba52c352397993549` | Spike I (master `cccd58a`) |
| v3 | `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` | Spike II (this commit) |

`server.harness.verify_dispatches` ALLOW_LIST 는 Task 6 에서 v3 추가.
v1 + v2 + v3 모두 인정 — 과거 dogfood 데이터 backward compatible.

## Files

- `bundled/_shared/harness-preamble.md` — 7 rules
- `server/harness.py` — `_PREAMBLE_V1_SHA256` 옆에 `_PREAMBLE_V2_SHA256` 추가 (Task 6)
- `tests/unit/test_harness_dispatches.py` — sha256 hard-coded 테스트 갱신 (Task 6)
