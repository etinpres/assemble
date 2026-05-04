# SCOPE — Mixed valid and freeform Korean deny entries

## Allow list

- `server/scope_parser.py` — new file: deterministic parser
- server/__init__.py — additive export only

## Deny list

- `server/harness.py` — do not modify
- `server/` 내 `run_dir.py` 외 모든 파일 (`__init__.py`) — 변경 금지 (freeform, should error)
- `server/inventory.py` — do not touch
- `server/` 안의 `classify.py` 및 다른 파일들 (`menu.py`, `i18n.py`) — 전체 변경 금지 (freeform, should error)

## Completion criterion

```bash
pytest tests/unit/test_scope_parser.py -v
```
