---
name: azure-devops-work-items
description: Creates, updates, comments on, tags, and links Azure DevOps work items, and tags builds and comments on pull requests (cloud Services and on-prem Server) through the devops-utils azdo CLI or MCP tools. Use when the user wants to change Azure DevOps state — create an Epic, Feature, User Story, Task or Bug; assign, re-state, schedule, or move one between areas/sprints; attach a commit, PR, branch, build, file or URL; or apply a bulk backlog plan. For read-only status questions prefer azure-devops-research.
---

# Azure DevOps work items

Use this skill to drive Azure DevOps work items and repositories against either
**Services (cloud, `https://dev.azure.com/{org}`)** or **Server (on-prem TFS
collection)**. Requires the `azure` extra (`httpx`).

## Contents

- Configuration · Windows · Human-in-the-loop · Surfaces
- Operations at a glance · Shell-neutral output
- Work-item hierarchy (Epic → Feature → User Story)
- Return shape · On-prem notes · Reference files

## Configuration (no machine credentials)

Nothing is read from `az` CLI, credential files, or the Windows credential
store. Config — and the token — come only from environment variables, so a
secret never flows through tool arguments or logs (see
`AzureDevOpsClient.from_env` in `core/azure_devops/client.py`).

| Variable | Required | Notes |
| --- | --- | --- |
| `AZURE_DEVOPS_ORG_URL` | yes | Cloud `https://dev.azure.com/{org}` or on-prem `https://server/tfs/{collection}` |
| `AZURE_DEVOPS_TOKEN` | yes | Bearer token or PAT |
| `AZURE_DEVOPS_AUTH_SCHEME` | no | `bearer` (default) → `Authorization: Bearer`; `pat` → `Authorization: Basic base64(":"+token)` |
| `AZURE_DEVOPS_API_VERSION` | no | Default `7.1`; lower it for older on-prem servers |
| `DEVOPS_UTILS_SKIP_CONFIRMATION` | no | Truthy (`1`/`true`/`yes`/`on`) bypasses the write confirmation on both the MCP server and the CLI, for unattended automation (see *Human-in-the-loop*) |

### Where the variables come from

Real environment variables win. Otherwise the CLI and the MCP server load the
**first existing** env file of: the path in `DEVOPS_UTILS_ENV_FILE`,
`./.env.devops-utils` (project — keep it out of git), `~/.devops-utils.env`
(user). `devops-utils setup env` writes a commented `.example` scaffold to copy.
Files are never merged, and an org URL from a file is only used together with
the token from that same file.

If a call fails with *Missing required environment variable(s)*, tell the user
which of the two is missing and where to put it — never ask them to paste the
token into the chat.

## Windows

The CLI and MCP server run natively on Windows (CI runs the test suite on
`windows-latest`). The commands in this skill and its references run unchanged
in PowerShell 7 (`pwsh`), Windows PowerShell 5.1, and `cmd`, except for the
parts that are shell syntax:

| Need | bash | PowerShell |
| --- | --- | --- |
| capture an id | `id=$(devops-utils azdo create … -y -o id)` | `$id = devops-utils azdo create … -y -o id` |
| use it | `--parent "$id"` | `--parent $id` |
| continue a line | trailing `\` | trailing `` ` `` |
| set a var for this session | `export AZURE_DEVOPS_TOKEN=…` | `$env:AZURE_DEVOPS_TOKEN = '…'` |
| area / iteration path | `'Contoso\Payments'` | `'Contoso\Payments'` (single quotes are literal in both) |

- **Prefer the env file over `setx`/`$env:`** — Claude Desktop and Claude Code
  start the MCP server without your PowerShell session's variables, and `setx`
  only reaches processes started afterwards.
- **Never pipe to `jq`** — it is rarely installed on Windows. Use
  `-o id` / `--select` (below). For anything richer in PowerShell,
  `devops-utils azdo … | ConvertFrom-Json` works; in Windows PowerShell 5.1 run
  `[Console]::OutputEncoding = [Text.UTF8Encoding]::new()` first, or non-ASCII
  titles arrive garbled.
- Paths for `azdo attach` / `azdo apply` may use `\` or `/`.

## Human-in-the-loop (writes)

All **ten write tools** — `azdo_create_work_item`, `azdo_comment_work_item`,
`azdo_set_work_item_tags`, `azdo_update_work_item`, `azdo_add_work_item_link`,
`azdo_remove_work_item_link`, `azdo_add_work_item_attachment`,
`azdo_tag_build`, `azdo_comment_pull_request`, `azdo_apply_plan` — preview the
pending change and require confirmation before mutating Azure DevOps. Read
tools are not gated. For batches, prefer `azdo_apply_plan` / `azdo apply`
(see [reference/bulk-apply.md](reference/bulk-apply.md)): one review window
and one confirmation cover the whole batch instead of a prompt per item.

- **MCP server:** approval via MCP **elicitation**. Declining returns a
  `cancelled` status and writes nothing. If the client can't prompt
  (elicitation unsupported / non-interactive) the write is **blocked** unless
  `DEVOPS_UTILS_SKIP_CONFIRMATION` is truthy.
- **CLI:** the equivalent commands (`create`, `comment`, `tag`, `update`,
  `link`, `unlink`, `attach`, `build-tag`, `pr-comment`) print the pending
  change and prompt. `--yes`/`-y` skips the prompt, `--dry-run` previews
  without applying, and `DEVOPS_UTILS_SKIP_CONFIRMATION` also skips it.
- **Python callables** (`devops_utils.agent.tools`) are ungated — the caller
  drives them directly.

## Surfaces

The same operations are exposed three ways, all reading the env vars above:

- **CLI:** `devops-utils azdo {repos,files,code-search,list,search,get,create,update,comment,tag,link,unlink,attach,apply,definitions,builds,build,timeline,logs,log,build-tag,pr-comment}`
- **MCP tools:** `azdo_*` — served by `devops-utils-mcp` (requires the `mcp` extra).
- **Python / agent callables:** `from devops_utils.agent.tools import azdo_*`.

Core logic lives in `src/devops_utils/core/azure_devops/` (`client.py`,
`workitems.py`, `repos.py`, `builds.py`, `pullrequests.py`) and is
surface-agnostic.

### Running the CLI without installing it (uvx)

Assume `uv` is available. If `devops-utils` is not on `PATH` — or you don't
want it installed — every `devops-utils …` command in this skill runs unchanged
behind `uvx`, which fetches the package and its extra per invocation:

```bash
uvx --from "devops-utils[azure]" devops-utils azdo list --project Contoso --mine
uvx --from "devops-utils[mcp]" devops-utils-mcp        # the MCP server itself
```

The extra is mandatory: `azdo` needs `[azure]`, the MCP server needs `[mcp]`,
`[all]` covers everything. Pin it (`"devops-utils[azure]==0.8.0"`) when a run
has to be reproducible. Examples below are written bare (`devops-utils azdo …`)
— prefix them with `uvx --from "devops-utils[azure]"` when the command is not
installed. `uv tool install "devops-utils[all]"` makes the bare form work
permanently.

## Operations at a glance

| agent callable | CLI | key typed params |
| --- | --- | --- |
| `azdo_list_repositories` | `azdo repos` | `project: str \| None`, `name_filter: str \| None` |
| `azdo_find_repo_files` | `azdo files` | `project`, `repo`, `path_pattern: str`, `branch`, `top` |
| `azdo_code_search` | `azdo code-search` | `project`, `text`, `repo`, `branch`, `top` |
| `azdo_list_work_items` | `azdo list` | `project: str`, `states/types/tags: list[str] \| None`, `assigned_to` (`"@Me"` ok), `parent: int \| None`, `area_path`, `iteration_path`, `top: int` |
| `azdo_search_work_items` | `azdo search` | `project`, `text`, `states/types/tags`, `assigned_to`, `parent`, `area_path`, `iteration_path`, `top` |
| `azdo_get_work_item` | `azdo get` | `work_item_id: int`, `relations: bool`, `full: bool` |
| `azdo_create_work_item` | `azdo create` | `project`, `work_item_type`, `title`, `description`, `tags`, `area_path`, `iteration_path`, `assigned_to`, `parent`, `fields: dict` (dates/effort/priority — see reference/fields-and-scheduling.md) |
| `azdo_update_work_item` | `azdo update` | `work_item_id`, `state`, `assigned_to`, `title`, `description`, `area_path`, `iteration_path`, `fields: dict` (dates/effort/priority — see reference/fields-and-scheduling.md) |
| `azdo_comment_work_item` | `azdo comment` | `work_item_id: int`, `text: str` |
| `azdo_set_work_item_tags` | `azdo tag` | `work_item_id`, `tags: list[str]`, `mode: "add" \| "replace"` |
| `azdo_add_work_item_link` | `azdo link` | `work_item_id`, `kind`, `value`, `project`, `repo`, `comment` |
| `azdo_remove_work_item_link` | `azdo unlink` | `work_item_id`, `kind`, `value`, `project`, `repo` |
| `azdo_add_work_item_attachment` | `azdo attach` | `work_item_id`, `file_path`, `comment` |
| `azdo_apply_plan` | `azdo apply` | `plan: dict \| str` (YAML/JSON), `stop_on_error: bool` |
| `azdo_list_build_definitions` | `azdo definitions` | `project`, `name` (supports `*`), `top` |
| `azdo_list_builds` | `azdo builds` | `project`, `definitions: list[int]`, `branch`, `statuses/results: list[str]`, `top` |
| `azdo_get_build` | `azdo build` | `project: str`, `build_id: int` |
| `azdo_get_build_timeline` | `azdo timeline` | `project`, `build_id` |
| `azdo_list_build_logs` | `azdo logs` | `project`, `build_id` |
| `azdo_get_build_log` | `azdo log` | `project`, `build_id`, `log_id`, `start_line`, `end_line` |
| `azdo_tag_build` | `azdo build-tag` | `project`, `build_id`, `tags: list[str]` |
| `azdo_comment_pull_request` | `azdo pr-comment` | `project`, `repo`, `pull_request_id`, `text`, `thread_id` |

## Shell-neutral output (`--output` / `--select`)

Every `azdo` command that prints JSON also takes:

- `-o id` — print only the `id` (one per line for lists). Use it to capture a
  new item's id for the next command.
- `--select PATH` (repeatable) — keep only that `/`-separated path; dotted
  field names need no quoting: `--select fields/Microsoft.VSTS.Scheduling.TargetDate`.
  One path prints the bare value, several print an object keyed by each
  path's last segment; lists are projected per item.
- `-o raw` — print `--select` values unquoted, one per line.

```bash
devops-utils azdo list --project Contoso --mine -o id
devops-utils azdo get 1400 --full --select fields/System.State --select title
devops-utils azdo get 1400 --full --select fields/Microsoft.VSTS.Scheduling.TargetDate -o raw
```

## Work-item hierarchy — always Epic → Feature → User Story

**Structure every backlog item this way.** New work is decomposed top-down and
each level is parented to the one above:

```
Epic            business outcome / initiative, spans releases
└── Feature     value delivered to the end user — a capability they can use
    └── User Story   one increment of end-user value, estimable, fits in a sprint
        └── Task / Bug   implementation steps and defects (optional leaf)
```

**Features and User Stories are value delivered to the end user.** They
describe what someone using the product can now do and why it matters to
them — never how the team built it. Write them that way:

- **Title from the user's side.** A Feature names the capability the user gets
  ("Guest checkout"), not the component built ("Payment service refactor"). A
  User Story follows *As a <user>, I can <action> so that <benefit>* — or at
  least names the user-visible outcome.
- **Description = the value.** Who benefits, what they can do now that they
  couldn't before, and why it matters. Put acceptance criteria in
  user-observable terms (`Microsoft.VSTS.Common.AcceptanceCriteria`).
- **Technical work is a Task, not a story.** Refactors, CI, dependency bumps,
  test scaffolding, and infrastructure are Tasks under the User Story whose
  value they enable. If a request describes only technical work, ask which
  user-facing outcome it serves and parent it there; don't invent a Feature or
  Story to hold it.
- **The Epic is an outcome too** — the business or user result the Features
  add up to ("Customers can check out without help"), not a component or a
  "<repo> backlog" bucket.

**Value check — before proposing any Feature or User Story, answer:**

1. Who is the user, and what can they do afterwards that they couldn't before?
2. Is the benefit stated (the *so that …*)?
3. Are the acceptance criteria observable by that user — not "code merged",
   "tests pass", or "endpoint added"?

If any answer is "nobody" or "internal only", it is a Task under the story it
enables; ask the user which outcome it serves instead of creating the
Feature/Story.

Rules:

- **Never create an orphan** Feature or User Story. Pass `parent=<id>` on
  `azdo_create_work_item` (CLI `--parent ID`), or fix an existing item with
  `azdo_add_work_item_link(id, "parent", "<parent-id>")`.
- **Ask for the missing level, don't skip it.** If the user asks for a story and
  names no Feature, first look for one — `azdo_search_work_items(project, text,
  types=["Feature"])` — and only create the Feature (itself parented to an Epic)
  when nothing fits. Same one level up for Feature → Epic. Every create is
  confirmation-gated, so propose the whole chain in one preview.
- **Create top-down**, capturing each id: Epic → Feature (`parent=epic`) →
  User Story (`parent=feature`) → Task/Bug (`parent=story`).
- **Bugs** hang off the User Story whose behaviour they break; a bug with no
  story goes under the Feature.
- **Verify** with `azdo_get_work_item(id, relations=True)` — the `parent` /
  `child` relations should reproduce the chain above.
- **Type names per process template** — the *shape* is fixed, the labels are
  not: Agile `Epic → Feature → User Story → Task`, Scrum
  `Epic → Feature → Product Backlog Item → Task`, CMMI
  `Epic → Feature → Requirement → Task`, Basic `Epic → Issue → Task` (no
  Feature level). Read an existing item's `type` when unsure, and say which
  mapping you used.

```bash
epic=$(devops-utils azdo create --project Contoso --type Epic \
  --title "Self-service checkout" -y -o id)
feature=$(devops-utils azdo create --project Contoso --type Feature \
  --title "Guest checkout" --parent "$epic" -y -o id)
devops-utils azdo create --project Contoso --type "User Story" \
  --title "As a guest I can pay without an account" --parent "$feature"
```

```powershell
$epic = devops-utils azdo create --project Contoso --type Epic `
  --title "Self-service checkout" -y -o id
$feature = devops-utils azdo create --project Contoso --type Feature `
  --title "Guest checkout" --parent $epic -y -o id
devops-utils azdo create --project Contoso --type "User Story" `
  --title "As a guest I can pay without an account" --parent $feature
```

```python
epic = tools.azdo_create_work_item("Contoso", "Epic", "Self-service checkout")
feature = tools.azdo_create_work_item(
    "Contoso", "Feature", "Guest checkout", parent=epic["id"]
)
story = tools.azdo_create_work_item(
    "Contoso",
    "User Story",
    "As a guest I can pay without an account",
    parent=feature["id"],
)
```

## Return shape

Every work-item op returns a trimmed dict (`_trim` in `workitems.py`):

```python
{
    "id",
    "type",
    "title",
    "state",
    "assigned_to",
    "tags",
    "area_path",
    "iteration_path",
    "url",
}
```

`list`/`search` return a `list` of these; `get`/`create`/`comment`/`tag`/`link`/
`unlink`/`attach` return a single one. `azdo_get_work_item(..., full=True)` adds
`rev` and a `fields` map of every raw field on top — the only way to read
anything the nine keys above drop. `azdo_list_repositories` returns its own
`{id, name, project, default_branch, web_url}` shape, builds return
`{id, number, definition, status, result, branch, requested_for, queue_time,
finish_time, web_url}`, `azdo_tag_build` a plain tag list, and
`azdo_comment_pull_request` `{thread_id, comment_id, status}`.

## On-prem notes

For maximum Server (on-prem) compatibility the tools avoid preview-only or
separate-host APIs: comments use the `System.History` field and work-item
search uses WIQL `CONTAINS` (no Search extension). The one exception is
`azdo_code_search`, which needs the Search extension — on servers without it
the tool errors clearly and `azdo_find_repo_files` is the fallback. If an old
server rejects the API version, lower `AZURE_DEVOPS_API_VERSION` (default `7.1`).

## Reference files

Load only the one the task needs:

- [reference/operations.md](reference/operations.md) — exact signatures and
  CLI flags for repos, files, code search, list, search, get, create, update,
  area/iteration paths, comments, tags, assigning users.
- [reference/fields-and-scheduling.md](reference/fields-and-scheduling.md) —
  custom fields (`--field NAME=VALUE`), start/target/due dates, effort,
  priority, and reading them back.
- [reference/links-and-builds.md](reference/links-and-builds.md) — link /
  unlink kinds (commit, PR, branch, build, parent/child, predecessor,
  hyperlink), builds and failure diagnosis, PR comments, attachments.
- [reference/bulk-apply.md](reference/bulk-apply.md) — the YAML/JSON plan
  format for `azdo apply` / `azdo_apply_plan` (one confirmation per batch).
- [reference/examples.md](reference/examples.md) — end-to-end worked
  examples in Python, bash, and PowerShell.
