---
name: setup-issue-tracker
description: Guided, prompt-based setup of a repo's Azure DevOps issue-tracker config — asks for org URL, project, parent Epic, Area Path, and default tags, validates each against the live organization, then writes docs/agents/issue-tracker.md via `devops-utils setup tracker`.
---

# Set up the issue tracker (prompt-based)

Use this skill when a repo should start tracking its issues/PRDs as Azure
DevOps work items, or when its `docs/agents/issue-tracker.md` needs to be
(re)configured. The outcome is a rendered tracker config —
`docs/agents/issue-tracker.md` + `docs/agents/triage-labels.md` — whose
**Defaults for this repo** table (org URL, project, parent Epic, Area Path,
default tags, done state) other skills read to create and find work items.

Run the flow below **interactively**: ask the user for each value, but never
ask blind — query the live Azure DevOps organization first and offer what
actually exists as the choices. Requires the `azure` extra; if `devops-utils`
is not on `PATH`, prefix every command with `uvx --from "devops-utils[azure]"`.

## Step 0 — credentials

Check that `AZURE_DEVOPS_ORG_URL` and `AZURE_DEVOPS_TOKEN` are set. If not,
run `devops-utils setup env` and ask the user to fill in the scaffold — never
hunt for credentials yourself.

## Step 1 — organization URL

Default to the current `AZURE_DEVOPS_ORG_URL` value and confirm it with the
user (cloud `https://dev.azure.com/{org}` or on-prem
`https://server/tfs/{collection}`). The env var stays authoritative at
runtime; the value recorded in the config is documentation for agents.

## Step 2 — project

Ask which team project the repo's issues live in. Validate the answer against
the live org — `devops-utils azdo repos` lists repositories with their
`project` names; a project that returns results exists. If the user is unsure,
present the distinct project names from that output.

## Step 3 — parent Epic

Every new work item should hang under one Epic for this repo. List the
candidates and let the user pick one (or none):

```bash
devops-utils azdo list --project <PROJECT> --type Epic --top 25
```

If no Epic fits, offer to create one (confirmation-gated):

```bash
devops-utils azdo create --project <PROJECT> --type Epic --title "<repo> backlog"
```

Record the chosen Epic's **id**.

## Step 4 — Area Path

Ask which `System.AreaPath` the repo's items belong to. Read the `area_path`
of existing items (e.g. the children of the chosen Epic, via
`devops-utils azdo list --project <PROJECT> --parent <EPIC_ID>`) and offer
those values; fall back to the project root when the project doesn't use
areas. Paths are backslash-separated and rooted at the project name
(`Project\Team`).

## Step 5 — default tags

Ask for the set of tags every created item should carry (and queries should
filter by) — typically one repo-identifying tag (e.g. the repo name) plus any
team conventions. Suggest tags seen on existing items under the Epic. An empty
set is valid.

## Step 6 — done state

Read the `state` of a closed item in the project (or ask): Agile uses
`Closed`, Scrum `Done`, CMMI/others sometimes `Resolved`.

## Step 7 — write the config

Summarize every collected value, get one confirmation, then render:

```bash
devops-utils setup tracker \
  --project-name <PROJECT> \
  --org-url <ORG_URL> \
  --parent-epic <EPIC_ID> \
  --area-path '<AREA\PATH>' \
  --default-tag <tag1> --default-tag <tag2> \
  --done-state <STATE> \
  --force
```

(`--default-tag` is repeatable; omit any flag the user declined — the template
renders a sensible fallback. `--dest <repo-root>` targets another repo;
without `--force` existing files are skipped, not overwritten.)

## Step 8 — verify

Read back `docs/agents/issue-tracker.md`, check the **Defaults for this
repo** table matches what the user chose, and prove the defaults work by
running the pending-issues query it documents:

```bash
devops-utils azdo list --project <PROJECT> --state New --state Active \
  --area-path '<AREA\PATH>' --tag <tag1>
```

Show the user the result count. Editing the rendered markdown later is fine —
it is config, not generated-only output.
