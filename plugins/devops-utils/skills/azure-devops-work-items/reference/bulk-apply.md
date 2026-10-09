# Bulk operations: apply a plan

Back to [SKILL.md](../SKILL.md).

For anything beyond a couple of writes — importing a backlog, mass updates,
wiring many links — build a **plan** (YAML or JSON) and apply it in one gated
batch instead of issuing per-item commands:

```yaml
project: Contoso              # default project for every item
defaults:                     # merged into every item; the item wins
  type: User Story
  area_path: Contoso\Payments
  fields: {Custom.Source: git-history}
items:
  - ref: feat-checkout        # local handle later items can reference
    type: Feature
    title: Guest checkout
    description: "<p>Shoppers can buy without creating an account.</p>"
    state: Closed             # applied via follow-up patch after create
    assigned_to: dev@contoso.com
    tags: [checkout]
    fields:                   # ANY reference name passes through — custom too
      Microsoft.VSTS.Scheduling.TargetDate: 2026-08-31
      Custom.RiskLevel: High
    links:
      - {kind: commit, value: 3f2a91c, repo: web-app}
      - {kind: hyperlink, value: "https://status.contoso.com/42"}
    comments: [Imported from git history.]
  - type: User Story
    title: As a guest I can pay without an account so I finish faster
    parent: ref:feat-checkout # or a real work-item id
    fields:
      Microsoft.VSTS.Common.AcceptanceCriteria: >-
        <p>A guest completes payment with only an email address.</p>
  - id: 1421                  # has an id → update instead of create
    state: Active
    fields: {Custom.RiskLevel: Low}
```

Rules and behaviour:

- Items apply **in order**. No `id` → create (`type` + `title` required);
  `id` → update. `parent` and work-item link values take `ref:<name>`
  pointing at an *earlier* item, so a whole Feature → Story tree lands in one
  plan.
- The schema is deliberately loose: named keys cover the common fields, and
  the per-item `fields` map passes **any** field reference name through
  (`Microsoft.VSTS.*`, `Custom.*`, …) — the user is never limited to the named
  keys. Unknown item keys are *warnings* shown in the review, not errors.
- All of an item's `links` are sent in a single patch request.
- **Review window / HITL:** `azdo apply plan.yml` prints every warning and the
  full expanded operation list to stderr, then asks **one** confirmation for
  the whole batch. `--dry-run` stops after the review; `--yes` /
  `DEVOPS_UTILS_SKIP_CONFIRMATION` skip the prompt. On MCP, `azdo_apply_plan`
  is elicitation-gated like every write tool.
- **Results:** per-item JSON on stdout (`--out results.json` to also save) —
  `{ref, action, id, url, status}` with `status` of
  `created`/`updated`/`failed` (+ `error`)/`skipped`. A failure doesn't stop
  the batch unless `--stop-on-error`; items referencing a failed `ref` fail
  with a clear message instead of mis-parenting. Nothing is rolled back —
  re-run with the failed items only, or switch them to `id:` updates.
- Exit code is non-zero if any item failed.

```bash
devops-utils azdo apply plan.yml --dry-run   # review only
devops-utils azdo apply plan.yml --out results.json
```

```python
from devops_utils.agent import tools

results = tools.azdo_apply_plan(open("plan.yml", encoding="utf-8").read())
```
