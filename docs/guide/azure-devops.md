# Azure DevOps from the command line

`devops-utils azdo` is a task-shaped interface to Azure DevOps work items,
builds, repositories and pull requests. It talks plain REST, works against
**Services (cloud)** and **Server (on-prem)** alike, and prints JSON and nothing
but JSON on stdout — so every command below composes with `jq`.

Needs the `azure` extra and the environment variables from
{doc}`install`.

```{tip}
Every example works unchanged with `uvx --from "devops-utils[azure]"
devops-utils azdo …` if you'd rather not install anything.
```

For the full parameter-by-parameter reference — link kinds, field reference
names, WIQL semantics — see {doc}`../agents/azure-devops`. This page is the
cookbook.

## Two rules worth knowing first

**Writes ask before they write.** `create`, `update`, `comment`, `tag`, `link`,
`unlink`, `attach`, `build-tag`, `pr-comment` and `apply` print a preview of the
pending change and prompt for confirmation. Add `--yes` to skip the prompt in a
script, or `--dry-run` to see the preview and stop.

**stdout is data, stderr is conversation.** Previews, prompts and warnings go to
stderr, so `devops-utils azdo get 42 --full | jq .fields` works even for
commands that prompted you. Output is UTF-8 whatever the shell's code page, so
accented text needs no `chcp` or `PYTHONUTF8` preamble on Windows.

## Finding work

### What's on my plate?

`--mine` uses the WIQL `@Me` macro — the server resolves the identity behind
your token, so nothing has to be configured:

```bash
devops-utils azdo list --project MyProject --mine --state Active
```

### The team's open bugs, newest 20

```bash
devops-utils azdo list --project MyProject \
  --type Bug --state New --state Active --top 20
```

Repeatable filters (`--state`, `--type`, `--tag`) are OR within a flag and AND
across flags; tags AND with each other.

### Everything in the current sprint, for one team

```bash
devops-utils azdo list --project MyProject \
  --area-path 'MyProject\Payments' \
  --iteration-path 'MyProject\Sprint 3'
```

Both paths match the node **and everything under it** (WIQL `UNDER`), so
`MyProject\Payments` also picks up `MyProject\Payments\Fraud`.

### Walk an Epic's backlog

```bash
devops-utils azdo list --project MyProject --parent 1400          # direct children
devops-utils azdo list --project MyProject --parent 1400 --state New
```

`--parent` returns *direct* children only — walk a level at a time to map a
tree.

### Search by words in the title or description

```bash
devops-utils azdo search --project MyProject "login timeout"
devops-utils azdo search --project MyProject "retry" --type Bug --tag payments
```

`search` accepts the same filters as `list`, so it narrows rather than replaces
them.

### Read one item in full

`list` and `search` return a trimmed shape on purpose — find the id there, then:

```bash
devops-utils azdo get 42                # id, title, type, state, assignee, tags
devops-utils azdo get 42 --relations    # + parent/child/commit/PR links
devops-utils azdo get 42 --full         # + every raw field: description, dates, Custom.*
```

`--full` is the only way to read back custom fields and scheduling dates. It
composes with `--relations`.

## Changing work

### File a bug under the right Epic

```bash
devops-utils azdo create --project MyProject \
  --type Bug --title "Checkout times out at 30s" \
  --parent 1400 \
  --area-path 'MyProject\Payments' \
  --assigned-to dev@example.com \
  --tag payments --tag regression
```

### Move an item along

```bash
devops-utils azdo update 42 --state Resolved --assigned-to qa@example.com
devops-utils azdo update 42 --iteration-path 'MyProject\Sprint 4'   # push to next sprint
```

State names come from your process template — `Closed`, `Done` and `Resolved`
are all real answers depending on the project.

### Leave a note, add tags

```bash
devops-utils azdo comment 42 "Reproduced on staging; capture pool is exhausted."
devops-utils azdo tag 42 backend urgent              # merged with existing tags
devops-utils azdo tag 42 triaged --mode replace      # replaces them
```

### Connect the item to the code

```bash
devops-utils azdo link 42 --kind commit --project MyProject --repo MyRepo --value 0a1b2c3d
devops-utils azdo link 42 --kind pull_request --project MyProject --repo MyRepo --value 77
devops-utils azdo link 42 --kind hyperlink --value "https://wiki/retries"
devops-utils azdo link 42 --kind parent --value 1400
```

Re-parenting is an unlink followed by a link:

```bash
devops-utils azdo unlink 42 --kind parent --value 1400
devops-utils azdo link   42 --kind parent --value 1500
```

### Attach evidence

```bash
devops-utils azdo attach 42 ./trace.log --comment "Timeout trace from staging"
```

### Set a date or a custom field

There is no named flag for dates or estimates — they're ordinary fields, set by
reference name:

```bash
devops-utils azdo update 1400 \
  --field Microsoft.VSTS.Scheduling.StartDate=2026-08-03 \
  --field Microsoft.VSTS.Scheduling.TargetDate=2026-09-30 \
  --field Custom.RiskLevel=High
```

Confirm it landed with `azdo get 1400 --full` — `create`/`update` return the
trimmed shape, which omits `Microsoft.VSTS.*`.

### Do it to fifty items at once

One plan file, one confirmation — see {doc}`bulk-plans`.

## Diagnosing a failed pipeline

The usual descent: find the run, read its timeline, tail the log of whatever is
red.

```bash
# 1. Which pipelines exist?
devops-utils azdo definitions --project MyProject --name 'CI*'

# 2. What failed on main lately?
devops-utils azdo builds --project MyProject --branch main --result failed --top 5

# 3. Where in the run did it break? (stages/jobs/tasks + error issues + log ids)
devops-utils azdo timeline 1234 --project MyProject

# 4. Which logs are worth reading, and how long are they?
devops-utils azdo logs 1234 --project MyProject

# 5. Tail the interesting one instead of downloading 40k lines
devops-utils azdo log 1234 7 --project MyProject --start-line 800
```

Then tie the finding to a work item, and annotate the run itself:

```bash
devops-utils azdo link 42 --kind build --value 1234    # no project/repo needed
devops-utils azdo build-tag 1234 flaky --project MyProject
```

Builds have no comments — tags are the annotation mechanism.

### Watch a running pipeline

```bash
devops-utils azdo builds --project MyProject --status inProgress
devops-utils azdo build 1234 --project MyProject | jq '{status, result, branch}'
```

## Searching repositories

Three tiers, cheapest first:

```bash
# Repository names
devops-utils azdo repos --project MyProject --name api

# File paths — Git Items API glob, works everywhere including on-prem
devops-utils azdo files --project MyProject --repo MyRepo --pattern '*.yml'
devops-utils azdo files --project MyProject --repo MyRepo --pattern 'src/**/*.py' --branch develop

# File contents — needs the Search extension
devops-utils azdo code-search "connection pool" --project MyProject --repo MyRepo
```

`code-search` is always available on cloud; on-prem needs the Search extension
installed. When it isn't, `files` is the portable fallback.

## Pull requests

```bash
devops-utils azdo pr-comment 77 "Nit: this retry should be capped." \
  --project MyProject --repo MyRepo

# reply into an existing thread
devops-utils azdo pr-comment 77 "Agreed, capped at 3." \
  --project MyProject --repo MyRepo --thread 5
```

Commits cannot be commented on — Azure DevOps exposes no REST endpoint for it.
Comment on the PR that contains the commit, or on the work item that links it.

## Scripting recipes

Because stdout is clean JSON:

```bash
# Ids of my active bugs
devops-utils azdo list --project MyProject --mine --type Bug --state Active \
  | jq -r '.[].id'

# Close everything tagged 'obsolete', unattended
devops-utils azdo list --project MyProject --tag obsolete | jq -r '.[].id' \
  | xargs -I{} devops-utils azdo update {} --state Closed --yes

# Capture the new id when creating
NEW=$(devops-utils azdo create --project MyProject --type Task \
        --title "Fix flaky test" --yes | jq -r .id)

# CSV of the sprint
devops-utils azdo list --project MyProject --iteration-path 'MyProject\Sprint 3' \
  | jq -r '.[] | [.id, .type, .state, .title] | @csv'
```

For a fully unattended run (CI), either pass `--yes` per command or export
`DEVOPS_UTILS_SKIP_CONFIRMATION=1` once. Prefer `--yes`: it keeps the blast
radius to the command you meant.

## The same operations elsewhere

Every command here exists as an MCP tool (`azdo_*`, served by
`devops-utils-mcp`) and as a plain Python callable in
`devops_utils.agent.tools`, all reading the same environment variables:

```python
from devops_utils.agent import tools

for item in tools.azdo_list_work_items("MyProject", states=["Active"], assigned_to="@Me"):
    print(item["id"], item["title"])
```

See {doc}`agents` for wiring those into Claude Code or another agent.
