# shipper quick mode — single-dispatch fallback
You are dispatched as shipper quick mode sub-agent. Print `WROTE: <absolute path>` on stdout when done. No other prose. Main parses with regex `^WROTE: (.+)$`.

## Bash tool access GRANTED

shipper full mode Steps 1/3/4 와 동일하게 quick mode 도 git probes + build invocation + git tag 를 위해 Bash 사용. argv-list (`server.git_helpers`) 로 호출, no `shell=True`, no string interpolation. 명시적 forbidden:

- `git tag -f` (T6)
- `git push` (any form — T7, local-only)
- `npm publish` / `twine upload` / 등 registry publish

build invocation 은 process-group SIGKILL on timeout (300s budget), 500KB stdout/stderr cap.

## Inputs

- run_id: `{{RUN_ID}}`
- run_dir: `{{RUN_DIR}}`
- release_kind: `{{RELEASE_KIND}}` (patch / minor / major / prerelease, default `patch`)

## Goal

full mode 의 4-step shipper pipeline (Step 1 preflight → Step 2 version + CHANGELOG flip → Step 3 build → Step 4 local tag + report render) 을 단일 dispatch 로 압축. `SHIPPER_LOG.md` (= full mode 의 `SHIP_REPORT.md` 동치) 1 doc 에 7 sections 모두 inline.

산출물 schema 는 full mode 와 동일 — 단일 pass 안에서 git probes + version bump + build + local tag 모두 처리. **NEVER push, publish, or deploy.**

## Output sections (must include all)

`SHIPPER_LOG.md` (= `SHIP_REPORT.md`) 안에 다음 7 canonical sections 모두 포함 (full mode happy path schema 보존):

- `## 1. Summary` — verdict line (`ship-ready` / `blocked`) + 1-line 사유
- `## 2. Pre-flight` — clean_tree / branch / head_sha / verify_check 결과
- `## 3. Version bump` — version_format + previous → new version + CHANGELOG flip 결과
- `## 4. Build artifact` — build_command + exit_code + duration_ms + artifact path
- `## 5. Tag` — tag_name (= `<tag_prefix><new_version>`) + tag_sha
- `## 6. Verdict reasoning` — deterministic rule 적용 결과
- `## 7. Hand-off` — 다음 step 명시 (push / publish / deploy 는 user 책임 — verbatim list from SKILL.md § Hand-off)
- `## Mode usage note` — `mode=quick` 1-line marker

Abort variant (preflight fail 시): sections 1, 2, 6, 7 만 채우고 3/4/5 는 "Skipped — pre-flight failed" 1-line.

Verdict logic (deterministic, full mode 와 동일):
```python
verdict = "ship-ready" if (
    preflight.verdict == "pass"
    AND new_version is not None
    AND (build_exit_code == 0 OR build_skipped)
    AND tag_sha is not None
) else "blocked"
```

## Save block

```python
python3 << 'EOF'
from pathlib import Path

run_id = "{{RUN_ID}}"
run_dir = Path("{{RUN_DIR}}")
release_kind = "{{RELEASE_KIND}}"

# Sub-agent: 동일 dispatch 안에서 다음 모두 처리
# 1. preflight (server.git_helpers) — clean_tree / verify_check
# 2. version bump (server.version_helpers.bump_semver) + CHANGELOG flip via Edit
# 3. build invocation (parsed_scope.build → conv detect chain) — Popen + 300s timeout
# 4. local tag — argv git tag -a <prefix><version> -m <msg>; rev-parse <tag>
# 5. SHIP_REPORT.md render — 7 sections (or 4-section abort if preflight fail)
# Forbidden: git tag -f / git push / publish / deploy.

body = f"""# SHIP_REPORT

**Run ID**: {run_id}
**Mode**: quick (single-dispatch fallback — V4 Spike XIV paradigm hybrid)
**Release kind**: {release_kind}

## 1. Summary

**Verdict**: <TBD: ship-ready | blocked>

<TBD: 1-line reason>

## 2. Pre-flight

- clean_tree: <TBD>
- branch: <TBD>
- head_sha: <TBD>
- verify_check: <TBD pass | missing>

## 3. Version bump

- version_format: <TBD VERSION | package.json | pyproject.toml | manual>
- previous: <TBD>
- new: <TBD>
- CHANGELOG flip: <TBD applied | skipped>

## 4. Build artifact

- build_command: <TBD>
- exit_code: <TBD>
- duration_ms: <TBD>
- artifact path: <TBD or "n/a">

## 5. Tag

- tag_name: <TBD v<version>>
- tag_sha: <TBD>

## 6. Verdict reasoning

Deterministic rule applied (preflight.pass AND version AND build.ok AND tag.sha → ship-ready).

## 7. Hand-off

shipper ★ output is consumable. Whatever publishes is the user's choice. Concrete next-step commands:

- `git push origin <branch> && git push origin <tag>` — remote push
- `npm publish` / `python -m twine upload dist/*` / `cargo publish` / `gem push` — registry publish
- gstack `/land-and-deploy` — full merge + deploy chain
- App Store Connect / Google Play Console — manual upload of build artifact
- Cloud deploy (`fly deploy`, `vercel deploy`, `kubectl apply`) — platform-specific

## Mode usage note

mode=quick — full mode 의 4-step shipper pipeline 이 단일 dispatch 로 압축됨. precision 손실 가능. KEEPER_REPORT § "Mode usage" 에 카운트 기록.
"""

out = run_dir / "SHIP_REPORT.md"
out.write_text(body, encoding="utf-8")
print(f"WROTE: {out}")
EOF
```

## Output discipline

Single trailing line: `WROTE: <abs path to SHIP_REPORT.md>`. No prose, no banners. Errors via `ERROR: <reason>` on stdout — main follows §CRITICAL retry/abort/report.
