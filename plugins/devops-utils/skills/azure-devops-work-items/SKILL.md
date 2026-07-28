---
name: azure-devops-work-items
description: Create, query, annotate, and link Azure DevOps work items, builds, and PR comments (cloud + on-prem) via the azdo tools.
---

# Azure DevOps work items

Use this skill to drive Azure DevOps work items and repositories against either
**Services (cloud, `https://dev.azure.com/{org}`)** or **Server (on-prem TFS
collection)**. Reach for it when the task is: create a Bug/Task/Story, list or
search work items, comment, tag, assign someone, change state (close/resolve),
attach a commit / PR / branch / build / file / URL to a work item, list or
inspect builds, tag a build, or comment on a pull request. Requires the
`azure` extra (`httpx`).

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

## Human-in-the-loop (writes)

All **nine write tools** — `azdo_create_work_item`, `azdo_comment_work_item`,
`azdo_set_work_item_tags`, `azdo_update_work_item`, `azdo_add_work_item_link`,
`azdo_remove_work_item_link`, `azdo_add_work_item_attachment`,
`azdo_tag_build`, `azdo_comment_pull_request` — preview the pending change and
require confirmation before mutating Azure DevOps. Read tools are not gated.

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

- **CLI:** `devops-utils azdo {repos,files,code-search,list,search,get,create,update,comment,tag,link,unlink,attach,definitions,builds,build,timeline,logs,log,build-tag,pr-comment}`
- **MCP tools:** `azdo_*` — served by `devops-utils-mcp` (requires the `mcp` extra).
- **Python / agent callables:** `from devops_utils.agent.tools import azdo_*`.

Core logic lives in `src/devops_utils/core/azure_devops/` (`client.py`,
`workitems.py`, `repos.py`, `builds.py`, `pullrequests.py`) and is
surface-agnostic.

## Operations at a glance

| agent callable | CLI | key typed params |
| --- | --- | --- |
| `azdo_list_repositories` | `azdo repos` | `project: str \| None`, `name_filter: str \| None` |
| `azdo_find_repo_files` | `azdo files` | `project`, `repo`, `path_pattern: str`, `branch`, `top` |
| `azdo_code_search` | `azdo code-search` | `project`, `text`, `repo`, `branch`, `top` |
| `azdo_list_work_items` | `azdo list` | `project: str`, `states/types/tags: list[str] \| None`, `assigned_to` (`"@Me"` ok), `area_path`, `iteration_path`, `top: int` |
| `azdo_search_work_items` | `azdo search` | `project`, `text`, `states/types/tags`, `assigned_to`, `area_path`, `iteration_path`, `top` |
| `azdo_get_work_item` | `azdo get` | `work_item_id: int`, `relations: bool` |
| `azdo_create_work_item` | `azdo create` | `project`, `work_item_type`, `title`, `description`, `tags`, `area_path`, `iteration_path`, `assigned_to`, `parent`, `fields: dict` |
| `azdo_update_work_item` | `azdo update` | `work_item_id`, `state`, `assigned_to`, `title`, `description`, `area_path`, `iteration_path`, `fields: dict` |
| `azdo_comment_work_item` | `azdo comment` | `work_item_id: int`, `text: str` |
| `azdo_set_work_item_tags` | `azdo tag` | `work_item_id`, `tags: list[str]`, `mode: "add" \| "replace"` |
| `azdo_add_work_item_link` | `azdo link` | `work_item_id`, `kind`, `value`, `project`, `repo`, `comment` |
| `azdo_remove_work_item_link` | `azdo unlink` | `work_item_id`, `kind`, `value`, `project`, `repo` |
| `azdo_add_work_item_attachment` | `azdo attach` | `work_item_id`, `file_path`, `comment` |
| `azdo_list_build_definitions` | `azdo definitions` | `project`, `name` (supports `*`), `top` |
| `azdo_list_builds` | `azdo builds` | `project`, `definitions: list[int]`, `branch`, `statuses/results: list[str]`, `top` |
| `azdo_get_build` | `azdo build` | `project: str`, `build_id: int` |
| `azdo_get_build_timeline` | `azdo timeline` | `project`, `build_id` |
| `azdo_list_build_logs` | `azdo logs` | `project`, `build_id` |
| `azdo_get_build_log` | `azdo log` | `project`, `build_id`, `log_id`, `start_line`, `end_line` |
| `azdo_tag_build` | `azdo build-tag` | `project`, `build_id`, `tags: list[str]` |
| `azdo_comment_pull_request` | `azdo pr-comment` | `project`, `repo`, `pull_request_id`, `text`, `thread_id` |

## Operations reference

Signatures below match `src/devops_utils/agent/tools.py` verbatim. Every
work-item op returns a **trimmed** dict (see *Return shape*).

### List repositories

```python
azdo_list_repositories(
    project: str | None = None,
    name_filter: str | None = None,    # case-insensitive substring on repo name
) -> list[dict]
```

`project` optional — omit to list org-wide. Returns
`{id, name, project, default_branch, web_url}` dicts. Use it to get the `repo`
name/id needed by commit/PR/branch links.

CLI: `devops-utils azdo repos [--project NAME] [--name SUBSTR]`

### Find files in a repository

```python
azdo_find_repo_files(
    project: str,
    repo: str,
    path_pattern: str = "*",           # glob vs path or basename, e.g. "*.yml"
    branch: str | None = None,         # defaults to the repo default branch
    top: int = 100,
) -> list[dict]                        # {path, size, commit, url}
```

Git Items API — no Search extension needed, works on cloud and on-prem.

CLI: `devops-utils azdo files --project P --repo R [--pattern '*.yml'] [--branch B] [--top N]`

### Search code content

```python
azdo_code_search(
    project: str,
    text: str,                         # code-search syntax ok: def:Foo, ext:yml
    repo: str | None = None,
    branch: str | None = None,
    top: int = 25,
) -> list[dict]                        # {path, repo, project, matches}
```

Uses the **Search extension** — always present on cloud
(`almsearch.dev.azure.com` is derived automatically); on-prem servers without
the extension get a clear error — fall back to `azdo_find_repo_files`.

CLI: `devops-utils azdo code-search "TEXT" --project P [--repo R] [--branch B] [--top N]`

### List work items

```python
azdo_list_work_items(
    project: str,
    states: list[str] | None = None,   # e.g. ["Active", "New"]
    types: list[str] | None = None,    # e.g. ["Bug", "Task"]
    assigned_to: str | None = None,    # email, display name, or "@Me"
    tags: list[str] | None = None,     # AND semantics: every tag must be present
    area_path: str | None = None,      # matches this node AND everything under it
    iteration_path: str | None = None, # matches this node AND everything under it
    top: int = 50,
) -> list[dict]
```

Backed by a WIQL query ordered by `System.ChangedDate DESC`.
`assigned_to="@Me"` uses the WIQL macro that resolves the identity behind the
token — "assigned to me" without knowing the user's email. "Pending" items are
the non-closed states of the process template (e.g. `["New", "Active"]`).
`area_path`/`iteration_path` filter with WIQL `UNDER` — see
*Area path / iteration path*.

CLI: `devops-utils azdo list --project NAME [--state S ...] [--type T ...] [--assigned-to WHO | --mine] [--tag X ...] [--area-path P] [--iteration-path P] [--top N]`
(`--state`/`--type`/`--tag` are repeatable; `--mine` = `--assigned-to @Me`.)

### Search work items

```python
azdo_search_work_items(
    project: str,
    text: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    assigned_to: str | None = None,    # email, display name, or "@Me"
    tags: list[str] | None = None,
    area_path: str | None = None,
    iteration_path: str | None = None,
    top: int = 50,
) -> list[dict]
```

Matches `text` against title **and** description via WIQL `CONTAINS`; the
other filters compose the same way as `azdo_list_work_items`.

CLI: `devops-utils azdo search --project NAME "TEXT" [--state S ...] [--type T ...] [--assigned-to WHO | --mine] [--tag X ...] [--area-path P] [--iteration-path P] [--top N]`

### Get one work item

```python
azdo_get_work_item(work_item_id: int, relations: bool = False) -> dict
```

With `relations=True` the result carries a `relations` list of
`{kind, target, ...}` dicts — work-item kinds (`parent`, `child`,
`predecessor`, `successor`, `work_item`) carry the target work-item id;
`hyperlink`/`attachment`/`commit`/`pull_request`/`branch`/`build` carry the URL.

CLI: `devops-utils azdo get WORK_ITEM_ID [--relations]`

### Create a work item

```python
azdo_create_work_item(
    project: str,
    work_item_type: str,               # see "Work-item type" below
    title: str,
    description: str | None = None,    # HTML
    tags: list[str] | None = None,     # see "Tags"
    area_path: str | None = None,      # see "Area path / iteration path"
    iteration_path: str | None = None,
    assigned_to: str | None = None,    # see "Assigning users"
    parent: int | None = None,         # create directly under this work item
    fields: dict | None = None,        # see "Custom fields"
) -> dict
```

CLI: `devops-utils azdo create --project NAME --type TYPE --title "T" [--description H] [--tag X ...] [--area-path P] [--iteration-path P] [--assigned-to WHO] [--parent ID] [--field NAME=VALUE ...]`
(`--tag` and `--field` are repeatable.)

**Work-item type** — `work_item_type` is a free-form string sent as
`$WorkItemType` to the REST API; the valid set depends on the project's process
template. Common values: `Bug`, `Task`, `User Story`, `Feature`, `Epic`,
`Issue`. On Agile/Scrum/CMMI processes the names differ (e.g. CMMI uses
`Requirement` instead of `User Story`). If a create fails with an unknown-type
error, list an existing item with `azdo_list_work_items` to see the `type`
values the project actually uses.

### Work-item hierarchy — always Epic → Feature → User Story

**Structure every backlog item this way.** New work is decomposed top-down and
each level is parented to the one above:

```
Epic            business outcome / initiative, spans releases
└── Feature     shippable capability delivering part of the Epic
    └── User Story   user-visible increment, estimable, fits in a sprint
        └── Task / Bug   implementation steps and defects (optional leaf)
```

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
  --title "Self-service checkout" -y | jq -r .id)
feature=$(devops-utils azdo create --project Contoso --type Feature \
  --title "Guest checkout" --parent "$epic" -y | jq -r .id)
devops-utils azdo create --project Contoso --type "User Story" \
  --title "As a guest I can pay without an account" --parent "$feature"
```

```python
epic = tools.azdo_create_work_item("Contoso", "Epic", "Self-service checkout")
feature = tools.azdo_create_work_item(
    "Contoso", "Feature", "Guest checkout", parent=epic["id"]
)
story = tools.azdo_create_work_item(
    "Contoso", "User Story",
    "As a guest I can pay without an account", parent=feature["id"],
)
```

### Update a work item (state / assignee / title / description / area / iteration / custom)

```python
azdo_update_work_item(
    work_item_id: int,
    state: str | None = None,          # e.g. "Active", "Resolved", "Closed"
    assigned_to: str | None = None,    # email or display name
    title: str | None = None,
    description: str | None = None,    # HTML
    area_path: str | None = None,      # move between Boards areas
    iteration_path: str | None = None, # move between sprints
    fields: dict | None = None,        # see "Custom fields"
) -> dict
```

Pass only the fields to change; giving none raises `ValueError`. Use it to
**close/resolve** (`state="Closed"` — valid state names are
process-template-specific: Agile uses `Closed`, Scrum `Done`, some templates
`Resolved`; check an existing item's `state` if a transition is rejected),
**reassign** an existing item, or **move it** to another area/sprint.

CLI: `devops-utils azdo update WORK_ITEM_ID [--state S] [--assigned-to WHO] [--title T] [--description H] [--area-path P] [--iteration-path P] [--field NAME=VALUE ...]`

### Area path / iteration path

`System.AreaPath` and `System.IterationPath` are Azure Boards' two
classification trees — area = which team/component owns the item, iteration =
which sprint it's in. Paths are backslash-separated and rooted at the project
name, e.g. `Contoso\Team A` / `Contoso\Sprint 3`.

- **On `create`/`update`** they **set** the field, i.e. move the item.
- **On `list`/`search`** they **filter** using WIQL `UNDER`, matching the given
  node *and everything nested under it* — `area_path="Contoso\\Team A"` also
  returns items in `Contoso\Team A\Sub-team`. That is usually what you want;
  there is no exact-node-only variant.

```bash
# everything the Payments team has open in the current sprint
devops-utils azdo list --project Contoso \
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' \
  --state Active --state New

# move an item to another sprint
devops-utils azdo update 1421 --iteration-path 'Contoso\Sprint 4'
```

An invalid path is rejected by the server — list an existing item and read its
values if a write fails with a classification-node error.

### Custom fields

`azdo_create_work_item` and `azdo_update_work_item` take a `fields` dict
(CLI: repeatable `--field NAME=VALUE`) to set **any** work-item field the named
parameters don't cover — process-specific fields like
`Microsoft.VSTS.Common.Priority` or org-defined ones like `Custom.RiskLevel`:

```python
tools.azdo_create_work_item(
    "Contoso", "Bug", "Login page 500s under load",
    fields={"Microsoft.VSTS.Common.Priority": 1, "Custom.RiskLevel": "High"},
)
tools.azdo_update_work_item(1421, fields={"Custom.RiskLevel": "Low"})
```

```bash
devops-utils azdo update 1421 --field Custom.RiskLevel=Low
```

Keys must be the field's **reference name** (`Custom.RiskLevel`), not its
display label ("Risk Level") — reference names are process/org specific, so
check the project's process configuration if a write is rejected. Values pass
through as-is (string/number/bool). `fields` is applied *after* the named
params, so a key targeting e.g. `System.AreaPath` overrides `area_path`.

### Comment on a work item

```python
azdo_comment_work_item(work_item_id: int, text: str) -> dict
```

Written via the `System.History` field (works on every server, unlike the
preview-only `/comments` endpoint).

CLI: `devops-utils azdo comment WORK_ITEM_ID "TEXT"`

### Tags

Two ways to set tags:

- **At create time** — pass `tags=["urgent", "regression"]` to
  `azdo_create_work_item`.
- **After the fact** — `azdo_set_work_item_tags`:

```python
azdo_set_work_item_tags(
    work_item_id: int,
    tags: list[str],
    mode: str = "add",                 # "add" | "replace"
) -> dict
```

`mode="add"` (default) **merges** with existing tags, de-duplicating
case-insensitively; `mode="replace"` **overwrites** the whole tag set. Any
other value raises `ValueError`. Tags are stored joined by `"; "`.

CLI: `devops-utils azdo tag WORK_ITEM_ID TAG [TAG ...] [--mode add|replace]`

### Assigning users

Set the assignee via the `assigned_to` parameter — it accepts an **email** or a
**display name** and maps to `System.AssignedTo`:

- On create: `azdo_create_work_item(..., assigned_to="dev@contoso.com")`.
- On an existing item: `azdo_update_work_item(id, assigned_to="dev@contoso.com")`.
- CLI: `--assigned-to dev@contoso.com` (on `create` and `update`).

On `list`/`search`, `assigned_to` is a *filter*, not a mutation.

### Links / references

```python
azdo_add_work_item_link(
    work_item_id: int,
    kind: str,                         # see table
    value: str,
    project: str | None = None,        # required for commit/pull_request/branch
    repo: str | None = None,           # required for commit/pull_request/branch
    comment: str | None = None,
) -> dict
```

One entry point covers every reference kind (`LINK_KINDS` in `workitems.py`):

| kind | needs | `value` is | relation |
| --- | --- | --- | --- |
| `commit` | `project` + `repo` | commit SHA | `ArtifactLink` `vstfs:///Git/Commit/...` |
| `pull_request` | `project` + `repo` | PR id | `ArtifactLink` `vstfs:///Git/PullRequestId/...` |
| `branch` | `project` + `repo` | branch name | `ArtifactLink` `vstfs:///Git/Ref/...GB{branch}` |
| `build` | — | build id | `ArtifactLink` `vstfs:///Build/Build/{id}` |
| `work_item` | — | target work-item id | `System.LinkTypes.Related` |
| `parent` | — | target work-item id | `System.LinkTypes.Hierarchy-Reverse` |
| `child` | — | target work-item id | `System.LinkTypes.Hierarchy-Forward` |
| `predecessor` | — | target work-item id | `System.LinkTypes.Dependency-Reverse` |
| `successor` | — | target work-item id | `System.LinkTypes.Dependency-Forward` |
| `hyperlink` | — | raw URL | `Hyperlink` |

Hierarchy and dependency kinds are read from the item being linked:
`parent` makes `value` the parent of `work_item_id`; `predecessor` marks
`work_item_id` as **blocked by** `value` (use these for wayfinder-style
dependency maps).

An unknown `kind`, or a repo kind missing `project`/`repo`, raises `ValueError`.

CLI: `devops-utils azdo link WORK_ITEM_ID --kind KIND --value V [--project P] [--repo R] [--comment C]`

### Remove a link

```python
azdo_remove_work_item_link(
    work_item_id: int,
    kind: str,                         # same kinds as azdo_add_work_item_link
    value: str,
    project: str | None = None,        # required for commit/pull_request/branch
    repo: str | None = None,           # required for commit/pull_request/branch
) -> dict
```

Removes a reference using the same kind/value pairs as `link` — e.g.
re-parenting is `unlink --kind parent --value <old>` then
`link --kind parent --value <new>`. Raises `ValueError` if no matching relation
exists.

CLI: `devops-utils azdo unlink WORK_ITEM_ID --kind KIND --value V [--project P] [--repo R]`

### Builds (definitions / list / get / timeline / logs / tag / link)

```python
azdo_list_build_definitions(
    project: str,
    name: str | None = None,               # name filter, supports * wildcards
    top: int = 25,
) -> list[dict]                            # {id, name, path, type, queue_status, web_url}

azdo_list_builds(
    project: str,
    definitions: list[int] | None = None,  # pipeline definition ids
    branch: str | None = None,             # "main" expands to refs/heads/main
    statuses: list[str] | None = None,     # inProgress/completed/notStarted/...
    results: list[str] | None = None,      # succeeded/partiallySucceeded/failed/canceled
    top: int = 25,
) -> list[dict]

azdo_get_build(project: str, build_id: int) -> dict

azdo_get_build_timeline(project: str, build_id: int) -> list[dict]
# ordered records: {id, parent_id, type, name, state, result, log_id,
#                   start_time, finish_time, issues}

azdo_list_build_logs(project: str, build_id: int) -> list[dict]  # {id, line_count}

azdo_get_build_log(
    project: str, build_id: int, log_id: int,
    start_line: int | None = None, end_line: int | None = None,
) -> str

azdo_tag_build(project: str, build_id: int, tags: list[str]) -> list[str]
```

Builds return `{id, number, definition, status, result, branch, requested_for,
queue_time, finish_time, web_url}`. Use the `id` to reference a build from a
work item — `azdo_add_work_item_link(wi, "build", "<build-id>")` needs no
`project`/`repo`. Builds have **no comments**; `azdo_tag_build` (tags) is the
annotation mechanism and returns the resulting tag list.

**Failure diagnosis pattern** (cheapest first): timeline → the `failed`
records' `issues` usually name the error; if log context is needed, take that
record's `log_id`, read `line_count` from `azdo_list_build_logs`, and **tail**
with `azdo_get_build_log(..., start_line=line_count - 200)` rather than
fetching the whole log.

CLI: `devops-utils azdo definitions --project P [--name 'CI*'] [--top N]`,
`devops-utils azdo builds --project P [--definition ID ...] [--branch B] [--status S ...] [--result R ...] [--top N]`,
`devops-utils azdo build BUILD_ID --project P`,
`devops-utils azdo timeline BUILD_ID --project P`,
`devops-utils azdo logs BUILD_ID --project P`,
`devops-utils azdo log BUILD_ID LOG_ID --project P [--start-line N] [--end-line N]`,
`devops-utils azdo build-tag BUILD_ID TAG [TAG ...] --project P`

### Comment on a pull request

```python
azdo_comment_pull_request(
    project: str,
    repo: str,
    pull_request_id: int,
    text: str,
    thread_id: int | None = None,      # reply to an existing thread
) -> dict                              # {thread_id, comment_id, status}
```

Without `thread_id` a new (active) comment thread is created; with it the
comment is a reply on that thread. **Commits cannot be commented on** — Azure
DevOps has no documented REST endpoint for commit comments; comment on the PR
containing the commit, or on the work item that links it.

CLI: `devops-utils azdo pr-comment PR_ID "TEXT" --project P --repo R [--thread N]`

### Attach a file

```python
azdo_add_work_item_attachment(
    work_item_id: int,
    file_path: str,                    # local path
    comment: str | None = None,
) -> dict
```

Two-step: uploads the file, then attaches it as an `AttachedFile` relation.

CLI: `devops-utils azdo attach WORK_ITEM_ID FILE_PATH [--comment C]`

## Return shape

Every work-item op returns a trimmed dict (`_trim` in `workitems.py`):

```python
{"id", "type", "title", "state", "assigned_to", "tags",
 "area_path", "iteration_path", "url"}
```

`list`/`search` return a `list` of these; `get`/`create`/`comment`/`tag`/`link`/
`unlink`/`attach` return a single one. `azdo_list_repositories` returns its own
`{id, name, project, default_branch, web_url}` shape, builds return
`{id, number, definition, status, result, branch, requested_for, queue_time,
finish_time, web_url}`, `azdo_tag_build` a plain tag list, and
`azdo_comment_pull_request` `{thread_id, comment_id, status}`.

## Worked example: create → assign → tag → comment → link

**CLI**

```bash
devops-utils azdo create \
  --project Contoso --type Bug \
  --title "Login page 500s under load" \
  --description "<p>Repro at 200 rps.</p>" \
  --assigned-to dev@contoso.com --tag urgent --tag regression
# => {"id": 1421, ...}

devops-utils azdo tag 1421 needs-review --mode add
devops-utils azdo comment 1421 "Root cause: connection pool exhaustion."
devops-utils azdo link 1421 --kind pull_request --value 88 \
  --project Contoso --repo web-app --comment "Fix"
```

**Python / agent**

```python
from devops_utils.agent import tools

wi = tools.azdo_create_work_item(
    "Contoso", "Bug", "Login page 500s under load",
    description="<p>Repro at 200 rps.</p>",
    assigned_to="dev@contoso.com",
    tags=["urgent", "regression"],
)
tools.azdo_set_work_item_tags(wi["id"], ["needs-review"], mode="add")
tools.azdo_comment_work_item(wi["id"], "Root cause: connection pool exhaustion.")
tools.azdo_add_work_item_link(
    wi["id"], "pull_request", "88",
    project="Contoso", repo="web-app", comment="Fix",
)
```

## On-prem notes

For maximum Server (on-prem) compatibility the tools avoid preview-only or
separate-host APIs: comments use the `System.History` field and work-item
search uses WIQL `CONTAINS` (no Search extension). The one exception is
`azdo_code_search`, which needs the Search extension — on servers without it
the tool errors clearly and `azdo_find_repo_files` is the fallback. If an old
server rejects the API version, lower `AZURE_DEVOPS_API_VERSION` (default `7.1`).
