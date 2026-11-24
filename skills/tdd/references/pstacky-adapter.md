# pstacky — Cursor to Hermes adapter

pstack skill text is upstream, unchanged. It speaks in Cursor names. Read this
file once per session before you follow a pstack skill, then map every name with
the tables below. If a Cursor field has no row here, drop it and say so; never
pass a field or value the Hermes tool schema rejects.

`<pstacky>` is this package's install directory, the folder that holds `skills/`,
`agents/` and `plugin.json`. Skills load as `pstacky:<name>`; the slash command is
`/pstacky:<name>`. Give subagents absolute paths, never `<pstacky>` itself.

## Tools

| Cursor | Hermes |
| --- | --- |
| `Task` | `delegate_task`. One entry in `tasks` per subagent; entries run in parallel. Children know nothing of this chat, so put every path, constraint and skill to read in `context`. |
| `AskQuestion` | `clarify`. One call holds up to five independent questions. When `clarify` is unavailable (cron, one-shot), ask in plain text and stop. |
| Open a todo list, `TodoWrite` | `todo_list` (load it with `tool_describe` first). A child cannot use it; keep its list in the reply. |
| Run another pstack skill (`/name`, "the **name** skill") | `skill_view("pstacky:<name>")`, then follow it. Within skill text, a relative link such as `../ketchup/SKILL.md` resolves inside this package. |
| `Read` | `read_file` |
| `Grep`, `Glob` | `search_files` (`target: "content"` for Grep, `target: "files"` for Glob) |
| `Shell`, a command | `terminal`. Long runs: `background: true` with `notify: true`. |
| `StrReplace` | `patch`. New or fully rewritten files: `write_file` (read an existing file first). |
| `WebFetch`, `WebSearch` | `web_extract`, `web_search`. JS or login: `browser_exec`. |
| `Await` | Background children return as a new message between turns. End the turn with one status line. Never poll. |

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
| `run_in_background: true` | Omit. `delegate_task` already runs in the background and returns a new message. |
| `readonly: true` | A normal entry whose `context` says "Read-only: do not edit, create or delete files, and do not commit." When it returns, run `git status --porcelain` and revert anything it touched. |
| `environment: "cloud"` | A worktree on this machine: `git worktree add <path> -b <branch> <base>`, named in `context`. Remove it when the worker is done. |
| `cloud_base_branch: <b>` | Tell the worker to base its worktree on `<b>`. |
| `resume` | Still running: `delegate_task` with `action: "steer"`. Finished: start a fresh entry and paste the earlier result into `context`. |
| `file_attachments` | List paths in `context`; images go in the entry's `images`. |
| Nesting | Children cannot spawn children and cannot call `clarify`. The chat running the pstack skill owns every spawn. When a skill tells a delegate to spawn its own subagents, return so the parent spawns them; if the delegate does the work itself, it says the pass was not independent. |
| "Inspect its report and diff" | `delegate_task` returns a summary, not a diff. Run `git diff`/`git status --porcelain` in the child's checkout and review that. |

## Models

Check the `delegate_task` schema before the first spawn.

- **Routed.** Task items have an `option` property (`advanced-delegation`,
  `delegation.backend: model_map`). Its enum is the route list; the description
  gives `name: description` per route. Each entry can run elsewhere.
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
| The cross-vendor judge | The first pool entry whose route's provider differs from the parent's. If the provider is unclear, check `hermes delegation config --show`. No qualifying entry: skip the judge and say so. Never let the parent judge. | The rule cannot be met: skip the judge and say so; the parent still scores candidates. |

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
- Budget. Ask with `clarify`. Routed: move each value's effort to the nearest
  route of its family. Names with no effort token do not move.
- Write `~/.hermes/pstack-models.md` with the `# defaults: 3` line, the
  `# budget` line and one line per role, each value a route name or
  `inherit-parent`. Overwrite the whole file. Never write these lines into a
  project's `AGENTS.md`.
- Never install a plugin, add routes, or change `delegation.*` or any Hermes
  config without asking the user.

## Frontmatter and paths

| Cursor | Hermes |
| --- | --- |
| `disable-model-invocation: true` | Drop silently. Plugin skills run only when named or routed to. |
| `icon`, `alwaysApply`, `globs` | Drop silently. |
| `.cursor/skills/`, project skill | `<repo>/.hermes/skills/`; Hermes loads it only from a trusted project dir. Tell the user; never add it yourself. |
| `~/.cursor/skills/`, user skill | `~/.hermes/skills/<category>/<name>/` through `skill_manage`. |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `<pstacky>`; the version is in `<pstacky>/plugin.json`. |
| `.cursor/rules/*.mdc`, the `pstack-models.mdc` rule | `~/.hermes/pstack-models.md` for the model roles; repo rules go in `AGENTS.md`. Hermes never reads `.mdc`. |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | The local copy under `<pstacky>/<path>` when it exists; read it, do not fetch it. |
| Agent transcripts | `session_search`; raw files are under `~/.hermes/sessions/` and `state.db`. Subagent transcripts are the paths `delegate_task` returns. |
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

## House rules that win over a pstack step

- Anything sent outside this chat (email, messages, comments on someone else's
  repo, publishing) needs the user's yes first, even if a playbook says not to ask.
- Never type a password, token or card number. Use the vault tools.
- Pushes to a remote need the user's write token, and a yes for anything outside
  the user's own repos.
