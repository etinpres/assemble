# SCOPE — Em-dash variant rejection test

## Allow list

- `server/scope_parser.py` – wrong en-dash separator
- `server/__init__.py` -- double-hyphen separator

## Completion criterion

```bash
pytest tests/unit/test_scope_parser.py -v
```
