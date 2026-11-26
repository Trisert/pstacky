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

In Hermes these steps replace setup-pstack's steps 1 to 5. Steps 6 to 8
(confirm, then the optional verification skills) stay as written. One run is
enough: the role file is read by every later session.

Ignore the `~/.cursor/rules/pstack-models.mdc` path from upstream step 2 — read
`$HERMES_HOME/pstack-models.md` only, even in your first tool batch.

1. **Routes.** Read `hermes config get delegation.backends.model_map.options
   --json` and `hermes config get delegation.backend`. The config is the source
   of truth; when `model_map` is active the `option` enum shows the same list.
   - Routes exist: go on, whether or not `model_map` is active.
   - None: say that per-role models need routes, and offer to add them. Only
     on a yes: `hermes plugins install advanced-delegation --enable` when it is
     missing, then add each route by reading the stored list, appending the new
     entries and writing the whole list back with `hermes config set
     delegation.backends.model_map.options '<json list>'`. Use provider and
     model ids the user named or that the provider's model list shows; never
     invent an id. Name each route after the model it runs, then its effort
     (`deepseek-xhigh`, `kimi-high`), cheapest first, each with a one-line
     description; never name a route for a family it does not run. Read the
     list back, show it, and go on with it.
   - The user declines: leave an existing `$HERMES_HOME/pstack-models.md`
     unchanged; when none exists, write one with every value
     `inherit-parent`. Stop.
2. **Current choices.** Read `$HERMES_HOME/pstack-models.md` only; never look
   under `~/.cursor/`. Drop retired roles (`hardest tasks`, `architect
   runners`, `reflect tooling`, `why investigators`). Do not run upstream's
   Cursor-slug migrations (`gemini-4-*`, `grok-*`, `claude-*`) on Hermes route
   names.
3. **Budget, only when it can move a role.** Ask with `clarify` only when at
   least one role (a saved choice or a mapped default) uses a family that has
   two or more configured routes at different efforts. Offer these three
   options with these exact labels, naming the current budget when the file
   records one (or saying `large` matches the defaults when there is no file):
   - `large — xhigh reasoning`
   - `medium — high reasoning`
   - `small — medium reasoning`

   On the ladder `xhigh > high > medium > low`, `large` keeps each role's
   target effort (`xhigh` for single-model roles, `high` for `swarm workers`
   and panel seats other than Gemini's `xhigh` seat), `medium` lowers each
   target one step, and `small` lowers it two steps (clamped at `low`).
   Otherwise do not ask: keep an existing file's `# budget` line, or write
   `# budget: large (xhigh)` when creating a new file.
4. **One proposal per role.** Build the table in this order:
   - `inherit-parent` and `auto` are always valid saved choices and stay as-is;
   - a saved choice whose route still exists stays (subject to the budget
     step below if asked);
   - a saved choice whose route is gone is shown as `route missing`, with a
     replacement offered;
   - a role with no choice gets the route of its default's family when one
     exists (`opus-*`, `fable-*`, `gemini-*`, mapped as in Route names);
   - every other role gets a suggestion from the route descriptions: a worker
     or implementation route for implementation, bug-fix, hillclimb and swarm;
     a reasoning or review route for perf-issue, judgment and prose; a
     different route per panel seat for panel roles (`arena runners`,
     `interrogate reviewers`) when there are enough; for `arena cross-judge
     pool` (not a panel — Arena runs one judge, the first candidate from a
     vendor other than the parent's), suggest candidates from vendors other
     than the parent's in preference order. Mark each suggestion `suggested`.

   If step 3 asked for a budget, apply each role's target effort to every
   concrete route in the table — saved choices, defaults, and panel/pool
   entries alike: keep the family and the seat, and pick that family's
   highest-effort route at or below the role's target, else mark it as needing
   a choice. `inherit-parent`, `auto`, and route names with no effort token do
   not move.
   With no answer possible (cron, one-shot), suggested values stay
   `inherit-parent`.
5. **One confirmation.** Show the table and ask with one `clarify`: accept,
   change named roles, or cancel.
   - Cancel / no: write nothing, leave any existing
     `$HERMES_HOME/pstack-models.md` unchanged, change no config, and stop.
   - When `delegation.backend` is not `model_map`, the same question says that
     accepting also runs `hermes config set delegation.backend model_map`. When
     `delegation.backend` is already `model_map`, do not mention activating it.
   - Never change `delegation.backends.model_map.default`, or remove or replace
     a stored route, without a separate yes.

   Before writing, check every value and every list entry: it must be a
   configured route name, `inherit-parent` or `auto`. If one is not, show it
   with the available choices and ask again; never write an unknown name.
6. **Write.** Overwrite `$HERMES_HOME/pstack-models.md` as plain text with no
   frontmatter (no `---` block, `description` or `alwaysApply`): these two
   comment lines, the `# defaults: 3` line, the `# budget` line, then one line
   per role, each value a route name, `inherit-parent` or `auto`.

   ```
   # pstack model configuration. One line per role. Delete a line to fall back to the skill default.
   # `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit `option` on delegate_task). Alias entries in a panel list still count toward its fan-out.
   ```

   Never write these lines into a project's `AGENTS.md`. Say once that routes
   and roles take effect in sessions started after this one, with no rerun.

Never install a plugin, add routes, or change `delegation.*` or any Hermes
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
