# pstacky — design

Date: 2026-11-24
Status: draft for review

## Context

pstack (Lauren Tan, MIT) is a 59-skill agent-method stack. Three community Hermes
ports exist and each trades something away:

- `khaeransori/pstack-hermes` — byte-for-byte + adapter, pinned, but its adapter
  assumes Anthropic/OpenAI/Google/xAI route families, so arbitrary `model_map`
  routes fall back to `inherit-parent`.
- `Cloeille/pstack` — 52 skills, hand-rewritten, no arena/correct/statechart.
- `iap/pstack-hermes` — Hermes-native rewrite, converter retired, 49 skills,
  missing `correct`, `sharpen`, `benchmark-checklist`, `statechart`.

pstacky is our own port: upstream text unchanged, an adapter written for both
delegation modes, and `deslop` (required by poteto-mode before every commit but
shipped outside pstack in `cursor-team-kit`).

## Goals

1. Ship pstack 1:1: every upstream skill except `make-bot-ui` (its `curl | sudo
   sh` Tailscale step trips the plugin install scanner), plus one adapter line.
2. Work in both delegation modes: single-model (no `option` in `delegate_task`)
   and routed (`delegation.backend: model_map`, `option` enum), with arbitrary
   route names — not only `<vendored-family>-<effort>`.
3. Include `deslop` as a package skill.
4. Reproducible, diffable build; a pin bump is one command.
5. No JOS-specific rules in the package: house rules stay generic.

## Non-goals

- Rewriting upstream skill text (iap's model) or maintaining a variant.
- Shipping Python that runs at install or at skill-load time: the package is
  content-only; the generator is dev tooling.
- Choosing the user's models. Routes are configured outside the package.
- Replacing `advanced-delegation`; pstacky only uses its `option` field.

## Upstream and pin

- `cursor/plugins` at a commit in `UPSTREAM_PIN`, subtree `pstack/`.
- `deslop` from the same commit, `cursor-team-kit/skills/deslop/SKILL.md`.
- Attribution: MIT © 2026 Lauren Tan, `NOTICE` naming both subtrees and the pin.
- Package version is ours (`0.x.y`), independent of the upstream version, which
  is recorded in `UPSTREAM_PIN` and the changelog. (iap's `0.16.3` conflating the
  two is a naming trap we avoid.)

## Package layout (committed build)

```
plugin.json                     agent-plugins v1, name "pstacky"
NOTICE                          attribution + pin
UPSTREAM_PIN                    sha + upstream version
README.md                       install, modes, update
LICENSE                         MIT
skills/<58 upstream>/           SKILL.md + upstream references/scripts
  references/pstacky-adapter.md copied adapter (one per skill)
  references/agents/<agent>.md  only the agents that skill spawns
skills/deslop/SKILL.md          cursor-team-kit, byte-for-byte, no adapter line
agents/poteto-agent.md          upstream copy
agents/comment-sicko.md         upstream copy
docs/harness/hermes.md          adapter source of truth
docs/guide/                     upstream guide, links rewritten
tools/generate.py               build, --check, --sync
tools/validate.py               package contract checks
tests/                          generator + validator tests
```

Commands come from the plugin namespace: `/pstacky:poteto-mode`,
`/pstacky:interrogate`, `/pstacky:deslop`. Bare `/<name>` is the user's choice
via `skills.external_dirs`, not a package feature.

## Generator contract

`python3 tools/generate.py` builds into the repo tree; `--check` rebuilds in
memory and exits 1 on any difference; `--sync` moves `UPSTREAM_PIN` to a given
sha and rebuilds.

1. Verify the vendored clone (`vendor/cursor-plugins`, gitignored) is at the pin.
2. Copy every `pstack/skills/*` directory byte-for-byte, pruning build junk.
3. Insert exactly one line after the first H1 of each upstream skill:
   `In Hermes, read [the pstacky adapter](references/pstacky-adapter.md) once per session before you follow this file.`
4. Rewrite relative links that leave the skill directory to pinned GitHub URLs.
5. Copy `pstack/agents/*` to `agents/`, and each agent a skill spawns into that
   skill's `references/agents/` (`poteto-mode`/`poteto-help` → poteto-agent;
   `no-comments` → comment-sicko).
6. Copy `deslop` unchanged; it contains no Cursor terms, so it gets no adapter
   line and no per-skill adapter.
7. Copy `docs/guide/`, rewriting asset links to the pinned tree.
8. Generate `plugin.json` (name, own version, MIT, keywords) and `NOTICE`.
9. Refuse to write if any Cursor term from `TERMS` appears in a skill whose
   adapter has no row for it.

Determinism: sorted traversal, no timestamps, LF endings, no absolute paths.

## Adapter contract (`docs/harness/hermes.md`)

One file, copied per skill, so a skill loads standalone without a router.

- **Tool map**: `Task`→`delegate_task`, `AskQuestion`→`clarify`, todo→`todo_list`,
  read/write/edit/search→`read_file`/`write_file`/`patch`/`search_files`,
  shell→`terminal`, web→`web_search`/`web_extract`, browser→`browser_exec`,
  background agents→`delegate_task` + `process_manage`, hooks→Hermes plugins.
- **Subagents**: `subagent_type` mapping to agent files; per-task `option` when
  the schema has it; `model:`/`reasoning:` fields dropped, they are not
  model-facing parameters.
- **Routed mode**: read the `option` enum from the live schema. Names are
  arbitrary strings; the `<family>-<effort>` convention is a hint, never a
  requirement. A role line may name any enum value. No matching route → omit
  `option` (parent route) and say so once.
- **Single-model mode**: no `option` in the schema → every child inherits the
  parent model; panels fan out N children with distinct framings; the
  cross-vendor judge cannot be satisfied — skip it and state it once.
- **`/deslop`** resolves to the package's `deslop` skill.
- **House rules** (generic, no repo specifics): ask before merge, force-push,
  cron changes, config/model changes; never handle secrets by hand; an action
  outside the chat needs consent.

## `setup-pstack` behaviour in pstacky

Reads the live `option` enum (from `delegate_task`'s schema) and
`delegation.backends.model_map.options`; writes `~/.hermes/pstack-models.md`
next to `config.yaml` with one line per role the adapter defines (arena runners,
interrogate reviewers, swarm workers, architect runners, and so on) plus a
`# budget` line.
Rules: values are enum names only; unknown names are refused; `inherit-parent`
always valid; single-model mode writes only the budget line. Idempotent.

## Validation (`tools/validate.py`)

- 59 skills; `name:` unique, kebab-case, matches directory.
- Every upstream skill has exactly one adapter line and its adapter copy; `deslop`
  has neither.
- Every `TERMS` entry used in a skill has a row in the adapter.
- No `{{`, `TODO`, `FIXME` placeholders in generated files.
- No relative link escapes the skill directory; no absolute host paths.
- `plugin.json` parses, declares name/version/license, and its skill count matches.
- Skill names do not collide with Hermes built-in commands.

## Tests and CI

- Unit: generator pure functions (adapter injection, link rewrite, TERMS scan),
  determinism, `--check` catches a one-byte edit.
- Integration: full build against the pinned clone; validate on the resulting tree.
- Smoke (local, needs Hermes): install into a temp `HERMES_HOME`, enable,
  `plugins doctor`, assert `/pstacky:poteto-mode` resolves.
- CI: ruff, `unittest`, `generate.py --check`, `validate.py`. No network beyond
  fetching the pinned repo.

## Rollout

1. Build v0.1.0 at the current upstream pin.
2. Install on `jos` alongside `pstack-hermes` (different plugin name) and run one
   real task with routed mode.
3. If it behaves, remove `pstack-hermes`; keep `deslop` in the package so the
   profile skill can be dropped.
4. Publish the repo (decision below).

## Risks

- Upstream refactors skill layout → generator asserts the strings it injects and
  fails loudly; pin bump is deliberate.
- Adapter drift: 60 copies are generated from one file, validated each build.
- Route names that do not exist → `setup-pstack` refuses; adapter omits `option`.
- Prompt cost: 60 skills in the plugin namespace (same as today's port).

## Open decisions

- Repo hosting: local until the first green run, then GitHub under the user's
  account (default: local).
- Sync cadence: manual `--sync` first; a cron after two clean bumps.
- `docs/guide` shipping: include (default) unless install size matters.

## Decision log

| Decision | Choice |
|---|---|
| Name | `pstacky`, plugin namespace `/pstacky:<skill>` |
| Base | rebuild from `cursor/plugins` with our generator, not a fork of a port |
| Skill text | byte-for-byte upstream + one adapter line |
| Companion skills | `deslop` included; `control-ui`/`control-cli` excluded |
| Routes | generic: no hardcoded models; setup reads the live enum |
| Build | committed, reproducible, `--check` in CI |
| Excluded skill | `make-bot-ui` only: install scanner flags `curl \| sudo sh` |
