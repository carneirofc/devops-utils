# Azure DevOps work-item tools

A limited, LLM-friendly interface to Azure DevOps work items, working against both
**Services (cloud)** and **Server (on-prem)**. Requires the `azure` extra (`httpx`).

## Configuration (no machine credentials)

Credentials are never read from the machine (no `az` CLI, credential files, or
Windows credential store). Everything comes from environment variables:

| Variable | Required | Notes |
| --- | --- | --- |
| `AZURE_DEVOPS_ORG_URL` | yes | Cloud `https://dev.azure.com/{org}` or on-prem `https://server/tfs/{collection}` |
| `AZURE_DEVOPS_TOKEN` | yes | Bearer token or PAT |
| `AZURE_DEVOPS_AUTH_SCHEME` | no | `bearer` (default) sends `Authorization: Bearer`; `pat` sends `Authorization: Basic base64(":"+token)` |
| `AZURE_DEVOPS_API_VERSION` | no | Default `7.1`; lower it for older on-prem servers |
| `DEVOPS_UTILS_SKIP_CONFIRMATION` | no | Truthy (`1`/`true`/`yes`/`on`) bypasses the MCP work-item write confirmation (see *Human-in-the-loop*) |

## Human-in-the-loop (MCP work-item writes)

On the **MCP server**, the seven work-item write tools (`azdo_create_work_item`,
`azdo_comment_work_item`, `azdo_set_work_item_tags`, `azdo_update_work_item`,
`azdo_add_work_item_link`, `azdo_remove_work_item_link`,
`azdo_add_work_item_attachment`) require human approval via MCP **elicitation**
before mutating Azure DevOps — the tool describes the pending change and applies
it only on `accept`; `decline`/`cancel` returns a `cancelled` status and writes
nothing. When the client can't prompt (elicitation unsupported / non-interactive),
the write is **blocked** unless `DEVOPS_UTILS_SKIP_CONFIRMATION` is truthy, which
allows unattended automation. Read tools and the non-work-item writes
(`azdo_tag_build`, `azdo_comment_pull_request`) are not gated; the CLI and agent
callables are unaffected (a human/caller invokes them directly). Implemented in
`src/devops_utils/mcp/server.py` (`_confirm_write` + `WORK_ITEM_WRITE_TOOLS`).

## Surfaces

The same fifteen operations are exposed three ways, all reading the env vars above:

- **CLI**: `devops-utils azdo {repos,list,search,get,create,update,comment,tag,link,unlink,attach,builds,build,build-tag,pr-comment}`
- **MCP tools**: `azdo_*` (run `devops-utils-mcp`)
- **Agent callables**: `devops_utils.agent.tools.azdo_*`

Core logic lives in `src/devops_utils/core/azure_devops/` (`client.py`,
`workitems.py`, `repos.py`, `builds.py`, `pullrequests.py`) and is
surface-agnostic.

## References (`link` / `azdo_add_work_item_link`)

One entry point covers every reference kind:

| kind | needs | `value` | relation |
| --- | --- | --- | --- |
| `commit` | project + repo | commit SHA | `ArtifactLink` `vstfs:///Git/Commit/...` |
| `pull_request` | project + repo | PR id | `ArtifactLink` `vstfs:///Git/PullRequestId/...` |
| `branch` | project + repo | branch name | `ArtifactLink` `vstfs:///Git/Ref/...GB{branch}` |
| `build` | — | build id | `ArtifactLink` `vstfs:///Build/Build/{id}` |
| `work_item` | — | target work-item id | `System.LinkTypes.Related` |
| `parent` | — | target work-item id | `System.LinkTypes.Hierarchy-Reverse` |
| `child` | — | target work-item id | `System.LinkTypes.Hierarchy-Forward` |
| `predecessor` | — | target work-item id | `System.LinkTypes.Dependency-Reverse` |
| `successor` | — | target work-item id | `System.LinkTypes.Dependency-Forward` |
| `hyperlink` | — | raw URL | `Hyperlink` |

`unlink` (`azdo unlink` / `azdo_remove_work_item_link`) removes a reference
using the same kind/value pairs — e.g. re-parenting is
`unlink --kind parent --value <old>` followed by `link --kind parent --value <new>`.
The relation is located by rel type + URL and removed by index with a guarding
JSON-Patch `test` op.

## Hierarchy (parent/child)

- **Create under a parent**: `azdo create --parent <id>` /
  `azdo_create_work_item(..., parent=<id>)` links the new item under an existing
  one (e.g. a Task under a User Story) in the same API call.
- **Read relations**: `azdo get <id> --relations` /
  `azdo_get_work_item(id, relations=True)` returns a `relations` list of
  `{kind, target, ...}` dicts — work-item kinds (`parent`, `child`,
  `predecessor`, `successor`, `work_item`) carry the target work-item id;
  `hyperlink`/`attachment`/artifact kinds carry the URL.

`update` (`azdo update` / `azdo_update_work_item`) changes `System.State`,
`System.AssignedTo`, `System.Title`, and/or `System.Description` on an existing
item — state names are process-template-specific (`Closed`/`Done`/`Resolved`).

## Builds

- **Query**: `azdo builds --project P [--definition ID] [--branch B] [--status S] [--result R] [--top N]` /
  `azdo_list_builds(project, ...)` lists builds (newest first) as trimmed
  `{id, number, definition, status, result, branch, requested_for, queue_time, finish_time, web_url}`
  dicts; `azdo build <id> --project P` / `azdo_get_build` fetches one. Short
  branch names are expanded to `refs/heads/...`.
- **Link to a work item**: `azdo link <wi> --kind build --value <build-id>` —
  no `project`/`repo` needed (the artifact URI carries only the build id).
- **Tag**: `azdo build-tag <build-id> TAG [TAG ...] --project P` /
  `azdo_tag_build` adds tags (builds have no comments; tags are the annotation)
  and returns the resulting tag list.

## Pull-request comments

`azdo pr-comment <pr-id> "TEXT" --project P --repo R [--thread N]` /
`azdo_comment_pull_request` posts a new (active) comment thread on a PR, or a
reply when a thread id is given. Returns `{thread_id, comment_id, status}`.

**Commits cannot be commented on** — Azure DevOps has no documented REST
endpoint for commit comments (the web UI uses an internal API). Comment on the
PR containing the commit, or on the work item that links it.

Comments use the `System.History` field and search uses WIQL `CONTAINS`, both for
maximum on-prem compatibility (no preview-only endpoints or separate Search host).
