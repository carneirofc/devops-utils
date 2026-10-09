# Links, builds, PR comments, attachments

Back to [SKILL.md](../SKILL.md).

## Contents

- Links / references
- Remove a link
- Builds (definitions / list / get / timeline / logs / tag / link)
- Comment on a pull request
- Attach a file

## Links / references

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

One example per kind — `commit`/`pull_request`/`branch` need `--project` and
`--repo`; nothing else does:

```bash
# code artifacts (project + repo required)
devops-utils azdo link 1421 --kind commit --value 9fceb02 \
  --project Contoso --repo web-app --comment "Fixed here"
devops-utils azdo link 1421 --kind pull_request --value 88 \
  --project Contoso --repo web-app
devops-utils azdo link 1421 --kind branch --value feature/guest-checkout \
  --project Contoso --repo web-app

# build — the artifact URI carries only the id, so no project/repo
devops-utils azdo link 1421 --kind build --value 20345

# work-item graph
devops-utils azdo link 1421 --kind parent --value 1400        # 1400 is now the parent
devops-utils azdo link 1400 --kind child --value 1421         # same edge, other direction
devops-utils azdo link 1421 --kind predecessor --value 1399   # 1421 is blocked by 1399
devops-utils azdo link 1421 --kind successor --value 1450     # 1450 waits on 1421
devops-utils azdo link 1421 --kind work_item --value 1500     # plain "Related"

# external URL
devops-utils azdo link 1421 --kind hyperlink \
  --value 'https://status.contoso.com/incidents/42' --comment "Incident"

# re-parent: unlink the old edge, then link the new one
devops-utils azdo unlink 1421 --kind parent --value 1400
devops-utils azdo link   1421 --kind parent --value 1402

# verify — relations are not in the trimmed shape
devops-utils azdo get 1421 --relations --select relations
```

```python
tools.azdo_add_work_item_link(
    1421,
    "pull_request",
    "88",
    project="Contoso",
    repo="web-app",
    comment="Fix",
)
tools.azdo_add_work_item_link(1421, "build", "20345")
tools.azdo_add_work_item_link(1421, "predecessor", "1399")
tools.azdo_add_work_item_link(
    1421,
    "hyperlink",
    "https://status.contoso.com/incidents/42",
)
tools.azdo_get_work_item(1421, relations=True)["relations"]
# [{'kind': 'pull_request', 'target': 'vstfs:///Git/PullRequestId/...', 'name': 'Pull Request', 'comment': 'Fix'},
#  {'kind': 'predecessor', 'target': 1399}, ...]
```

## Remove a link

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

## Builds (definitions / list / get / timeline / logs / tag / link)

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

## Comment on a pull request

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

## Attach a file

```python
azdo_add_work_item_attachment(
    work_item_id: int,
    file_path: str,                    # local path
    comment: str | None = None,
) -> dict
```

Two-step: uploads the file, then attaches it as an `AttachedFile` relation.

CLI: `devops-utils azdo attach WORK_ITEM_ID FILE_PATH [--comment C]`
