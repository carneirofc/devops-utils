# Custom fields and scheduling

Any work-item field — custom (`Custom.*`) or system (`Microsoft.VSTS.*`) — and
the scheduling dates/effort. Back to [SKILL.md](../SKILL.md).

## Contents

- Custom fields
- Scheduling: start date, target date, due date, effort

## Custom fields

`azdo_create_work_item` and `azdo_update_work_item` take a `fields` dict
(CLI: repeatable `--field NAME=VALUE`) to set **any** work-item field the named
parameters don't cover — process-specific fields like
`Microsoft.VSTS.Common.Priority` or org-defined ones like `Custom.RiskLevel`:

```python
tools.azdo_create_work_item(
    "Contoso",
    "Bug",
    "Login page 500s under load",
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

The CLI parses `--field NAME=VALUE` into **strings** — `--field
Microsoft.VSTS.Common.Priority=1` sends `"1"`, which the server coerces for
numeric fields. The Python/MCP `fields` dict preserves real JSON types; use it
(`{"Microsoft.VSTS.Common.Priority": 1}`) if a numeric or boolean write is
rejected.

## Scheduling: start date, target date, due date, effort

**No named parameter covers dates or estimates** — they are ordinary fields, so
they go through `fields` / `--field` with their reference names:

| field | reference name | type | usually on |
| --- | --- | --- | --- |
| Start Date | `Microsoft.VSTS.Scheduling.StartDate` | DateTime | Epic, Feature |
| Target Date | `Microsoft.VSTS.Scheduling.TargetDate` | DateTime | Epic, Feature |
| Due Date | `Microsoft.VSTS.Scheduling.DueDate` | DateTime | Bug, Issue, Task |
| Finish Date | `Microsoft.VSTS.Scheduling.FinishDate` | DateTime | Task (Agile/CMMI) |
| Effort | `Microsoft.VSTS.Scheduling.Effort` | Double | Scrum PBI / Feature / Epic |
| Story Points | `Microsoft.VSTS.Scheduling.StoryPoints` | Double | Agile User Story |
| Original Estimate | `Microsoft.VSTS.Scheduling.OriginalEstimate` | Double | Task |
| Remaining Work | `Microsoft.VSTS.Scheduling.RemainingWork` | Double | Task |
| Completed Work | `Microsoft.VSTS.Scheduling.CompletedWork` | Double | Task |
| Priority | `Microsoft.VSTS.Common.Priority` | Integer | most types |
| Severity | `Microsoft.VSTS.Common.Severity` | String | Bug |
| Business Value | `Microsoft.VSTS.Common.BusinessValue` | Integer | Epic / Feature / Story |
| Acceptance Criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` | HTML | User Story / PBI |
| Repro Steps | `Microsoft.VSTS.TCM.ReproSteps` | HTML | Bug |

Dates are **ISO 8601** — `"2026-08-03"` or `"2026-08-03T00:00:00Z"`. Azure
DevOps stores them in UTC, so a bare date is midnight UTC. **Start Date +
Target Date are what Delivery Plans render**, which is why Epics and Features
carry that pair while a Task carries Due/Finish Date instead.

Which of these exist on a given type is process-template-specific (Agile vs
Scrum vs CMMI, plus per-org customisation). A field the type doesn't have comes
back as an unknown-field error on the patch — read a comparable existing item
with `azdo get <id> --full` and use the reference names it actually returns.

```bash
# schedule an Epic: start now, land end of quarter
devops-utils azdo update 1400 \
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 \
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-09-30

# create a Feature already scheduled, sized, and in a sprint
devops-utils azdo create --project Contoso --type Feature \
  --title "Guest checkout" --parent 1400 \
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' \
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 \
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-08-31 \
  --field Microsoft.VSTS.Scheduling.Effort=13

# a Bug due Friday, priority 1
devops-utils azdo update 1421 \
  --field Microsoft.VSTS.Scheduling.DueDate=2026-08-07 \
  --field Microsoft.VSTS.Common.Priority=1

# read the dates back (they are NOT in the trimmed shape) — no jq needed,
# the same line works in bash, PowerShell and cmd
devops-utils azdo get 1400 --full \
  --select fields/Microsoft.VSTS.Scheduling.StartDate \
  --select fields/Microsoft.VSTS.Scheduling.TargetDate
# => {"Microsoft.VSTS.Scheduling.StartDate": "...", "Microsoft.VSTS.Scheduling.TargetDate": "..."}
```

```python
tools.azdo_update_work_item(
    1400,
    fields={
        "Microsoft.VSTS.Scheduling.StartDate": "2026-08-03",
        "Microsoft.VSTS.Scheduling.TargetDate": "2026-09-30",
    },
)
feature = tools.azdo_create_work_item(
    "Contoso",
    "Feature",
    "Guest checkout",
    parent=1400,
    area_path="Contoso\\Payments",
    iteration_path="Contoso\\Sprint 3",
    fields={
        "Microsoft.VSTS.Scheduling.StartDate": "2026-08-03",
        "Microsoft.VSTS.Scheduling.TargetDate": "2026-08-31",
        "Microsoft.VSTS.Scheduling.Effort": 13,  # real number, not "13"
    },
)
dates = tools.azdo_get_work_item(1400, full=True)["fields"]
dates["Microsoft.VSTS.Scheduling.TargetDate"]  # '2026-09-30T00:00:00Z'
```

Always confirm a scheduling write with `azdo_get_work_item(id, full=True)` —
`create`/`update` return the **trimmed** shape, which drops every
`Microsoft.VSTS.*` field, so their return value cannot tell you the date landed.
