---
name: azure-devops-work-items
description: Create, query, annotate, and link Azure DevOps work items (cloud + on-prem) via the azdo tools.
---

# Azure DevOps work items

Use this skill to drive Azure DevOps work items and repositories against either
**Services (cloud, `https://dev.azure.com/{org}`)** or **Server (on-prem TFS
collection)**. Reach for it when the task is: create a Bug/Task/Story, list or
search work items, comment, tag, assign someone, change state (close/resolve),
or attach a commit / PR / branch / file / URL to a work item. Requires the
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

## Surfaces

The same ten operations are exposed three ways, all reading the env vars above:

- **CLI:** `devops-utils azdo {repos,list,search,get,create,update,comment,tag,link,attach}`
- **MCP tools:** `azdo_*` — served by `devops-utils-mcp` (requires the `mcp` extra).
- **Python / agent callables:** `from devops_utils.agent.tools import azdo_*`.

Core logic lives in `src/devops_utils/core/azure_devops/` (`client.py`,
`workitems.py`, `repos.py`) and is surface-agnostic.

## Operations at a glance

| agent callable | CLI | key typed params |
| --- | --- | --- |
| `azdo_list_repositories` | `azdo repos` | `project: str \| None` |
| `azdo_list_work_items` | `azdo list` | `project: str`, `states/types: list[str] \| None`, `assigned_to`, `top: int` |
| `azdo_search_work_items` | `azdo search` | `project`, `text`, `states/types`, `top` |
| `azdo_get_work_item` | `azdo get` | `work_item_id: int` |
| `azdo_create_work_item` | `azdo create` | `project`, `work_item_type`, `title`, `description`, `tags`, `area_path`, `iteration_path`, `assigned_to` |
| `azdo_update_work_item` | `azdo update` | `work_item_id`, `state`, `assigned_to`, `title`, `description` |
| `azdo_comment_work_item` | `azdo comment` | `work_item_id: int`, `text: str` |
| `azdo_set_work_item_tags` | `azdo tag` | `work_item_id`, `tags: list[str]`, `mode: "add" \| "replace"` |
| `azdo_add_work_item_link` | `azdo link` | `work_item_id`, `kind`, `value`, `project`, `repo`, `comment` |
| `azdo_add_work_item_attachment` | `azdo attach` | `work_item_id`, `file_path`, `comment` |

## Operations reference

Signatures below match `src/devops_utils/agent/tools.py` verbatim. Every
work-item op returns a **trimmed** dict (see *Return shape*).

### List repositories

```python
azdo_list_repositories(project: str | None = None) -> list[dict]
```

`project` optional — omit to list org-wide. Returns
`{id, name, project, default_branch, web_url}` dicts. Use it to get the `repo`
name/id needed by commit/PR/branch links.

CLI: `devops-utils azdo repos [--project NAME]`

### List work items

```python
azdo_list_work_items(
    project: str,
    states: list[str] | None = None,   # e.g. ["Active", "New"]
    types: list[str] | None = None,    # e.g. ["Bug", "Task"]
    assigned_to: str | None = None,    # email or display name
    top: int = 50,
) -> list[dict]
```

Backed by a WIQL query ordered by `System.ChangedDate DESC`.

CLI: `devops-utils azdo list --project NAME [--state S ...] [--type T ...] [--assigned-to WHO] [--top N]`
(`--state`/`--type` are repeatable.)

### Search work items

```python
azdo_search_work_items(
    project: str,
    text: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    top: int = 50,
) -> list[dict]
```

Matches `text` against title **and** description via WIQL `CONTAINS`.

CLI: `devops-utils azdo search --project NAME "TEXT" [--state S ...] [--type T ...] [--top N]`

### Get one work item

```python
azdo_get_work_item(work_item_id: int) -> dict
```

CLI: `devops-utils azdo get WORK_ITEM_ID`

### Create a work item

```python
azdo_create_work_item(
    project: str,
    work_item_type: str,               # see "Work-item type" below
    title: str,
    description: str | None = None,    # HTML
    tags: list[str] | None = None,     # see "Tags"
    area_path: str | None = None,
    iteration_path: str | None = None,
    assigned_to: str | None = None,    # see "Assigning users"
) -> dict
```

CLI: `devops-utils azdo create --project NAME --type TYPE --title "T" [--description H] [--tag X ...] [--area-path P] [--iteration-path P] [--assigned-to WHO]`
(`--tag` is repeatable.)

**Work-item type** — `work_item_type` is a free-form string sent as
`$WorkItemType` to the REST API; the valid set depends on the project's process
template. Common values: `Bug`, `Task`, `User Story`, `Feature`, `Epic`,
`Issue`. On Agile/Scrum/CMMI processes the names differ (e.g. CMMI uses
`Requirement` instead of `User Story`). If a create fails with an unknown-type
error, list an existing item with `azdo_list_work_items` to see the `type`
values the project actually uses.

### Update a work item (state / assignee / title / description)

```python
azdo_update_work_item(
    work_item_id: int,
    state: str | None = None,          # e.g. "Active", "Resolved", "Closed"
    assigned_to: str | None = None,    # email or display name
    title: str | None = None,
    description: str | None = None,    # HTML
) -> dict
```

Pass only the fields to change; giving none raises `ValueError`. Use it to
**close/resolve** (`state="Closed"` — valid state names are
process-template-specific: Agile uses `Closed`, Scrum `Done`, some templates
`Resolved`; check an existing item's `state` if a transition is rejected) and to
**reassign** an existing item.

CLI: `devops-utils azdo update WORK_ITEM_ID [--state S] [--assigned-to WHO] [--title T] [--description H]`

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
{"id", "type", "title", "state", "assigned_to", "tags", "url"}
```

`list`/`search` return a `list` of these; `get`/`create`/`comment`/`tag`/`link`/
`attach` return a single one. `azdo_list_repositories` returns its own
`{id, name, project, default_branch, web_url}` shape.

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
separate-host APIs: comments use the `System.History` field and search uses WIQL
`CONTAINS` (no Search extension). If an old server rejects the API version,
lower `AZURE_DEVOPS_API_VERSION` (default `7.1`).
