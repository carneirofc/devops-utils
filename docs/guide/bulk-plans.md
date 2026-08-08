# Bulk work items with a plan file

Creating a feature and its eight stories one command at a time means eight
confirmation prompts, eight chances to typo a parent id, and no way to review
the shape of the whole thing before it exists. `devops-utils azdo apply` takes
one declarative **plan file** — YAML or JSON — and applies the entire batch
after a single review-and-confirm.

```bash
devops-utils azdo apply plan.yml             # preview, confirm once, apply
devops-utils azdo apply plan.yml --dry-run   # preview only, change nothing
devops-utils azdo apply plan.yml --yes --out results.json
cat plan.yml | devops-utils azdo apply -     # read the plan from stdin
```

## The shape of a plan

Three top-level keys: a `project`, an optional `defaults` map merged into every
item, and an ordered list of `items`.

```yaml
project: MyProject
defaults:
  area_path: MyProject\Platform
  fields:
    Custom.Source: git-history
items:
  - ref: feat                    # a local handle other items can point at
    type: Feature
    title: Payment retries
    tags: [payments, backend]
  - type: User Story
    title: Retry failed captures
    parent: ref:feat             # parented under the Feature created above
    assigned_to: dev@example.com
```

An item **without** `id` is a create (needs `type` and `title`); an item **with**
`id` is an update. `ref:<name>` points at an item defined *earlier* in the same
run — that's what makes a hierarchy expressible in one file.

Named keys cover the common fields — `type`, `title`, `description`, `state`,
`assigned_to`, `tags`, `area_path`, `iteration_path`, `parent`, `links`,
`comments` — and anything else goes under `fields:` by reference name. Unknown
top-level keys are a **warning in the preview, not an error**, so a typo is
visible without blocking the run.

## Worked example: a feature with its stories

```yaml
project: MyProject
defaults:
  area_path: MyProject\Payments
  iteration_path: MyProject\Sprint 4
  tags: [payments]
items:
  - ref: feat
    type: Feature
    title: Resilient payment capture
    description: "<p>Captures must survive a flaky acquirer.</p>"
    fields:
      Microsoft.VSTS.Scheduling.StartDate: 2026-08-03
      Microsoft.VSTS.Scheduling.TargetDate: 2026-09-30

  - ref: retry
    type: User Story
    title: Retry failed captures with backoff
    parent: ref:feat
    assigned_to: dev@example.com
    fields:
      Microsoft.VSTS.Scheduling.StoryPoints: 5

  - type: Task
    title: Add exponential backoff to the capture client
    parent: ref:retry
    links:
      - {kind: commit, repo: MyRepo, value: 0a1b2c3d}
      - {kind: hyperlink, value: "https://wiki/retries"}
    comments:
      - "Implemented in the capture client; see linked commit."

  - type: Task
    title: Alert when the retry budget is exhausted
    parent: ref:retry
```

```bash
devops-utils azdo apply plan.yml --dry-run
```

The preview lists all four operations with `defaults` already merged in. Drop
`--dry-run`, answer the single `Apply all 4 operation(s)?` prompt, and the tree
exists.

## Worked example: a bulk triage sweep

Updates need nothing but an `id`:

```yaml
project: MyProject
items:
  - id: 41
    state: Closed
    comments: ["Superseded by #1500."]
  - id: 42
    state: Active
    assigned_to: dev@example.com
    tags: [triaged, backend]
  - id: 43
    iteration_path: MyProject\Sprint 5
    fields: {Custom.RiskLevel: Low}
```

Generating that file from a query is a two-liner:

```bash
devops-utils azdo list --project MyProject --tag obsolete \
  | jq '{project: "MyProject", items: [.[] | {id: .id, state: "Closed"}]}' \
  | devops-utils azdo apply -
```

## Reading the results

Per-item results are printed as JSON on stdout (and written to `--out` if you
ask), one entry per item:

```json
[
  {"ref": "feat", "action": "create", "status": "created", "id": 1501, "url": "https://…"},
  {"ref": "retry", "action": "create", "status": "created", "id": 1502, "url": "https://…"},
  {"ref": null, "action": "update", "status": "failed", "id": 43,
   "error": "AzureDevOpsError: TF401320: Rule Error…"}
]
```

`status` is `created`, `updated`, `failed`, or `skipped`. The exit code is
non-zero if anything failed, so CI notices.

By default a failure does **not** stop the run — the remaining independent items
still apply, and only items whose `ref:` target failed fail with a message
naming the cause. Pass `--stop-on-error` to halt at the first failure instead;
everything after it reports as `skipped`.

## Notes that save time

- **`state` on a create** is applied as a follow-up patch, because most process
  templates refuse to create an item directly in a closed state. Writing
  `state: Closed` on a new item works.
- **All of an item's links** go out in a single request, so a partially linked
  item isn't a thing.
- **Field values keep their YAML type.** A number in the plan stays a number —
  unlike the CLI's `--field NAME=VALUE`, which is always a string. If a numeric
  or boolean write is being rejected on the command line, a plan is the fix.
- **Order matters** only for `ref:` — a reference must point backwards.

## The same thing from an agent

`azdo_apply_plan` exposes this as an MCP tool and as a Python callable, taking
the plan as a dict:

```python
from devops_utils.agent.tools import azdo_apply_plan

results = azdo_apply_plan({
    "project": "MyProject",
    "items": [{"type": "Task", "title": "Fix flaky test"}],
})
```

Over MCP it is gated by the same human confirmation as every other write tool —
one elicitation covering the whole batch. This is the intended path for an agent
that has just mined a backlog out of git history and wants to push it: build one
plan, review it once. The bundled `git-history-workitems` skill does exactly
that.
