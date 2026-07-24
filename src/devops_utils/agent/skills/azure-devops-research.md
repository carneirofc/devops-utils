---
name: azure-devops-research
description: Research Azure DevOps status read-only — my pending work items, filtering by type/state/tags, build definitions and run status, failure diagnosis via timeline and log tailing, and finding repos/files/code. Use when the question is "what's the status of X" rather than "change X".
---

# Azure DevOps research

Read-only playbooks over the `azdo_*` tools (MCP server `devops-utils`, CLI
`devops-utils azdo`, Python `devops_utils.agent.tools`). Configuration comes
from `AZURE_DEVOPS_ORG_URL` + `AZURE_DEVOPS_TOKEN` (see the `azure-devops-work-items`
skill for the full env-var table). Everything here works on cloud and on-prem
Server unless noted.

If the `devops-utils setup agents` subagents are installed
(`azdo-workitem-analyst`, `azdo-build-analyst`, `azdo-repo-analyst`), prefer
delegating the corresponding playbook to them — they keep raw query results out
of the main conversation.

## My pending work items

- `azdo_list_work_items(project, assigned_to="@Me", states=[...])` — `@Me` is
  a WIQL macro resolving the identity behind the token; no email needed.
  CLI: `devops-utils azdo list --project P --mine --state Active --state New`.
- "Pending" = the non-closed states of the process template: Agile
  `New/Active`, Basic `To Do/Doing`, Scrum `New/Approved/Committed`. Unknown
  template? Query once without a state filter and read the states that appear.

### Worked example: my pending bugs tagged urgent

**CLI**

```bash
devops-utils azdo list --project Contoso --mine \
  --state Active --state New --type Bug --tag urgent
```

**Python / agent**

```python
from devops_utils.agent import tools

items = tools.azdo_list_work_items(
    "Contoso",
    assigned_to="@Me",
    states=["Active", "New"],
    types=["Bug"],
    tags=["urgent"],
)
# => [{"id": 1421, "type": "Bug", "title": "Login page 500s under load",
#      "state": "Active", "assigned_to": "dev@contoso.com",
#      "tags": "urgent; regression", "url": "https://..."}]
```

Report the count first, then id/title/state per item — never mutate from
here; route any create/update/comment/tag through the write tools (MCP
elicitation-gated) instead.

## Filter by type and tags

- `types=["Bug"]` etc.; `tags=["backend", "urgent"]` has AND semantics (every
  tag must be present). CLI: `--type Bug --tag backend --tag urgent`.
- Combine with `azdo_search_work_items(project, text, ...)` for a text match on
  title/description on top of the same filters.
- Drill in with `azdo_get_work_item(id, relations=True)` to see parent/child
  items and linked commits/PRs/branches/builds.

## Build status and failure diagnosis

1. Find the pipeline: `azdo_list_build_definitions(project, name="CI*")`.
2. Runs: `azdo_list_builds(project, definitions=[id], branch="main",
   results=["failed"])` — newest first.
3. Why it failed, cheapest first:
   - `azdo_get_build_timeline(project, build_id)` → the `failed` records'
     `issues` usually contain the answer.
   - Need log context? Take that record's `log_id`, get `line_count` from
     `azdo_list_build_logs`, then **tail**:
     `azdo_get_build_log(project, build_id, log_id, start_line=line_count-200)`.
     Never pull a large log whole; widen only if the tail is inconclusive.

## Find repos, files, and code

Three tiers, cheapest and most portable first:

1. Repo names: `azdo_list_repositories(project, name_filter="api")`.
2. File paths: `azdo_find_repo_files(project, repo, path_pattern="*.yml")` —
   Git Items API, works everywhere.
3. Code content: `azdo_code_search(project, text, repo=...)` — Search
   extension; always on cloud, may be missing on-prem (clear error → fall back
   to tier 2). Supports code-search syntax (`def:Foo`, `ext:yml pipeline`).

## Ground rules

- This skill is research-only: report findings with ids and `web_url`s; route
  any create/update/comment/tag through the write tools, which the MCP server
  gates behind human confirmation.
- Keep `top` modest and say when results were truncated.
