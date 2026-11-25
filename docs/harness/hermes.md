# pstacky — Cursor to Hermes adapter

pstack skill text is upstream, unchanged. It speaks in Cursor names. Read this
file once per session before you follow a pstack skill, then map every name with
the tables below. If a Cursor field has no row here, drop it and say so; never
pass a field or value the Hermes tool schema rejects. If the mapped Hermes tool
is not in this session (its toolset is disabled, or the surface does not offer
it), write the `Skipped in Hermes` line from Cursor-only features and continue.

`$HERMES_HOME` is the active Hermes home: `~/.hermes` without a profile,
`~/.hermes/profiles/<name>` with one. Resolve every path below from it; never
hardcode `~/.hermes`.

`<pstacky>` is this package's install directory, the folder that holds `skills/`,
`agents/` and `plugin.json`. Skills load as `pstacky:<name>`; the slash command is
`/pstacky:<name>`. Give subagents absolute paths, never `<pstacky>` itself.

## Tools

| Cursor | Hermes |
| --- | --- |
| `Task` | `delegate_task`. One entry in `tasks` per subagent; entries run in parallel. Children know nothing of this chat, so put every path, constraint and skill to read in `context`. |
| `AskQuestion` | `clarify`. One call holds up to five independent questions. When `clarify` is unavailable (cron, one-shot), ask in plain text and stop. |
| Open a todo list, `TodoWrite` | `todo_list`. When it is deferred behind `tool_search`, load it with `tool_describe` first. A child cannot use it; keep its list in the reply. |
| Run another pstack skill (`/name`, "the **name** skill") | `skill_view("pstacky:<name>")`, then follow it. Within skill text, a relative link such as `../ketchup/SKILL.md` resolves inside this package. |
| `Read` | `read_file` |
| `Grep`, `Glob` | `search_files` (`target: "content"` for Grep, `target: "files"` for Glob) |
| `Shell`, a command | `terminal`. Long runs: `background: true` with `notify: true`. |
| `StrReplace` | `patch`. New or fully rewritten files: `write_file` (read an existing file first). |
| `WebFetch`, `WebSearch` | `web_extract`, `web_search`. JS or login: `browser_exec`. |
| `Await` | If `delegate_task` returned results inline, use them and continue in this turn. This includes orchestrator children, one-shot runs, cron, and inline gateway sessions. If it returned a background dispatch handle instead, end the turn with one status line and never poll; results arrive between turns. |

`/deslop` in pstack text is the companion skill shipped here: load
`pstacky:deslop`. Upstream keeps it in `cursor-team-kit`; pstacky includes it
because poteto-mode requires it before every commit.

## Subagents

| Cursor | Hermes |
| --- | --- |
| `subagent_type: "generalPurpose"` | A plain `delegate_task` entry. |
| `subagent_type: "poteto-agent"` | An entry whose `context` starts with `Read <skill-dir>/worker.md before anything else.`, then "Read `<skill-dir>/references/agents/poteto-agent.md`, then `<skill-dir>/SKILL.md` in full, before any work." Absolute paths. `poteto-mode` and `poteto-help` carry the agent file. |
| `subagent_type: "comment-sicko"` | An entry whose `context` starts with "Read `<skill-dir>/references/agents/comment-sicko.md` and follow it." `no-comments` carries it. |
| `model:` on a `Task` or in an agent file | Routed: the entry's `option` (see Models). Single-model: omit it. |
| Reasoning level | Routed: pick the route that ends in that level. Single-model: put it in `context` ("work at xhigh effort: check every claim"). Never change `delegation.reasoning_effort`. |
| `run_in_background: true` | Omit. `delegate_task` already runs in the background where the session can take a later result, and inline otherwise. |
| `readonly: true` | A normal entry whose `context` says "Read-only: do not edit, create or delete files, and do not commit." When it returns, run `git status --porcelain` and revert anything it touched. |
| `environment: "cloud"` | A worktree on this machine: `git worktree add <path> -b <branch> <base>`, named in `context`. Remove it when the worker is done. |
| `cloud_base_branch: <b>` | Tell the worker to base its worktree on `<b>`. |
| `resume` | Still running: `delegate_task` with `action: "steer"`. Finished: start a fresh entry and paste the earlier result into `context`. |
| `file_attachments` | List paths in `context`; images go in the entry's `images`. |
| Nesting | Children never call `clarify`, `memory` or `cronjob_manage`. A child may call `delegate_task` only when nesting is enabled (`delegation.max_spawn_depth` above 1, orchestrator children); by default children are leaves. When a skill tells a delegate to spawn its own subagents and it cannot, it returns so the parent spawns them; if the delegate does the work itself, it says the pass was not independent. |
| "Inspect its report and diff" | `delegate_task` returns a summary, not a diff. Run `git diff`/`git status --porcelain` in the child's checkout and review that. |

## Models

Check the `delegate_task` schema before the first spawn.

- **Routed.** Task items have an `option` property (`advanced-delegation`,
  `delegation.backend: model_map`). Its enum is the route list; the description
  gives `name: description` per route. Each entry can run elsewhere. Needs the
  `advanced-delegation` plugin; never install it without asking.
- **Single-model.** No `option`. Every child runs on `delegation.model`, else the
  session model. pstack's per-role and multi-vendor choices collapse; say so once.

### Route names

Route names are arbitrary strings. pstack's `<family>-<effort>` convention
(`opus-xhigh`, `gemini-high`, `sol-xhigh`) is a hint, not a requirement: a user
may configure `deepseek-xhigh`, `glm-high`, `nemotron-high`. Use a route name
only when it is in the enum.

Mapping a slug to a route:

1. Split the slug into family and effort (`claude-opus-5-5-xhigh-fast` → `opus`,
   `xhigh`; `gpt-6.2-sol-xhigh` → `sol`, `xhigh`; `gemini-*` → `gemini`).
2. Exact `<family>-<effort>` in the enum: use it.
3. Same family, nearest effort, preferring the lower one on a tie; say which.
4. No route for the family: the slug is unrouted. Never substitute another
   family. Omit `option`, put the effort in `context`, and say where it ran (the
   `model_map` default route when set, else the session model).

A role line that names a route directly is used as is when the name is in the
enum; otherwise apply steps 1 to 4 to it.

### Panels and the judge

| Case | Routed | Single-model |
| --- | --- | --- |
| A panel (arena runners, interrogate reviewers) | One entry per seat, each on its route. Every two seats on the same model get distinct framings in `context` ("assume the design is wrong", "optimize for the reader"). Say each seat's route and whether the panel was single-vendor. | N children, one per seat, same model, distinct framings. Say the panel was single-vendor. |
| The cross-vendor judge | The first pool entry whose route's model vendor (the lab that trained it: Anthropic, OpenAI, Google, DeepSeek, Moonshot, ...) differs from the parent model's. Compare vendors, not the Hermes `provider`: one gateway such as `opencode-go` or `openrouter` serves many vendors. If the vendor is unclear from the route description, check `hermes delegation config --show` (it refuses to run inside the gateway; then ask the user to run it in a shell). No qualifying entry: skip the judge and say so. Never let the parent judge. | The rule cannot be met: skip the judge and say so; the parent still scores candidates. |

After a routed batch, read each result's `route` and `fallback_activated`. A
route that differs, or a fallback, is reported. A `route.refused` is a routing
error: re-map once or omit `option`, retry once. A connection or access failure
(401/403/404, timeout, DNS, TLS) drops that route for the rest of the run; do
not retry it.

Panels larger than `delegation.max_concurrent_children` run in batches.

## setup-pstack

- Detect. Routed: the detected models are the `option` enum with its
  descriptions. Single-model: the session model and `delegation.model`
  (`hermes config get delegation.model`). Say that per-role models need
  `advanced-delegation`.
- Defaults. Routed: map each default slug to a route; a family with no route
  becomes `inherit-parent`, and you say which. Single-model: every value is
  `inherit-parent`.
- Suggest, never substitute. pstack's defaults name Anthropic and Google
  families only, so a user whose routes are all other families (GPT only,
  DeepSeek, Kimi, GLM) gets `inherit-parent` everywhere. At the confirm step,
  for every role left on `inherit-parent` while routes exist, propose one route
  from the route descriptions: a worker or implementation route for
  implementation, bug-fix, hillclimb and swarm roles; a reasoning or review
  route for perf-issue, judgment and prose; distinct routes per panel seat when
  there are enough. Mark each one `suggested`, say why in a few words, and write
  it only if the user accepts. Without an answer (cron, one-shot), keep
  `inherit-parent`.
- No routes in this session. The schema has no `option`, but that only means
  `model_map` is not the active backend: routes can still be saved. Read
  `hermes config get delegation.backend` and
  `hermes config get delegation.backends.model_map.options --json` first.
  - Saved routes exist: name them and offer to activate them with
    `hermes config set delegation.backend model_map`. Change nothing else.
  - None saved: say that per-role models need routes, and how to add them:
    1. `hermes plugins install advanced-delegation --enable` (official catalog).
    2. `hermes delegation config` in a shell, mode Model routes, one route per
       model, ordered cheapest to strongest, each with a one-line description.
       Names follow `<family>-<effort>` (`sol-xhigh`, `deepseek-high`) so the
       defaults map on their own.
    3. A new session, then `/pstacky:setup-pstack` again.

    Offer to do steps 1 and 2. Only on a yes: install the plugin, then add
    each route by reading the stored list, appending the new entries and
    writing the whole list back with `hermes config set
    delegation.backends.model_map.options '<json list>'`, and set
    `hermes config set delegation.backend model_map`. Use provider and model
    ids the user named or that the provider's model list shows are available;
    never invent an id. Never remove or replace a stored route, and never
    change `delegation.backends.model_map.default`, without a separate yes.
    Read the list back and show it.
  - In every case, leave an existing `$HERMES_HOME/pstack-models.md`
    unchanged: a role that names a route this session lacks is still a valid
    choice for a routed session. Write the file only when none exists, every
    value `inherit-parent`. After activating or adding routes, stop: routes
    apply to new sessions, so say to rerun setup-pstack there, where the saved
    choices are checked at the normal confirm step.
- Never install a plugin, add routes, or change `delegation.*` or any Hermes
  config without the user's yes in this run.

## Frontmatter and paths

| Cursor | Hermes |
| --- | --- |
| `disable-model-invocation: true` | Drop silently. Hermes has no equivalent: plugin skills sit in the skill index, and the model may load one on its own. |
| `icon`, `alwaysApply`, `globs` | Drop silently. |
| `.cursor/skills/`, project skill | `<repo>/.hermes/skills/`; Hermes loads it only after `hermes skills trust <repo>`. Tell the user; never trust a repo yourself. |
| `~/.cursor/skills/`, user skill | `$HERMES_HOME/skills/<category>/<name>/` through `skill_manage`. |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `<pstacky>`; the version is in `<pstacky>/plugin.json`. |
| `.cursor/rules/*.mdc`, the `pstack-models.mdc` rule | `$HERMES_HOME/pstack-models.md` for the model roles; repo rules go in `AGENTS.md`. Hermes never reads `.mdc`. |
| `https://github.com/cursor/plugins/blob/ca782ed8b3c2c521cead8e1720d55c3a5dbf2347/pstack/<path>` | The local copy under `<pstacky>/<path>` when it exists; read it, do not fetch it. |
| Agent transcripts | `session_search`; raw files are under `$HERMES_HOME/sessions/` and `$HERMES_HOME/state.db`. Subagent transcripts are the paths `delegate_task` returns. |
| `/loop` | Iterate inside this turn while the check still moves. Longer: `cronjob_manage` after asking the user. |

## Cursor-only features

Hermes has no Bugbot, Cursor cloud agents, Cursor Automations or built-in PR
tool. When a step needs one and no row above gives an equivalent, write one line,
`Skipped in Hermes: <step>. <reason>.`, then continue. Do not stop or retry.

| Cursor | Hermes |
| --- | --- |
| Bugbot | Ordinary PR review threads: triage with `gh`. Skip a step that starts or configures Bugbot when the PR has no such check. |
| Cursor cloud agents | `environment: "cloud"` maps to a worktree. Skip steps that need the cloud machine itself. |
| Canvas, Cursor UI panes | Write the content as markdown and send the path; skip interactive canvas features with the line. |
| Automations, routines, `SendToUser` secret requests | `cronjob_manage` or a webhook route after asking. Secret requests never map: skip with the line. |
| A built-in PR tool | `gh pr create`, `gh pr view`, `gh pr checks`. Not a skip; write no line. |

## Gates that win over a pstack step

- Anything sent outside this machine (email, messages, comments, pushes,
  publishing, merges) needs the user's yes first, even if a playbook says not
  to ask.
- Never type a password, token or card number. For browser logins use
  `browser_vault`; otherwise ask the user to set the secret themselves.
