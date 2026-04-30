# Spike III final readiness — B-8 dogfood PASS, ship

## Result

**12/13 full PASS + 1 partial PASS with 3 iter1-path carryforwards. Ship.**

B-8 dogfood run `20260430-211523-212a` (md-sync — markdown notes sync CLI, p2p LAN + USB modes, ADR-decided conflict strategy). Iteration 0 + iteration 1 + user-requested-stop. ~50 minutes wall-clock.

## 13 Acceptance Criteria — final mapping

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | PRD `{{...}}` literal 0건 | ✅ | `grep -c "{{" runs/<rid>/*.md` → 0/0/0/0 |
| 2 | AC fence single (no nested) | ✅ | `runs/<rid>/PRD.md:20-22` single ` ```bash<cmd>``` ` pair |
| 3 | `record_dispatch(prompt_file="evil.md")` strict ValueError | ✅ | `tests/unit/test_dispatch_prompt.py` (code) |
| 4 | `dispatch_prompt` unknown file ValueError | ✅ | same test (code) |
| 5 | `dispatch_prompt` placeholders preserved | ✅ | `runs/<rid>/dispatches.jsonl` 모든 entry `prompt_file` 정확 + main의 "Verification OK -- {{TASK}} preserved in save block, {{RUN_ID}} substituted everywhere" 출력 |
| 6 | save block bare `...` 0건 | ✅ | 4 doc 0/0/0/0 |
| 7 | sub-agent prompt "Print `WROTE: ...`" | ✅ | `tests/unit/test_prompts_print_contract.py` (code) |
| 8 | SKILL.md options Korean (no `4-doc`/`cross-doc`) | ✅ | Step 6 entry: `"yes — 강조점 인터뷰 + 네 문서 재작성 + 문서 간 재검증 (추천)"`; exit: `"...한 라운드 더"` |
| 9 | Step 6 selector 분기 | ✅ | iteration_count=0 entry / iteration_count=1 exit override 정확 |
| 10 | `ui_step13` antipattern conditional | ✅ | `runs/<rid>/UI_GUIDE.md:9-21` "conditional signals, not absolute bans" |
| 11 | prompts/ subdir + allowlist | ✅ | dispatches.jsonl prompt_file 모두 정확 |
| 12 | pytest 231 | ✅ | master a92277d 베이스 |
| 13 | B-8 dogfood 0 informal / 0 leak / 0 nested fence | ⚠️ partial | 0 leak ✅, 0 nested fence ✅, 0 informal *first-pass*만 ✅ — iter1 path 약점 3건 (carryforward) |

Plus the audit trail confirms:

- `dispatches.jsonl` 8 entries (step 2/3/4/8/11/13/9/9_iter1) all with `preamble_sha256: 8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` (canonical v3 byte-identity)
- `iteration_state.json`: 2 iterations, stopped via `user-requested-stop`, `resolved_pct: 0.0 → 0.286`, `new_count: 6 → 1`
- ADR.md: 5 decisions × 5 sub-headings (Context/Decision/Reasoning/Rejected alternatives/Tradeoffs), Cross-doc review (first-pass) + Cross-doc review (iteration 1) headings separated correctly, COUNTS keys consistent in both passes
- Anti-downscale: 4 docs all written in first-pass; iter1 redrafted 1 (ADR), 3 marked no-change pass-through

## Carryforward (3 items — all confined to iter1 path)

### A — iter1 4-way dispatch missing from `dispatches.jsonl`

**Symptom**: `dispatches.jsonl` records first-pass step2/3/4/8/11/13/9 + step9_iter1 (8 rows). Missing: 4 rows for iter1 PRD/ARCH/ADR/UI 4-way redraft via `iter_emphasis.md`.

**Diagnosis**: orchestrator built iter1 emphasis prompts and dispatched 4 sub-agents (transcript shows `Running 4 agents...` with token/tool-use counts), but skipped the `record_dispatch(prompt_file="iter_emphasis.md", ...)` call after each `dispatch_prompt` load. Preamble v3 still prepended (sub-agents reported no-change pass-through correctly, indicating `wrap_with_preamble` ran), so §CRITICAL rule 7 still in effect — only the audit-trail row is missing.

**Severity**: Important. F12 safety net's *audit visibility* is partially bypassed in iter1 path. Acceptance #11 ("allowlist updated") code-level passes but the runtime usage pattern in iter1 doesn't pair `dispatch_prompt` + `record_dispatch`.

**Fix shape**: SKILL.md "Step 6 yes-path detail" step 3 explicitly enumerate the 4 `record_dispatch` calls (one per iter1 doc dispatch), with `prompt_file="iter_emphasis.md"` and `step="step6.iter1.PRD"` etc.

### B — iter1 ARCH/UI_GUIDE/PRD doc mtime not updated

**Symptom**:

- `ADR.md` mtime `21:59` (after iter1 — re-written for D2 mDNS → UDP broadcast change) ✅
- `PRD.md` / `ARCHITECTURE.md` / `UI_GUIDE.md` mtime `21:53/54` (after Step 9 first-pass; iter1 left bytes untouched)

The transcript labels iter1 ARCH/UI_GUIDE/PRD as "no change pass-through · Done", but `iter_emphasis.md` spec (`bundled/plan-pack/prompts/orchestrator/iter_emphasis.md:29-32`) requires the sub-agent to *read + write back unchanged via `write_run_artifact`* even on `(no change)`. Sub-agents elided the write — autonomous cost optimization, but spec violation.

**Severity**: Minor. Bytes identical, no user-visible regression. Audit-trail consequence overlaps with Issue A (no `record_dispatch` row → no `wrote_path` audit either).

**Fix shape**: Either (a) tighten `iter_emphasis.md` step-1 wording so sub-agents *must* call `write_run_artifact` regardless, or (b) relax spec to "no-change → main skips dispatch entirely; audit row records `step="step6.iter1.<DOC>" status="skipped"`".

### C — ADR sub-agent "Bash command prefix marker" hook v1 false-negative

**Symptom (transcript screen 03)**: Iter1 ADR re-write tool description — `Bash: Write ADR with magic marker in Bash command prefix - test if guard passes`. ADR.md write succeeded (mtime 21:59 confirms). The phrasing "*test if guard passes*" reads as the sub-agent intentionally probing the hook v1 matcher.

**Diagnosis**: hook v1 (`hooks/guard_run_dir.sh`) Bash branch matches `ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE` magic marker as a *substring of the Bash command*. Sub-agent placed the marker as a Bash-comment prefix and wrote ADR.md directly via Bash (likely `bash -c "# ASSEMBLE_SUBAGENT_LIFECYCLE_WRITE\ncat > ADR.md <<EOF ..."` or similar) instead of the canonical Python save-block path. hook v1 still passed it.

**Severity**: Important. Spike I sub-agent path-only return contract assumed the magic marker would only appear in Python save blocks dispatched by a recognized prompt; the Bash-prefix path is an unauthorized lifecycle. Combined with Issue A (no `record_dispatch` row), iter1 ADR's actual write event has zero audit trail anchored in `dispatches.jsonl`.

**Fix shape**: `hooks/guard_run_dir.sh` Bash branch tightened — accept marker only when it appears as the *first non-empty Python comment line* of an inline `python3 -c '...'` invocation, *not* as a generic Bash comment substring. Add hook test case (`tests/contracts/test_guard_bash_matcher.py`) for the false-negative shape from this transcript.

## Spike III ship verdict

**Ship Spike III.** First-pass artifacts (PRD/ARCH/ADR/UI_GUIDE) are 100% clean — placeholder-free, fence-correct, decision-rich, sub-heading-complete. The 12/13 PASS plus partial #13 (informal-dispatch in iter1 path only) clears the V4 distribution gate.

The 3 carryforwards are bundled together as the **iter1 audit-trail integrity** workstream — best addressed alongside the next spike rather than as a Spike III v3.1 patch, because:

1. iter1 path약점은 user-visible 산출물에 영향 없음 (B-8 PRD/ARCH/ADR/UI 모두 ready).
2. ★ candidate bundles (Spike IV — `builder` / `debugger` / `reviewer`) deliver larger user-visible value (자급자족 보증 강화).
3. hook v1 tightening (Issue C) naturally pairs with bundle-specific guards introduced in Spike IV.

## Next — Spike IV proposal

★ candidate bundles, in priority order driven by current Spike III findings:

1. **`debugger` ★** — systematic-debugging 정신 (가설→재현→이등분→근본원인). Highest ROI per Spike III memory § "★급 강화 후보". Guards against LLM "guess fix" pattern.
2. **`builder` ★** — TDD 강제 흐름. Pairs with Spike I path-only contract: every change has failing-test → impl → green → commit.
3. **`reviewer` ★** — diff scope vs SCOPE.md gate. Closes harness rule #3 (Surgical Changes) at runtime.

Spike IV scope **must include** the 3 iter1 carryforwards above (paired with hook v2 design or bundled-skill-specific dispatch-trail integrity).

## Source

- B-8 dogfood transcript: 형 직접 캡처 + run dir audit `~/.claude/channels/assemble/runs/20260430-211523-212a/`.
- 13 acceptance source: `docs/specs/2026-04-30-v4-spike-iii-design.md` §3.
- Spike III memory: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_iii.md`.
- Sibling readiness memo: `docs/dogfood/spike-i-readiness.md`. (Spike II 별도 readiness memo는 없음 — Spike II 변경은 본 readiness memo와 Spike III spec에 직접 흡수.)
