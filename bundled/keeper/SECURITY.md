# keeper ★ — Security model

Bash surface: 2 of 4 sub-agent steps (Step 1 read-only git probes via `server.git_helpers`; Step 2 + Step 4 single canned `python3 <fixed-path>` invocations). Step 3 = Read/Write only.

Trust paradigm: SCOPE author + run_dir contents are trusted (matches verifier ★ + shipper ★ trust models). keeper does NOT redact PII or secrets — this is the SCOPE author's responsibility.

## Threats

- **T1 — Step 1 git probe shell escape.** *Mitigation*: argv-list invariant via `server.git_helpers` (`git_status_porcelain`, `git_head_sha`, `git_branch`, `git_diff_name_only`). NO `shell=True` anywhere.
- **T2 — Step 2 canned Python script substitution attack.** *Mitigation*: `extract_rules.py` is shipped in version control under `bundled/keeper/scripts/`. Sub-agent invokes by literal path; no user-controlled args (only `{{RUN_DIR}}` substituted, which is itself derived from `run_id` and validated by `server.run_dir.run_dir_path` — Spike VII A1 invariant).
- **T3 — Ledger jsonl injection (newline / control char in summary).** *Mitigation*: Step 3 sanitizes summary before write (newlines → space, ≤200 chars, single line). Each ledger row written as `json.dumps(entry, ensure_ascii=False)` + `\n`. No user-controlled `\n` injection possible.
- **T4 — Skiplist file traversal.** *Mitigation*: `learnings.skip` path is hardcoded at `~/.claude/channels/assemble/learnings.skip` (via `server.learnings.learnings_skip_path`). NO user parameterization.
- **T5 — Concurrent ledger corruption (multi-process race).** *NOT mitigated in V4*. Documented as known limitation. V5 candidate (`fcntl.flock` or atomic-rename + content-hash check). Single-run V4 guarantee makes this acceptable.
- **T6 — Stale-evidence false positive.** If user reverts a deny-list violation in a later run, the prior learning still recommends avoiding the path. *Mitigation*: 30-day TTL + user-managed `learnings.skip` denylist (manual escape valve).
- **T7 — PII / secret leak via evidence.** If SCOPE.md or git diff exposes credentials/tokens, evidence captures them. *NOT mitigated*. Documented under § Audit-evidence trust model. SCOPE author's responsibility (matches verifier ★ AC=bash trust model).

## Mitigations

- **M1 (T1)** — argv-list discipline: all git probes go through `server.git_helpers`. T8 inheritance from Spike IX.
- **M2 (T2)** — script invocation by literal path; no `${user_input}` interpolation.
- **M3 (T3)** — Step 3 pre-write sanitization (newline collapse + length cap).
- **M4 (T4)** — hardcoded skiplist path.
- **M5 (T6)** — TTL 30d + skiplist deny.
- **M6 (T1+T2)** — orchestrator-only enforcement (V4 #9): main never calls Bash; sub-agents own Bash steps; allowlist checked at `dispatch_prompt`.

## Audit-evidence trust model

keeper writes evidence verbatim — no redaction. Examples of evidence captured:

- Step 1: file paths from `git diff --name-only` (could include secrets in path components — unusual but possible)
- Step 2 R2: deny pattern + path overlap (paths verbatim)
- Step 2 R4: TODO/FIXME line excerpt up to 120 chars (could include secret-string-in-comment)

If your project has secrets in source paths or in TODO comments, do NOT enable keeper without first sanitizing. The ledger jsonl is local-only by design (no remote sync — see § Explicit non-goals), but it is unencrypted on disk under `~/.claude/channels/assemble/`.

## Explicit non-goals

1. **No remote ledger sync** — `learnings.jsonl` is per-machine. Cross-machine learning would require explicit user-driven sync (e.g. rsync, dotfiles-style git). NOT a V4 feature.
2. **No cross-machine portability** — evidence_hash is machine-stable but file paths in evidence may differ across users.
3. **No PII redaction** — see § Audit-evidence trust model.
4. **No false-positive feedback loop** — V4 ships static `learnings.skip`; user manually adds evidence_hashes to suppress. V5 candidate: keeper learns from skip patterns to avoid emitting in future.
5. **No concurrent run safety** — single-run V4 guarantee. V5 candidate.

## Known limitations

- **T5 multi-process race window** — between read_ledger and write_ledger of two concurrent keeper invocations, the second's write clobbers the first's appends. V4 mitigation: documentation only. Single-run guarantee.
- **T7 PII pass-through** — keeper evidence is unredacted by design. SCOPE author's responsibility.
- **Build-command sandboxing** — out of scope (this is shipper ★ territory, V5 candidate per Spike IX).
