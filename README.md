# pstacky

pstack for Hermes Agent, 1:1. Every upstream skill ships byte for byte, with one
adapter line that maps Cursor's tool names to Hermes, plus `deslop` from
`cursor-team-kit`. It works with the default single-model delegation and with
`advanced-delegation`'s `model_map` routes.

Upstream: [cursor/plugins `pstack`](https://github.com/cursor/plugins/tree/main/pstack),
MIT, © Lauren Tan. See `NOTICE`.

## Install

```sh
hermes plugins install <owner>/pstacky --enable
```

Skills land in the plugin namespace: `/pstacky:poteto-mode`,
`/pstacky:interrogate`, `/pstacky:swarm`, `/pstacky:deslop`, and the rest.

## Use

- `/pstacky:poteto-mode <task>` runs the orchestrator, which picks a playbook.
- `/pstacky:interrogate <scope>` runs an adversarial review. Findings need a
  reproducing run.
- `/pstacky:deslop` removes AI slop from the current diff before a commit.

A skill reads `references/pstacky-adapter.md` once per session. That file is
generated from `docs/harness/hermes.md` into every skill.

## Models

**Single-model (default).** `delegate_task` has no `option`, so every child runs
on `delegation.model`. Panels fan out N children on one model with distinct
framings, and the cross-vendor judge is skipped and reported.

**Routed.** With `advanced-delegation` and `delegation.backend: model_map`,
`delegate_task` gains an `option` enum. pstacky maps each pstack role to a route
name. Names are arbitrary; `<family>-<effort>` (`opus-xhigh`, `deepseek-high`) is
only a convention. A role whose family has no route becomes `inherit-parent`.
`/pstacky:setup-pstack` writes the role file to `~/.hermes/pstack-models.md`.

pstacky ships no model ids. Routes are yours to configure.

## What is not shipped

- `make-bot-ui`: it installs Tailscale with `curl | sudo sh`; the plugin
  install scanner treats that as privilege escalation.
- `automations/benny`, upstream `assets/`, `.cursor-plugin/`: Cursor-only.

Upstream text is otherwise unchanged. The only edit is the adapter line after
the first heading (or after frontmatter when a skill has no heading).

## Layout

```
plugin.json            manifest (agent-plugins v1)
skills/<name>/         upstream skill + references/pstacky-adapter.md
skills/deslop/         companion skill, no adapter line
agents/                poteto-agent.md, comment-sicko.md
docs/harness/hermes.md adapter source of truth
docs/guide/            upstream guide
tools/                 generate.py, validate.py, terms.py, vendor.sh
UPSTREAM_PIN           repository, commit, upstream version
```

## Development

```sh
tools/vendor.sh                     # clone cursor/plugins at UPSTREAM_PIN
python3 tools/generate.py           # rebuild skills/, agents/, docs/guide/, plugin.json
python3 tools/generate.py --check   # fail on drift (CI)
python3 tools/validate.py           # package contract
python3 -m unittest discover -s tests -q   # tests (stdlib, no deps)
```

Bump the pin: edit `UPSTREAM_PIN`, re-run `tools/vendor.sh`, `generate.py`,
`validate.py`. The build is deterministic; the generated tree is committed.

## Licence

MIT. `LICENSE` covers the packaging, adapter and tools; upstream pstack and
`deslop` are MIT, © 2026 Lauren Tan, attributed in `NOTICE`.
