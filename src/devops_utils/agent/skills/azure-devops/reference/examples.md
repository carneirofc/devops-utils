# Worked examples

End-to-end scripts in Python, bash, and PowerShell 7. Back to
[SKILL.md](../SKILL.md).

## Contents

- Worked example: create → assign → tag → comment → link
- Worked example: a scheduled Epic → Feature → Story

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
    "Contoso",
    "Bug",
    "Login page 500s under load",
    description="<p>Repro at 200 rps.</p>",
    assigned_to="dev@contoso.com",
    tags=["urgent", "regression"],
)
tools.azdo_set_work_item_tags(wi["id"], ["needs-review"], mode="add")
tools.azdo_comment_work_item(wi["id"], "Root cause: connection pool exhaustion.")
tools.azdo_add_work_item_link(
    wi["id"],
    "pull_request",
    "88",
    project="Contoso",
    repo="web-app",
    comment="Fix",
)
```

## Worked example: a scheduled Epic → Feature → Story

Everything the Boards UI exposes on the right-hand pane — area, iteration,
dates, effort, links — set from one script. Named params carry area/iteration;
`fields` carries the scheduling dates.

```python
from devops_utils.agent import tools

AREA = "Contoso\\Payments"

epic = tools.azdo_create_work_item(
    "Contoso",
    "Epic",
    "Self-service checkout",
    area_path=AREA,
    fields={
        "Microsoft.VSTS.Scheduling.StartDate": "2026-08-03",
        "Microsoft.VSTS.Scheduling.TargetDate": "2026-12-18",  # a whole quarter
        "Microsoft.VSTS.Common.BusinessValue": 80,
    },
)

feature = tools.azdo_create_work_item(
    "Contoso",
    "Feature",
    "Guest checkout",
    parent=epic["id"],
    area_path=AREA,
    iteration_path="Contoso\\Sprint 3",
    fields={
        "Microsoft.VSTS.Scheduling.StartDate": "2026-08-03",
        "Microsoft.VSTS.Scheduling.TargetDate": "2026-08-31",
        "Microsoft.VSTS.Scheduling.Effort": 13,
    },
)

story = tools.azdo_create_work_item(
    "Contoso",
    "User Story",
    "As a guest I can pay without an account",
    parent=feature["id"],
    area_path=AREA,
    iteration_path="Contoso\\Sprint 3",
    assigned_to="dev@contoso.com",
    tags=["checkout"],
    fields={
        "Microsoft.VSTS.Scheduling.StoryPoints": 5,
        "Microsoft.VSTS.Common.AcceptanceCriteria": "<ul><li>Order completes with an email only</li></ul>",
    },
)

# wire it to the code and to the work that must land first
tools.azdo_add_work_item_link(
    story["id"],
    "pull_request",
    "88",
    project="Contoso",
    repo="web-app",
)
tools.azdo_add_work_item_link(story["id"], "predecessor", "1399")

# verify: dates and relations both need the non-trimmed reads
plan = tools.azdo_get_work_item(feature["id"], relations=True, full=True)
plan["fields"]["Microsoft.VSTS.Scheduling.TargetDate"]  # '2026-08-31T00:00:00Z'
plan["relations"]  # parent → epic id
```

`-o id` prints only the new id, so capturing it needs no `jq`. The flags are
identical in both shells; only the variable syntax and the line continuation
(`\` vs `` ` ``) differ.

```bash
epic=$(devops-utils azdo create --project Contoso --type Epic \
  --title "Self-service checkout" --area-path 'Contoso\Payments' \
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 \
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-12-18 -y -o id)

feature=$(devops-utils azdo create --project Contoso --type Feature \
  --title "Guest checkout" --parent "$epic" \
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' \
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 \
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-08-31 \
  --field Microsoft.VSTS.Scheduling.Effort=13 -y -o id)

devops-utils azdo create --project Contoso --type "User Story" \
  --title "As a guest I can pay without an account" --parent "$feature" \
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' \
  --assigned-to dev@contoso.com --tag checkout \
  --field Microsoft.VSTS.Scheduling.StoryPoints=5

devops-utils azdo get "$feature" --relations --full
```

```powershell
$epic = devops-utils azdo create --project Contoso --type Epic `
  --title "Self-service checkout" --area-path 'Contoso\Payments' `
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 `
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-12-18 -y -o id

$feature = devops-utils azdo create --project Contoso --type Feature `
  --title "Guest checkout" --parent $epic `
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' `
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 `
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-08-31 `
  --field Microsoft.VSTS.Scheduling.Effort=13 -y -o id

devops-utils azdo create --project Contoso --type "User Story" `
  --title "As a guest I can pay without an account" --parent $feature `
  --area-path 'Contoso\Payments' --iteration-path 'Contoso\Sprint 3' `
  --assigned-to dev@contoso.com --tag checkout `
  --field Microsoft.VSTS.Scheduling.StoryPoints=5

devops-utils azdo get $feature --relations --full
```
