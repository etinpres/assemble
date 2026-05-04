# SCOPE — B-11 재현: 한국어 자유 형식 deny 항목

## Allow list

- `server/scope_parser.py` — new file

## Deny list

- `server/` 내 `run_dir.py` 외 모든 파일 (`__init__.py`, `harness.py`) — 변경 금지

## Completion criterion

```bash
pytest tests/unit/test_scope_parser.py -v
```
