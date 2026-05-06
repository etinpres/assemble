# /assemble — Tool Concierge for Claude Code

[🇰🇷 한국어](README.ko.md)

[![tests](https://github.com/etinpres/assemble/actions/workflows/test.yml/badge.svg)](https://github.com/etinpres/assemble/actions/workflows/test.yml)
[![license](https://img.shields.io/github/license/etinpres/assemble)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![version](https://img.shields.io/badge/version-4.0.0-brightgreen)](CHANGELOG.md)

A Claude Code skill that scans your installed skills / plugins / agents, recommends a per-stage workflow for a task, and lets you pick which tool runs at each stage. **v4.0.0 ships a self-sufficient bundle library** — 7 ★ bundles + 3 standard bundles cover all 8 sequential stages + 2 orthogonal stages (safety/meta), so a blank Mac with only this skill installed can drive a real project end-to-end.

## What it does

1. **Scans** every `SKILL.md` (user + plugin) and every agent `.md` on your machine.
2. **Classifies** each one into stages (`discover / plan / design / execute / debug / review / verify / ship` + orthogonal `safety / meta`) via a frontmatter-keyword heuristic. Anything the heuristic isn't confident about is left as `unclassified` and filled in on demand by an inline LLM pass.
3. **Recommends a stage sequence** for the task you typed.
4. **Runs a per-stage menu loop** — at each stage you see the tools that fit + meta actions (`ask / skip / manual / back / done`) + contextual safety/meta helpers. Pick one, run it, advance.
5. **Persists a run log** so `/assemble resume` picks up where you stopped.
6. **Bundled tool library** — 7 ★ bundles + 3 standard bundles cover plan / execute / debug / review / verify / ship + discover / design / safety / meta. Each ★ bundle is a multi-step sub-agent pipeline (4-7 dispatches) producing structured artifacts (PRD / SCOPE / IMPL_REPORT / DEBUGGER_LOG / etc.).
7. **Paradigm hybrid (mode gate)** — every ★ bundle entry asks `[full / quick]` via `AskUserQuestion`. Default is full (spec-compliant N-step pipeline). Quick mode is opt-in (single dispatch fallback) for time-pressed runs.

## ★ bundles + standard bundles (V4 lineup)

10 bundles cover every stage. ★ bundles run multi-step sub-agent pipelines and emit structured artifacts; standard bundles are single-dispatch helpers (or main-IO-only per V4 #9 exception).

| Stage | Bundle | Grade | Pipeline |
|---|---|---|---|
| discover | `idea-shaper` | standard | 1-step interview → IDEA.md |
| plan | `plan-pack` | ★ | 4-doc parallel dispatch (PRD + ARCH + ADR + UI_GUIDE) + cross-doc review + iteration |
| design | `design-pack` | standard | 1-step → DESIGN.md + ANTI_PATTERNS.md |
| execute | `builder` | ★ | TDD red→green pipeline (SCOPE → test_first → impl → verify → review → report) |
| debug | `debugger` | ★ | systematic-debugging (hypothesis → repro → bisect → root cause → fix) |
| review | `reviewer` | ★ | SCOPE-deviation + LLM trust boundary + SQL safety + secret leak |
| verify | `verifier` | ★ | extract → execute → classify → report (AC = bash, exit-code adjudicated) |
| ship | `shipper` | ★ | preflight → version bump → build → tag → release notes (local scope) |
| safety | `guardian` | standard | main-direct IO (V4 #9 exception) — destructive cmd warnings + dir freeze |
| meta | `keeper` | ★ | run audit + 5-rule extractor + LLM summarize + ledger append + prune |

The mode gate fires once per ★ bundle entry. Pick `full` for spec-compliant pipelines, `quick` if you only have time for a single-dispatch fallback (artifact schema preserved, precision lower).

## Origins / inspiration

V4's harness preamble is descended from a chain of work that started with Andrej Karpathy's observations on coding-AI failure modes:

- [@karpathy on X](https://x.com/karpathy/status/2015883857489522876) — diagnosed LLM coding pitfalls (over-engineering, scope creep, fabricated context, fix-on-symptom).
- [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) — distilled those observations into a 65-line `CLAUDE.md` that became the most-starred Claude Code skill on GitHub (115k+ ★).

V4 absorbs the same 4 principles ("Think Before Coding / Simplicity First / Surgical Changes / Goal-driven Execution") but routes them through a different mechanism — **sub-agent prompt prepending**. Every dispatchable bundle prompt is wrapped by `bundled/_shared/harness-preamble.md` so the rules show up *inside the sub-agent's context*, not just inside the orchestrator's. The wrapping is byte-identical (canonical sha `8d22a29c…`), audited via `dispatches.jsonl`, and survives across iterations.

The preamble also adds 3 V4-specific rules on top of Karpathy's 4:
- **Rule 5** — natural Korean labels (no machine-translation artifacts in user-facing prompts when the user types in Korean)
- **Rule 6** — user-stated task is a *seed*, not a contract; ★ bundle full pipelines are the contract
- **Rule 7** — sub-agents may not read other skills' infrastructure code (server/ modules, hooks/, settings.json)

### Why prepending, not just rules

The decision to route the preamble through sub-agent prompts (rather than just publishing rules in `CLAUDE.md` and `SKILL.md`) came from a concrete conversation between this skill's author and Claude itself. The author asked: *"honestly, what fraction of the rules written in `CLAUDE.md` and `SKILL.md` does Claude end up ignoring?"* Claude's answer: **30–40%**. The author followed up: *"then writing more and more rules into more `.md` files is kind of pointless, isn't it?"* Claude agreed, and proposed the inverse — instead of writing rules and hoping they're read, **prepend the rules into every dispatched sub-agent's prompt so they cannot be ignored without literally rewriting them**. That conversation kicked off V4 development.

The 30–40% acknowledgement is what makes prepending non-negotiable in V4: even with perfect rules in `CLAUDE.md`, roughly a third of them won't reach the executing turn. The bundle library exists to close that gap — by putting the rules where they actually fire (inside the prompt the sub-agent receives), audited byte-for-byte against the canonical preamble sha.

## Install

```bash
git clone https://github.com/etinpres/assemble ~/.claude/skills/assemble
# Python 3 + PyYAML — `pip install pyyaml`. No other dependencies.
```

Reload Claude Code and run:

```
/assemble build a small CLI for parsing CSV files
```

`/assemble` walks you through:
1. Inventory scan (skills + agents + plugins on your machine).
2. Stage-sequence recommendation → you `approve` / `edit` / `cancel`.
3. Per-stage menu — pick a tool. ★ bundles appear with a leading `★` and sort first.
4. For ★ bundles, a mode gate asks `full` (spec pipeline) or `quick` (single dispatch).
5. Run the tool. Sub-agent dispatches are logged to `dispatches.jsonl`. Artifacts land in `~/.claude/channels/assemble/runs/<run_id>/`.
6. Stage marks done. Next stage menu appears. Repeat until sequence completes.

Resume mid-run with `/assemble resume`.

## How classification works

The heuristic classifier is conservative — anything it can't confidently map is left `unclassified`. Instead of a bulk pre-warm pass, the inline LLM classifier picks up the top-2 unclassified entries most relevant to the current `/assemble <task>` and classifies them on the spot. Results persist across runs in `~/.claude/channels/assemble/inventory.json`, so each task only pays for its relevant classifications — never the whole inventory.

There's also a CLI at `bin/classify-inventory` for dedicated bulk runs; it emits a JSONL prompt bundle on stdout and applies JSONL responses via `--apply <file>`. Most users never need it.

## Language / locale

Everything is English by default. A Korean locale is bundled:

```bash
export ASSEMBLE_LOCALE=ko   # menu labels & helper text switch to Korean
```

To contribute another locale, copy `config/i18n/en.json` → `config/i18n/<code>.json`, translate the strings, and set `ASSEMBLE_LOCALE=<code>`. Missing keys fall back to English so partial translations still work.

## Requirements

- Python 3 (stdlib + **PyYAML**, e.g. `pip install pyyaml`)
- Claude Code with the `Skill` + `AskUserQuestion` tools.
- Optional: pytest if running the test suite

## Repository layout

```
SKILL.md                  # Claude-facing procedure (the actual skill)
server/                   # Stdlib-only Python module
  __init__.py             # Facade — always import from `server`
  inventory.py            # Skill/agent scan, heuristic classifier
  classify.py             # LLM classification prompt + parser
  sequence.py             # Stage-sequence prompt + parser
  menu.py                 # Stage-menu builder (tools + meta + helpers)
  progress.py             # Run lifecycle (create / mark / resume / list)
  state_store.py          # Atomic JSON read/write with file locking
  i18n.py                 # Locale loader (env-var driven)
  harness.py              # Sub-agent dispatch + preamble wrapping + audit
  eject.py                # /assemble eject sub-command (V4 #9 IO exception)
bundled/                  # V4 bundle library — 10 self-sufficient skills
  _shared/
    harness-preamble.md   # 7-rule preamble (Karpathy 4 + V4-specific 3)
  plan-pack/              # ★ — 13-step PRD/ARCH/ADR/UI_GUIDE pipeline
  builder/                # ★ — TDD red→green pipeline
  debugger/               # ★ — systematic-debugging pipeline
  reviewer/               # ★ — SCOPE deviation + trust boundary review
  verifier/               # ★ — AC-as-bash exit-code adjudication
  shipper/                # ★ — local build/tag/release pipeline
  keeper/                 # ★ — run audit + learning ledger
  idea-shaper/            # standard — interview → IDEA.md
  design-pack/            # standard — DESIGN.md + ANTI_PATTERNS.md
  guardian/               # standard — main-IO safety (V4 #9 exception)
bin/
  classify-inventory      # Offline bulk-classification CLI
config/
  stages.json             # Stage ids only (display text lives in i18n/)
  stage_roles.json        # Role names used by contextual_helpers
  i18n/
    en.json               # English (default)
    ko.json               # Korean
docs/                     # Architecture + run docs
tests/                    # 833 pytest cases (unit + e2e + contracts + dogfood)
```

## Running tests

```bash
cd ~/.claude/skills/assemble
python3 -m pytest tests
```

Expected: `833 passed` in under 20 seconds. (CI matrix: 3.10 / 3.11 / 3.12 — see `.github/workflows/test.yml`.)

## Design notes worth knowing

- **No global skill-name table.** The earlier design shipped `pre_mapping.json` with a baked-in list of known skills. It was retired because you can't pre-map what isn't installed. Classification now reads each skill's own `SKILL.md` frontmatter.
- **User > plugin precedence.** If two skills share a name, the user-installed one wins via path-priority first-wins dedupe.
- **Corrupt cache is quarantined, not silently destroyed.** A bad `inventory.json` is renamed `inventory.json.bad-<ts>` and rebuilt. You can inspect the bad file later.
- **Concurrent writers are safe.** `scan()` and `apply_classification()` share `update_json_locked`, so an `/assemble` run and a background `classify-inventory` don't clobber each other.
- **No skill bodies in the menu.** `build_stage_options()` returns only `{label, kind, description(≤80), tool_path}` — bodies load lazily when `Skill` actually invokes the tool.
- **Plays well with other plugins.** SessionStart and file-pattern hooks from installed plugins (Vercel, gstack, etc.) are Claude Code runtime behavior; they don't interfere with the `/assemble` stage loop. Instead, those plugins' skills get classified into stages and become candidate tools — e.g. `vercel-cli` shows up under `ship`, `vercel-agent` under `review`/`debug`.
- **Canonical preamble sha v3 invariant.** Every dispatched sub-agent prompt is wrapped via `wrap_with_preamble`; the wrapped preamble portion always hashes to `8d22a29c…089a9`, audited per-record in `dispatches.jsonl`. ALLOW_LIST = {v1, v2, v3} so older runs still verify green.
- **Bundles are bundled, not nested skills.** A skill named `builder` in a user's `~/.claude/skills/builder/` and a bundled `builder` under `~/.claude/skills/assemble/bundled/builder/` co-exist; the menu shows both, marked `★` only for the bundled one.
- **Paradigm hybrid is opt-in only.** Quick mode never fires unless the user explicitly picks it via the AskUserQuestion mode gate; the orchestrator never decides to "save time" on its own. (V4 #11 + 4원칙 #1 enforcement.)
- **`/assemble eject <bundle>` copies a bundle into your user-skills tree** (`~/.claude/skills/<name>/`) so you can fork + customize without mutating the bundled copy. Default flow stays untouched.

## Contributing

- Write all code comments in English.
- User-visible strings go in `config/i18n/*.json`, never hardcoded.
- `from server import ...` only — don't reach into submodules.
- Run `python3 -m pytest tests` before opening a PR.

## License

MIT.
