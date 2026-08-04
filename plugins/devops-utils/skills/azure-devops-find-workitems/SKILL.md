---
name: azure-devops-find-workitems
description: Query Azure DevOps work items by type, tags, parent, and area path — recipes for finding pending issues, walking an Epic's backlog, and scoping searches with a repo's tracker defaults.
---

# Find Azure DevOps work items

Use this skill whenever a task needs to *locate* work items — "find the
pending issues", "what's in this Epic", "open bugs for this team" — before
reading or updating them. It composes the filter surface of
`azdo_list_work_items` / `azdo_search_work_items` (CLI: `devops-utils azdo
list` / `search`; same-named `azdo_*` MCP tools when available). Requires the
`azure` extra; prefix commands with `uvx --from "devops-utils[azure]"` when
`devops-utils` is not installed.

## Read the repo's defaults first

If the repo has `docs/agents/issue-tracker.md`, its **Defaults for this
repo** table names the project, parent Epic, Area Path, and default tags.
Apply them to every query — they are what makes this repo's items findable
among everything else in the project. Without that file, ask the user for at
least the project name.

## The filter surface

Both `list` and `search` accept the same filters, all AND-combined:

| filter | CLI flag | semantics |
| --- | --- | --- |
| state | `--state` (repeatable) | `IN` — pending work = the non-closed states (`New`, `Active`, …) |
| type | `--type` (repeatable) | `IN` — `Bug`, `Task`, `User Story`, `Feature`, `Epic`, … |
| tags | `--tag` (repeatable) | every tag must be present (AND) |
| parent | `--parent ID` | **direct children** of that work-item id (`[System.Parent]`) |
| area path | `--area-path P` | the node **and everything under it** (WIQL `UNDER`) |
| iteration | `--iteration-path P` | same `UNDER` semantics, for sprints |
| assignee | `--assigned-to WHO` / `--mine` | email, display name, or the `@Me` macro |
| text | `search` positional | title + description `CONTAINS` (search only) |

Results are ordered by last change, trimmed to
`{id, type, title, state, assigned_to, tags, area_path, iteration_path, url}`.
Follow up with `azdo get <id> --full --relations` for descriptions, dates, and
links.

## Recipes

Substitute the defaults from the tracker config for `<AREA>`, `<TAG>`,
`<EPIC_ID>`, and the project name.

```bash
# Pending issues for this repo (the canonical "what's open" query)
devops-utils azdo list --project P --state New --state Active \
  --area-path '<AREA>' --tag <TAG>

# By type: open bugs only
devops-utils azdo list --project P --type Bug --state New --state Active \
  --area-path '<AREA>' --tag <TAG>

# The backlog directly under the parent Epic
devops-utils azdo list --project P --parent <EPIC_ID>

# Drill one level down: children of a Feature found above
devops-utils azdo list --project P --parent <FEATURE_ID> --state Active

# Triage queue: everything tagged for agent pickup
devops-utils azdo list --project P --tag ready-for-agent --state New --state Active

# My pending work in this repo's area
devops-utils azdo list --project P --mine --state Active --area-path '<AREA>'

# Text search, still scoped to the repo's defaults
devops-utils azdo search --project P "checkout timeout" \
  --area-path '<AREA>' --tag <TAG> --state Active
```

Python / MCP equivalents take the same names:

```python
from devops_utils.agent import tools

tools.azdo_list_work_items(
    "P", states=["New", "Active"], tags=["<TAG>"], area_path="<AREA>"
)
tools.azdo_list_work_items("P", parent=EPIC_ID)                 # Epic's children
tools.azdo_search_work_items("P", "checkout timeout", types=["Bug"])
```

## Walking a whole hierarchy

`--parent` is one level deep. To collect an Epic's full tree, iterate:
children of the Epic (Features), then `--parent` on each Feature id (Stories),
then on each Story (Tasks/Bugs). Alternatively `azdo get <id> --relations`
returns `child` relations for a single item.

## When a query comes back empty

- Drop filters one at a time (tags first, then area path) to learn which one
  excluded everything — items created before the conventions may lack tags.
- Check state names: the process template decides them (`Done` vs `Closed`,
  Scrum's `Committed`, …). Read an existing item's `state` and retry.
- `--parent` needs Azure DevOps Services or Server 2019.1+ (`System.Parent`);
  on older servers walk `azdo get <id> --relations` instead.
