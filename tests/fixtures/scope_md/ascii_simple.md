# SCOPE — Add deterministic SCOPE.md parser

## Allow list

- `server/scope_parser.py` — new file: deterministic parser
- server/__init__.py — additive export only

## Deny list

- `server/harness.py` — do not modify

## Completion criterion

```bash
pytest tests/unit/test_scope_parser.py -v
```
