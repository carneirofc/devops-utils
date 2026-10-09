# Operations reference

Signatures below match `src/devops_utils/agent/tools.py` verbatim. Every
work-item op returns the **trimmed** shape described in `SKILL.md` →
*Return shape*. Back to [SKILL.md](../SKILL.md).

## Contents

- List repositories
- Find files in a repository
- Search code content
- List work items
- Search work items
- Get one work item
- Create a work item
- Update a work item (state / assignee / title / description / area / iteration / custom)
- Area path / iteration path
- Comment on a work item
- Tags
- Assigning users

## List repositories

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

## Find files in a repository

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

## Search code content

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

## List work items

```python
azdo_list_work_items(
    project: str,
    states: list[str] | None = None,   # e.g. ["Active", "New"]
    types: list[str] | None = None,    # e.g. ["Bug", "Task"]
    assigned_to: str | None = None,    # email, display name, or "@Me"
    tags: list[str] | None = None,     # AND semantics: every tag must be present
    parent: int | None = None,         # direct children of this work-item id
    area_path: str | None = None,      # matches this node AND everything under it
    iteration_path: str | None = None, # matches this node AND everything under it
    top: int = 50,
) -> list[dict]
```

Backed by a WIQL query ordered by `System.ChangedDate DESC`.
`assigned_to="@Me"` uses the WIQL macro that resolves the identity behind the
token — "assigned to me" without knowing the user's email. "Pending" items are
the non-closed states of the process template (e.g. `["New", "Active"]`).
`parent` filters on `[System.Parent]` and matches **direct children only**
(Services / Server 2019.1+; walk levels iteratively for a whole tree).
`area_path`/`iteration_path` filter with WIQL `UNDER` — see
*Area path / iteration path*.

CLI: `devops-utils azdo list --project NAME [--state S ...] [--type T ...] [--assigned-to WHO | --mine] [--tag X ...] [--parent ID] [--area-path P] [--iteration-path P] [--top N]`
(`--state`/`--type`/`--tag` are repeatable; `--mine` = `--assigned-to @Me`.)

## Search work items

```python
azdo_search_work_items(
    project: str,
    text: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    assigned_to: str | None = None,    # email, display name, or "@Me"
    tags: list[str] | None = None,
    parent: int | None = None,
    area_path: str | None = None,
    iteration_path: str | None = None,
    top: int = 50,
) -> list[dict]
```

Matches `text` against title **and** description via WIQL `CONTAINS`; the
other filters compose the same way as `azdo_list_work_items`.

CLI: `devops-utils azdo search --project NAME "TEXT" [--state S ...] [--type T ...] [--assigned-to WHO | --mine] [--tag X ...] [--parent ID] [--area-path P] [--iteration-path P] [--top N]`

## Get one work item

```python
azdo_get_work_item(work_item_id: int, relations: bool = False, full: bool = False) -> dict
```

With `relations=True` the result carries a `relations` list of
`{kind, target, ...}` dicts — work-item kinds (`parent`, `child`,
`predecessor`, `successor`, `work_item`) carry the target work-item id;
`hyperlink`/`attachment`/`commit`/`pull_request`/`branch`/`build` carry the URL.

With `full=True` it also carries `rev` and a `fields` map of **every** raw
field, keyed by reference name — this is how you read a description
(`System.Description`, HTML), a scheduling date
(`Microsoft.VSTS.Scheduling.DueDate` / `.TargetDate` / `.StartDate`), or a
`Custom.*` field, none of which are in the trimmed shape. The two flags
compose. `list`/`search` are always trimmed by design: find ids there, then
`full` the one item you care about.

CLI: `devops-utils azdo get WORK_ITEM_ID [--relations] [--full]`

## Create a work item

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
    fields: dict | None = None,        # see fields-and-scheduling.md
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


## Update a work item (state / assignee / title / description / area / iteration / custom)

```python
azdo_update_work_item(
    work_item_id: int,
    state: str | None = None,          # e.g. "Active", "Resolved", "Closed"
    assigned_to: str | None = None,    # email or display name
    title: str | None = None,
    description: str | None = None,    # HTML
    area_path: str | None = None,      # move between Boards areas
    iteration_path: str | None = None, # move between sprints
    fields: dict | None = None,        # see fields-and-scheduling.md
) -> dict
```

Pass only the fields to change; giving none raises `ValueError`. Use it to
**close/resolve** (`state="Closed"` — valid state names are
process-template-specific: Agile uses `Closed`, Scrum `Done`, some templates
`Resolved`; check an existing item's `state` if a transition is rejected),
**reassign** an existing item, or **move it** to another area/sprint.

CLI: `devops-utils azdo update WORK_ITEM_ID [--state S] [--assigned-to WHO] [--title T] [--description H] [--area-path P] [--iteration-path P] [--field NAME=VALUE ...]`

## Area path / iteration path

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
# create straight into a team area and a sprint
devops-utils azdo create --project Contoso --type "User Story" \
  --title "Guest checkout" --parent 1400 \
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3'

# everything the Payments team has open in the current sprint
devops-utils azdo list --project Contoso \
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' \
  --state Active --state New

# move an item to another team AND another sprint in one patch
devops-utils azdo update 1421 \
  --area-path 'Contoso\Payments\Checkout' --iteration-path 'Contoso\Sprint 4'
```

```python
tools.azdo_create_work_item(
    "Contoso",
    "User Story",
    "Guest checkout",
    parent=1400,
    area_path="Contoso\\Payments",
    iteration_path="Contoso\\Sprint 3",
)
tools.azdo_list_work_items(
    "Contoso",
    area_path="Contoso\\Payments",  # includes Contoso\Payments\Checkout
    iteration_path="Contoso\\Sprint 3",
    states=["New", "Active"],
)
tools.azdo_update_work_item(1421, iteration_path="Contoso\\Sprint 4")
```

Backslashes: single-quote the path in bash **and** PowerShell; in Python source
either escape it (`"Contoso\\Sprint 3"`) or use a raw string
(`r"Contoso\Sprint 3"`). An invalid path is rejected by the server — read an
existing item's `area_path`/`iteration_path` (they are in the trimmed shape) if
a write fails with a classification-node error.


## Comment on a work item

```python
azdo_comment_work_item(work_item_id: int, text: str) -> dict
```

Written via the `System.History` field (works on every server, unlike the
preview-only `/comments` endpoint).

CLI: `devops-utils azdo comment WORK_ITEM_ID "TEXT"`

## Tags

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

## Assigning users

Set the assignee via the `assigned_to` parameter — it accepts an **email** or a
**display name** and maps to `System.AssignedTo`:

- On create: `azdo_create_work_item(..., assigned_to="dev@contoso.com")`.
- On an existing item: `azdo_update_work_item(id, assigned_to="dev@contoso.com")`.
- CLI: `--assigned-to dev@contoso.com` (on `create` and `update`).

On `list`/`search`, `assigned_to` is a *filter*, not a mutation.
