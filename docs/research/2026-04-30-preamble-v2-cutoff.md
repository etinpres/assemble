# harness-preamble v1 → v2 cutoff (Spike I, 2026-04-30)

- v1 sha256: `858e9ff1cdc05ca73bb4009aab3acfc841169b30873d2fb00f2dfd546b86e159`
- v2 sha256: `df27450513c019a9dd395d8f62c99b445e7a16b4fcdbb5cba52c352397993549`
- v2 changes: rules 5 (한국어 quality) + 6 (anti-downscale) added — spec eeb6c96 §5.

Existing dogfood `runs/<rid>/dispatches.jsonl` files written before this cutoff use v1 sha256. `verify_dispatches()` accepts both via the ALLOW_LIST in `server/harness.py`.

Cutoff timestamp: 2026-04-30 (Spike I commit).
