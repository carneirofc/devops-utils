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

## Surfaces

The same eleven operations are exposed three ways, all reading the env vars above:

- **CLI**: `devops-utils azdo {repos,list,search,get,create,update,comment,tag,link,unlink,attach}`
- **MCP tools**: `azdo_*` (run `devops-utils-mcp`)
- **Agent callables**: `devops_utils.agent.tools.azdo_*`

Core logic lives in `src/devops_utils/core/azure_devops/` (`client.py`,
`workitems.py`, `repos.py`) and is surface-agnostic.

## References (`link` / `azdo_add_work_item_link`)

One entry point covers every reference kind:

| kind | needs | `value` | relation |
| --- | --- | --- | --- |
| `commit` | project + repo | commit SHA | `ArtifactLink` `vstfs:///Git/Commit/...` |
| `pull_request` | project + repo | PR id | `ArtifactLink` `vstfs:///Git/PullRequestId/...` |
| `branch` | project + repo | branch name | `ArtifactLink` `vstfs:///Git/Ref/...GB{branch}` |
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

Comments use the `System.History` field and search uses WIQL `CONTAINS`, both for
maximum on-prem compatibility (no preview-only endpoints or separate Search host).
