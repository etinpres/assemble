# V4 Spike IX Design — shipper ★ bundle (local build/tag scope)

**Date**: 2026-05-04
**Status**: approved
**Parent**: `project_assemble_v4_spec.md`, `project_assemble_v4_spike_viii.md`

---

## Scope

Single-track spike landing the **fifth self-sufficient ★ bundle** (orthogonal — ship stage),
completing V4's stage-cover guarantee for plan/execute/debug/review/verify/ship.

- **Track A — shipper ★ bundle (orthogonal, local build/tag scope only)** — 4-step pipeline
  that gates a release: pre-flight → version + CHANGELOG → build artifact → local tag.
  Deterministic verdict (`ship-ready` / `blocked`) emitted from concrete artifacts (clean
  tree marker, build exit code, tag SHA), NOT LLM judgment.

Ship gate: **B-14 dogfood** — fresh run_id, SCOPE.md with completion = a real test
command executable from this repo, shipper ★ runs 4 sub-agent dispatches, emits
`SHIP_REPORT.md` with `verdict: ship-ready`. Intentional-fail companion run (e.g. dirty
tree or build failure) verifies `verdict: blocked` path. 12 AC PASS target.

### Critical scope boundary — local-only

shipper ★ does NOT execute any of:

- `git push` (remote push)
- `npm publish` / `pip publish` / `cargo publish` / `gem push`
- Docker registry push (`docker push`, `nerdctl push`)
- App Store Connect / Google Play upload
- Cloud deploy (`fly deploy`, `vercel deploy`, `kubectl apply`)

These are **opt-in hand-offs** documented in SKILL.md §Hand-off. Reasons:

1. V4 정체성 #9 (orchestrator-only) — external publish surface is platform-specific and
   bloats the bundle's responsibility scope.
2. harness 4원칙 #3 (Surgical) — different users have different publish targets (npm vs
   pypi vs app store); a one-size shipper would inevitably over-reach.
3. Codex retro burden — external network/registry surface ≫ local-only build surface.
4. Existing user skills (e.g. gstack `/ship`, `/land-and-deploy`) already cover publish
   workflows; shipper ★ is the *local gate before* hand-off, not the replacement.

shipper ★ output is consumable: SHIP_REPORT.md + tag SHA + build artifact path. Whatever
publishes those is the user's choice (next stage skill, manual command, or CI).

### Out of scope

- ❌ Remote push / publish / deploy (see § Critical scope boundary above)
- ❌ `roles.json` standard role dictionary file (memory-only spec; Spike X candidate
  alongside `release-publish` / `deploy-target` role definitions)
- ❌ keeper ★ bundle (cross-cutting C trace audit + learning recall) — separate spike
- ❌ F4 perf collapse (reviewer ★ Steps 1/2/3/5/6 deterministic shell) — separate spike
- ❌ Multi-language version bumping (only the 3 most common formats supported in MVP:
  `VERSION` plain-text file, `package.json`, `pyproject.toml`. Cargo/Gem/etc. fall back to
  manual user edit before invoking shipper.)
- ❌ Codex CLI / Gemini CLI compat — V4 비범위

---

## Track A — shipper ★ bundle

Orthogonal sibling of verifier ★ — both consume `parsed_scope.json` and require the
SCOPE.md author to declare completion criteria, but verifier *runs* the criterion while
shipper *gates* the release after verification has already passed.

### Inputs

- `run_id` — resolves run_dir to `~/.claude/channels/assemble/runs/<rid>/`.
- `<run_dir>/parsed_scope.json` — must exist (created by reviewer ★ Step 1 or builder ★
  Step 2 or hand-authored via `server.scope_parser.parse_scope_md`).
- `<run_dir>/verify_result.json` — *expected* (from prior verifier ★ run); shipper checks
  `verdict == "pass"` as a precondition. Missing → soft warning + user-override prompt;
  Step 1 sub-agent records `verify_check: missing` in pre-flight result.
- `release_kind` — passed by main as a parameter (`patch` / `minor` / `major` /
  `prerelease`). Default = `patch`. Drives version bump in Step 2.

### Sub-agent matrix (4 step + 1 orchestrator helper)

| Step | Prompt file | Sub-agent type | Tools granted |
|---|---|---|---|
| 1 | `shipper_preflight_step1.md` | `general-purpose` | Read, Write, **Bash** (read-only git status / log) |
| 2 | `shipper_version_step2.md` | `general-purpose` | Read, Write, Edit |
| 3 | `shipper_build_step3.md` | `general-purpose` | Read, Write, **Bash** (single build command, 300s timeout) |
| 4 | `shipper_tag_step4.md` | `general-purpose` | Read, Write, **Bash** (`git tag` — local only) |
| iter | `shipper_iter_revisit.md` | orchestrator helper (NOT in allowlist) | — |

Bash is granted to 3 of 4 steps (vs verifier's 1 of 4). Each step's Bash usage is
narrowly scoped via prompt body — see § Security model below.

### Step responsibilities

#### Step 1 — pre-flight check

Sub-agent runs read-only git probes + verify_result lookup, writes `preflight.json`.

Probes:
- `git status --porcelain` → must be empty (clean tree). Non-empty → `clean_tree: false`,
  `dirty_files: [...]`.
- `git rev-parse HEAD` → records `head_sha` for tag baseline.
- `git rev-parse --abbrev-ref HEAD` → records `branch`.
- Read `<run_dir>/verify_result.json` if exists → records `verify_verdict`.
- Read `<run_dir>/parsed_scope.json` → records `scope_summary` (truncated 200 chars).

Pre-flight verdict (deterministic):
- `pass` if `clean_tree == true` AND (`verify_verdict == "pass"` OR `verify_verdict ==
  "missing"` AND user override flag in run_dir).
- `fail` otherwise.

`fail` aborts dispatch chain — Step 2/3/4 not dispatched. Final SHIP_REPORT still rendered
in Step 4-fail-path (reduced template — see § Artifact contract).

#### Step 2 — version bump + CHANGELOG flip

Sub-agent reads `release_kind` and current version. Detects format from filesystem
priority order:

1. `<run_dir>/../../<repo>/VERSION` (plain-text) — used by gstack-family
2. `<repo>/package.json` (Node.js)
3. `<repo>/pyproject.toml` (Python — both PEP 621 `[project]` and Poetry `[tool.poetry]`)

If none detected → records `version_format: manual` + `manual_hint: "edit VERSION/package.json/pyproject.toml then re-run from Step 2"`. Pipeline aborts (no build, no tag) without error so user can resume.

If detected:
- Computes next version per `release_kind` (semver — `patch`/`minor`/`major`); `prerelease` appends `-rc.<N>` where N starts at 1 if no prior `-rc` suffix or increments existing.
- Writes new version to detected file via `Edit` (in-place, single-line replacement).
- Reads `<repo>/CHANGELOG.md` if exists. Locates `## [Unreleased]` heading. Renames to `## [<new_version>] — <YYYY-MM-DD>` and inserts fresh empty `## [Unreleased]` block above. Missing CHANGELOG → records `changelog_status: missing`, no error.
- Writes `version_bump.json` (old_version, new_version, release_kind, version_format, files_changed, changelog_status).

No git commit/tag at this step — only file edits. Step 4 owns the tagging atom.

#### Step 3 — build artifact

Sub-agent reads `<run_dir>/parsed_scope.json.build` (NEW field — see § Schema additions
below) OR falls back to convention auto-detect:

| Format | Default build command |
|---|---|
| `package.json` w/ `build` script | `npm run build` |
| `pyproject.toml` | `python -m build` |
| `Cargo.toml` (no auto-bump support but build supported) | `cargo build --release` |
| plain `VERSION` (assemble itself) | `pytest -q` ← TEST not BUILD; assemble has no compile artifact |

If both SCOPE-declared and auto-detect available, SCOPE-declared wins. If neither, sub-agent records `build_status: skipped` + `skip_reason: "no build command available"`. Pipeline continues to Step 4 with warning logged in SHIP_REPORT.

Bash execution surface (Step 3 only):
- Single `subprocess.Popen(start_new_session=True)` invocation per verifier Step 2 pattern
- Timeout 300s (vs verifier's 30s — builds legitimately take minutes)
- Output cap 500KB stdout / 500KB stderr (vs verifier's 100KB — build logs are larger)
- Process-group SIGKILL on timeout (Codex retro F2 inherited)
- Streaming read with per-stream byte counter (Spike VIII FIX-1 inherited)

Records `build_result.json` (exit_code, duration_ms, timed_out, truncated, build_command).

#### Step 4 — local tag + SHIP_REPORT

Sub-agent:
1. Reads `version_bump.json.new_version`. Computes tag name = `v<new_version>` (configurable via SCOPE field `tag_prefix` — see § Schema additions; default `v`).
2. Runs `git tag -a <tag_name> -m "<release message>"` where release message =
   `"Release <new_version>\n\nGenerated by assemble shipper ★ run <run_id>"`.
3. Runs `git rev-parse <tag_name>` to capture tag SHA.
4. Renders `SHIP_REPORT.md` from template by substituting placeholders from preflight + version_bump + build_result + tag step outputs.

Bash usage (Step 4 only):
- `git tag` (write, local only — explicitly NOT `git tag -f` or any push)
- `git rev-parse <tag>` (read)

If pre-flight failed (Step 1 verdict=fail), Step 4 still runs but with the **abort path** template (`SHIP_REPORT_ABORT.md.template`) — no tag created, no version bump applied (Step 2/3 were skipped). The abort report enumerates pre-flight failures and recommends fixes.

### Verdict logic (deterministic)

```python
verdict = "ship-ready" if (
    preflight.verdict == "pass"
    AND version_bump.new_version is not None     # version step succeeded or skipped-clean
    AND (build_result.exit_code == 0 OR build_result.skipped == True)
    AND tag_step.tag_sha is not None
) else "blocked"
```

Reason text:
- `ship-ready` → "all 4 steps passed; tag <name> at <sha>"
- `blocked (preflight)` → "<dirty files | missing verify pass | aborted by user override>"
- `blocked (version)` → "version bump failed: <reason>"
- `blocked (build)` → "build exited <N>" or "build timed out (300s)"
- `blocked (tag)` → "git tag failed: <stderr excerpt>"

### Artifact contract

Run dir = `~/.claude/channels/assemble/runs/<rid>/`. Primary artifact: `SHIP_REPORT.md`
(7 canonical sections — see § Section schema). Audit JSONs:

- `preflight.json` (Step 1)
- `version_bump.json` (Step 2)
- `build_result.json` (Step 3)
- `tag_result.json` (Step 4)

#### SHIP_REPORT.md sections (canonical 7)

1. **Summary** — verdict line + tag name + tag SHA + new version (or abort summary)
2. **Pre-flight** — clean tree status, branch, head SHA, verify check result
3. **Version bump** — old → new, release_kind, format detected, files changed, CHANGELOG status
4. **Build artifact** — build command, exit code, duration, truncation flag
5. **Tag** — tag name, tag SHA, message
6. **Verdict reasoning** — concrete signal that fed verdict
7. **Hand-off** — recommended next steps (e.g. `git push --tags`, `npm publish`, manual upload) per project type

Abort template (when pre-flight fails) reuses Sections 1, 2, 6, 7 only — Sections 3, 4, 5
replaced with single "Skipped — pre-flight failed" line each.

### Schema additions to `parsed_scope.json`

Two new optional fields (additive, backwards-compatible — Spike VIII parsers ignore):

- `build` — single-line bash command (≤500 chars), same constraints as `completion`. Used
  by Step 3. If missing, Step 3 falls back to convention auto-detect.
- `tag_prefix` — string ≤10 chars, default `v`. Used by Step 4 to compute tag name.

`server/scope_parser.py` extended to parse two new SCOPE.md sections:

```markdown
## Build

`<build command>`

## Tag prefix

`<prefix>`
```

Existing tests for `parse_scope_md` continue to pass; 6+ new tests cover schema
additions + missing-field defaults + length cap on `build` field.

### Iteration audit invariant

Every iteration produces exactly **4** rows in `dispatches.jsonl` with step names
`step1.iter{N}.preflight`, `step2.iter{N}.version`, `step3.iter{N}.build`,
`step4.iter{N}.tag`. On user-triggered iteration (e.g. amend SCOPE.md after pre-flight
fail), Step 1 always re-runs; Step 2 re-runs only if release_kind changed; Step 3 always
re-runs (build artifacts are not cached); Step 4 only re-runs if Steps 1–3 all pass.

---

## Security model

Bash surface is **larger than verifier ★** (3 of 4 steps grant Bash vs 1 of 4). Threat
table follows verifier's pattern with shipper-specific adjustments:

| # | Threat | Severity | Mitigation |
|---|---|---|---|
| T1 | Malicious SCOPE author injects destructive build payload | low-med | length cap 500 on `build`; SCOPE author trust scope (repo owner / equivalent); same model as `make`/`npm test` |
| T2 | Runaway build blocks pipeline | medium | Popen + streaming read + TIMEOUT_S=300 + process-group SIGKILL (verifier Step 2 pattern reused) |
| T3 | Build output flood saturates RAM | medium | streaming read + per-stream cap 500KB (Spike VIII FIX-1 pattern reused, larger cap) |
| T4 | Build artifact dropped in unexpected location | low | shipper does not consume build output paths — only exit code + log capture |
| T5 | `git tag` collides with existing tag | medium | Step 4 pre-checks `git tag -l <name>` before creating; collision aborts with `blocked (tag)` verdict |
| T6 | `git tag -f` overwriting existing tag | high | Step 4 prompt body explicitly forbids `-f` flag; harness preamble v3 surgical-changes rule reinforces; SECURITY.md explicit |
| T7 | Tag pushed to remote unintentionally | high | Step 4 prompt body explicitly forbids `git push` (any form); SHIP_REPORT §Hand-off documents push as user-owned next step |
| T8 | Pre-flight Bash escape (`git status; rm -rf /`) | high | Step 1 prompt body uses argv list invocation only (`subprocess.run(["git", "status", "--porcelain"], ...)`) — no shell, no string interpolation |
| T9 | Pre-flight reads outside repo | low | git probes scoped to cwd (assemble repo or run_dir parent); SCOPE author can specify `git_repo` field for cross-repo workflows (Spike X — explicitly out of scope here) |

Codex retro is **mandatory for Spike IX** (per user's directive — security-sensitive
publish/push surface). The retro will exercise:
- Step 1 argv-list git invocation (T8) — confirm no `shell=True` or string concat
- Step 4 `git tag` invocation — confirm no `-f`, no `push`, no remote interaction
- Build command execution surface (T2, T3) — verify FIX-1 streaming pattern correctly
  inherited
- Tag collision handling (T5)
- SECURITY.md threat table completeness

The `Bash tool access GRANTED` substring marker convention (introduced in Spike VIII) is
reused — each Step 1, 3, 4 prompt body contains the marker for grep-based audit.

### Allowlist enforcement

`server.harness.ALLOWED_PROMPT_FILES` extended with 4 new entries:
- `shipper_preflight_step1.md`
- `shipper_version_step2.md`
- `shipper_build_step3.md`
- `shipper_tag_step4.md`

`shipper_iter_revisit.md` lives under `prompts/orchestrator/` and is registered in
`ORCHESTRATOR_ONLY_PROMPTS` (Spike VIII Pre-IX FIX-3 contract).

`_BUNDLED_DIR_TO_STAGE` extended with `"shipper": "ship"`.

### Hand-off (NOT shipper's responsibility)

SHIP_REPORT.md §7 Hand-off enumerates concrete next-step commands the user must run
(or delegate to another skill):

- `git push origin <branch> && git push origin <tag>` — remote push
- `npm publish` / `python -m twine upload dist/*` / etc. — registry publish
- gstack `/land-and-deploy` — full merge + deploy chain
- App Store Connect / Play Console — manual upload of build artifact

The goal is to make hand-off explicit + auditable, NOT to automate it.

---

## V4 정체성 보호

- ✅ Spike I~VIII core contracts (verdict logic, allowlist, 7-section, RUN_DIR token)
- ✅ canonical preamble v3 sha `8d22a29c9712d2c0c05bc2145ca5ad56c7e19705087dde4dd625908f7ec089a9` (Spike VIII corrected)
- ✅ ALLOW_LIST = {v1, v2, v3} unchanged (allowlist *additive* — 4 new entries)
- ✅ V3 concierge menu layer unchanged
- ✅ existing ★ bundle prompts (plan-pack / debugger / builder / reviewer / verifier) unchanged
- ✅ orchestrator-only V4 #9 — main never executes Bash; sub-agents own all 3 Bash-granted steps
- ✅ `run_dir_path` / `substitute_inputs` / `extract_wrote_paths` API unchanged (parser
  helper `parse_scope_md` extends additively for `build` + `tag_prefix` fields)
- ✅ `{{RUN_ID}}` / `{{RUN_DIR}}` token contracts unchanged
- ✅ `parsed_scope.json` shape additive only (existing keys untouched, two new optional fields)
- ✅ `ORCHESTRATOR_ONLY_PROMPTS` registered in single source of truth (`server.harness`)
- ✅ scope_parser deterministic helper untouched in core grammar (B-13 strict grammar
  preserved); only adds two new SCOPE.md section recognizers
- ✅ Codex retro mandatory (per user directive on security-sensitive surface)

---

## Acceptance criteria (B-14 dogfood)

| AC | Description |
|---|---|
| AC1 | shipper ★ bundle directory exists at `bundled/shipper/` with SKILL.md + SECURITY.md + 4 subagent prompts + 1 orchestrator helper + 2 templates (SHIP_REPORT, SHIP_REPORT_ABORT) |
| AC2 | `bundled/shipper/SKILL.md` declares `stages: ["ship"]` (inline form per Spike VI B1 fix); inventory scan classifies shipper into ship stage |
| AC3 | `server.harness.ALLOWED_PROMPT_FILES` includes 4 shipper subagent prompts; `_BUNDLED_DIR_TO_STAGE` includes `"shipper": "ship"`; `ORCHESTRATOR_ONLY_PROMPTS` includes `shipper_iter_revisit.md` |
| AC4 | `server.scope_parser.parse_scope_md` recognizes `## Build` and `## Tag prefix` sections; defaults applied when missing; length cap 500 on build enforced |
| AC5 | B-14 happy-path dogfood: clean tree + verifier verdict=pass + valid SCOPE.md → 4 dispatches → `SHIP_REPORT.md` rendered with 7 sections + verdict=ship-ready + tag created locally |
| AC6 | B-14 abort-path companion: dirty tree → Step 1 verdict=fail → Steps 2-3 skipped, Step 4 abort template rendered → verdict=blocked (preflight) |
| AC7 | B-14 build-fail companion: clean tree but build command exits 1 → Steps 1-2 pass, Step 3 records exit_code≠0 → verdict=blocked (build); no tag created |
| AC8 | dispatches.jsonl row count = 4 happy-path / 4 abort (Step 4 still dispatched for abort report) / 3 build-fail (Step 4 skipped — already verdict=blocked at Step 3) |
| AC9 | wall-time budget: self-execute ≤ 60s; real-dispatch ≤ 600s |
| AC10 | orchestrator-only: main Claude does NOT call Bash directly during dispatch chain (verified via dispatches.jsonl introspection) |
| AC11 | Codex retro applied: at least 1 amendment landed pre-ship (or all findings closed as documented non-goals); SECURITY.md updated to reflect retro outcomes |
| AC12 | contracts.json: 3 new entries — `spike-ix-shipper-allowlist` (4 prompts), `spike-ix-shipper-verdict-invariant` (deterministic rule), `spike-ix-shipper-artifact-invariant` (7-section SHIP_REPORT.md schema lock) |

Pytest baseline 449 → target 449 + ≥30 new tests = ≥479 passing.

---

## Phase roadmap

| Phase | Tasks | Output |
|---|---|---|
| **A** — scope_parser extension | A1: extend `parse_scope_md` for `build` + `tag_prefix` sections + tests; A2: `server/version_helpers.py` (semver bump pure function + format detection); A3: `server/git_helpers.py` (read-only git probe wrappers, argv-list only) | shared library extensions, no shipper bundle yet |
| **B** — shipper subagent prompts | B1: `shipper_preflight_step1.md` (read git status, verify_result, parsed_scope; emit preflight.json + verdict); B2: `shipper_version_step2.md` (Edit-only version + CHANGELOG flip); B3: `shipper_build_step3.md` (Bash exec build w/ FIX-1 pattern); B4: `shipper_tag_step4.md` (`git tag` + SHIP_REPORT render) | 4 subagent prompts in `bundled/shipper/prompts/subagent/` |
| **C** — orchestrator helper + SKILL.md + templates + SECURITY.md | C1: `shipper_iter_revisit.md` orchestrator helper; C2: `bundled/shipper/SKILL.md` (full body — When/Inputs/Artifacts/CRITICAL/Step 0–4/Iteration); C3: `SHIP_REPORT.md.template` + `SHIP_REPORT_ABORT.md.template`; C4: `bundled/shipper/SECURITY.md` (threat table T1–T9 + allowlist + hand-off) | bundle is dispatchable but harness allowlist not yet updated |
| **D** — harness wiring | D1: extend `ALLOWED_PROMPT_FILES` (4 entries); D2: extend `_BUNDLED_DIR_TO_STAGE` (`"shipper": "ship"`); D3: extend `ORCHESTRATOR_ONLY_PROMPTS` (`shipper_iter_revisit.md`); D4: contracts.json 3 entries | bundle reachable via dispatch chain |
| **E** — Codex retro (MANDATORY) | E1: dispatch `codex:codex-rescue` against shipper threat table + Step 1/3/4 prompt bodies + git tag invocation; E2: apply amendments; E3: write `docs/dogfood/spike-ix-codex-retro.md` | retro doc + amended SECURITY.md + amended prompt bodies |
| **F** — integration tests + B-14 dogfood + ship | F1: integration tests (dispatch_prompt + RUN_DIR + preamble v3 sha — verifier Spike VIII A9 pattern); F2: B-14 happy-path self-execute + real-dispatch; F3: B-14 abort + build-fail companions; F4: dogfood doc; F5: CHANGELOG flip + ship | shipped + memory updated |

Phase E is **mandatory gate** between D and F per user directive on security-sensitive
surface (publish/push concerns even though shipper itself is local-only — the threat
boundary is `git tag` write + 3-step Bash surface).

---

## Risks & open questions

### R1 — Convention auto-detect explosion (medium)

Step 3 fallback chain (`package.json` → `pyproject.toml` → `Cargo.toml` → assemble's
`pytest -q`) is opinionated. Different repos may have non-standard build conventions
(monorepos, custom scripts). MVP punts to manual SCOPE-declared `build` field + 4
hardcoded fallback rules. Future expansion → roles.json `release-publish` per-stack
preferences.

### R2 — Tag prefix collision (low)

Default `v<version>` (e.g. `v0.16.0`) is widely-adopted but not universal. SCOPE field
`tag_prefix` overrides. If user has existing tags in different scheme (e.g. `release-`,
`v.`), they must declare `tag_prefix` in SCOPE.md or rename existing tags before
shipping. Documented in SKILL.md §Inputs.

### R3 — Codex retro scope creep (medium)

Codex retro for Spike IX security surface (T1–T9) is ambitious. To avoid retro becoming
its own spike, retro is bounded to:
- Threat table T1–T9 review only
- Step 1, 3, 4 prompt body audit (Step 2 is Edit-only, low-surface)
- `git tag` invocation argv-list audit
- SECURITY.md hand-off boundary check

Out of retro scope: full repo audit, Phase D harness changes (already covered by Spike
VIII conventions), template content review.

### R4 — `prerelease` semantics (low)

`prerelease` release_kind appends `-rc.<N>` only — doesn't support `-beta`/`-alpha` or
custom prerelease tags. MVP picks the most common convention; future extension is
additive (new release_kind values).

### R5 — Multiple version files in single repo (low)

A repo with both `VERSION` and `package.json` (e.g. assemble itself if it ever ships as
npm) — Step 2 picks the first detected per priority order and records `files_changed`
list. SCOPE author can override via future `version_files` SCOPE field (out of scope —
Spike X candidate). MVP behavior documented in SKILL.md §Inputs.

---

## Source

- Parent spec: `~/.claude/skills/assemble/docs/specs/2026-05-04-v4-spike-viii-design.md`
- V4 master spec: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spec.md`
- Sibling memory: `~/.claude/projects/-Users-yonghaekim-my-folder/memory/project_assemble_v4_spike_viii.md`
- harness reference: `~/.claude/skills/assemble/server/harness.py` (ALLOWED_PROMPT_FILES line 52, ORCHESTRATOR_ONLY_PROMPTS line 47, _BUNDLED_DIR_TO_STAGE line 107 — verified 2026-05-04)
