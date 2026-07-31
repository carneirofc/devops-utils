---
name: git-history-workitems
description: Mine the repository's git history into per-year markdown Feature / User Story files (commits, tags, authors, status) ready to be pushed to Azure DevOps work items. Use when the user asks to reconstruct a backlog, features, or work items from git history.
---

# Git history → Features / User Stories

Turn the current repository's git history into a reviewable backlog on disk:
markdown files, one per **Feature**, grouped in `year/` folders, each Feature
containing its child **User Stories**. The files carry everything needed to
later create and update Azure DevOps work items with the
`azure-devops-work-items` skill (`devops-utils azdo`): titles, descriptions,
tags, commit hashes, authors, and completion status.

This skill only reads git and writes markdown — it performs **no Azure DevOps
writes**. Pushing the result to Azure DevOps is a separate, explicit follow-up.

## Before starting: ask the content language

**Always ask the user which language the generated content should be written
in** (titles, descriptions, story text — e.g. English, Portuguese) before
reading any history, unless they already stated it in the request. Structural
elements stay as-is regardless of the answer: frontmatter keys, field names,
`kind` values (`Feature`), status values (`implemented`/`in-progress`), slugs,
file names, and tags remain in English; commit subjects are quoted verbatim
from git.

## Output layout

Default output root: `docs/workitems/history/` (ask before using a different
one only if the user gave no hint). Features are grouped by the **year of
their first commit**:

```
docs/workitems/history/
├── index.md                     # one-line-per-feature table across all years
├── 2024/
│   ├── feature-initial-cli.md
│   └── feature-manifest-sanitizer.md
└── 2025/
    └── feature-azure-devops-client.md
```

One file per Feature, named `feature-<slug>.md`. Each file holds the Feature
plus all of its User Stories — a story never lives in a different file than
its parent.

## Feature file format

```markdown
---
kind: Feature
title: Azure DevOps REST client
slug: azure-devops-client
year: 2025
status: implemented          # implemented | in-progress
tags: [azure-devops, api-client, http]
first_commit: 3f2a91c
last_commit: 07aa258
authors:
  - Jane Dev <jane@contoso.com>
assigned_to: jane@contoso.com   # most active author on the feature
azure_devops_id:                # filled in once the work item exists
---

One or two paragraphs describing WHAT capability this feature delivered and
why, written from the diffs — not a paraphrase of commit subjects.

## User Stories

### Authenticate against cloud and on-prem servers

- status: implemented
- tags: [auth, on-prem]
- assigned_to: jane@contoso.com
- authors: Jane Dev <jane@contoso.com>
- first_commit: 3f2a91c
- last_commit: 9d41b02
- azure_devops_id:
- commits:
  - `3f2a91c` feat(azdo): add bearer-token client core
  - `9d41b02` feat(azdo): support PAT basic-auth scheme

Short description of the user-visible increment this story delivered.

### <next story…>
```

Rules for the fields:

- `commits` — **exhaustive**: every commit belonging to the story is listed,
  hash + verbatim subject, oldest first. These hashes are what gets linked to
  the Azure DevOps work item, so a commit missing here is a commit that never
  gets linked — never summarise a span as "…and follow-ups". A Feature's
  commit set is the union of its stories' lists.
- `first_commit` / `last_commit` — the earliest and latest commit (author
  date) belonging to the Feature/story. If the feature is still evolving,
  `last_commit` is the latest so far and `status: in-progress`.
- `status: implemented` only when the work reads as complete: the capability
  landed, follow-ups are fixes/docs that tapered off, nothing in the history
  (TODOs added, reverted halves, an abandoned flag) suggests unfinished work.
- `tags` — derived from the *changes*, not copied from commit subjects: the
  subsystem touched (paths, module names), conventional-commit scopes, the
  nature of the work (`api-client`, `cli`, `mcp`, `docs`, `packaging`,
  `security`, `refactor`, …). Lowercase, hyphenated, 2–6 per item. These
  become Azure DevOps tags verbatim.
- `assigned_to` — the author with the most commits on that item (ties → most
  lines changed). Keep the full `Name <email>` roster in `authors`; put only
  the chosen email in `assigned_to`. Respect `.mailmap` if present
  (`git log --use-mailmap`).
- `azure_devops_id` — always emitted empty; the Azure DevOps push fills it in
  so re-runs update instead of duplicating.

`index.md` is a table: feature title, year, status, story count, commit range,
assigned_to, azure_devops_id — the at-a-glance map for review and for the
push step.

## Workflow

### 1. Collect history

```bash
git log --use-mailmap --no-merges --reverse \
  --date=format:%Y-%m-%d \
  --pretty=format:'%h|%ad|%an|%ae|%s'
```

gives the full timeline (oldest first). For anything beyond the subject line,
inspect the actual change:

```bash
git show --stat <sha>          # files touched, size of the change
git show <sha>                 # full diff when the subject is vague
git log --follow -- <path>     # the history of one subsystem
```

On large repositories, page through history (`--max-count` + `--skip` or per
year with `--since/--until`) rather than loading everything at once, but never
let paging decide the grouping — a feature may span pages.

### 2. Group into Features — semantically, not by time

**Do not bundle commits merely because they are close in time.** Adjacent
commits routinely belong to different lines of work, and one feature is often
interleaved with others over weeks. Group by what the diffs say:

- Same subsystem/paths + same goal → same Feature, even months apart. A
  `fix(azdo): …` two releases later still belongs to the Azure DevOps client
  Feature.
- Conventional-commit scopes (`feat(azdo): …`, `fix(cli): …`) are strong
  grouping hints; verify against the diff when scopes are missing or sloppy.
- A Feature is a shippable capability (what a changelog "Added" bullet
  describes). A User Story is one user-visible increment within it — a
  subcommand, an auth scheme, an output format. Pure chores (CI, formatting,
  release bumps) that serve no feature go into a single "Repository
  maintenance" Feature per year rather than polluting real ones.
- `CHANGELOG.md`, release tags (`git tag --sort=creatordate`), and PR/issue
  references in messages are corroborating evidence for where a capability
  begins and ends.

Aim for coarse Features (a handful per year, not one per commit) with 2–6
stories each. Every commit should land in exactly one story; list a genuinely
cross-cutting commit under the story it advanced most and mention the overlap
in the description.

### 3. Write the files

Write each Feature file under `<out>/<year>/` (year of `first_commit`), then
regenerate `index.md`. Re-running the skill must be safe: update existing
files in place — extend commit lists, move `last_commit` forward, flip
`in-progress` → `implemented` — and **preserve any non-empty
`azure_devops_id`**.

### 4. Report

Summarise per year: features found, stories, how many implemented vs
in-progress, and any commits that resisted classification (say where you put
them). Stop here — pushing to Azure DevOps is the user's call.

## Custom fields and user extensions

The format above is the baseline, not a cage. If the user wants extra data on
the work items — priorities, story points, custom process fields — add a
`fields:` map (frontmatter for the Feature, a `- fields:` entry per story)
keyed by **field reference name**; every key passes through to Azure DevOps
untouched:

```yaml
fields:
  Microsoft.VSTS.Common.Priority: 2
  Custom.LegacyImport: "true"
```

Honour any other structural adjustments the user asks for (different output
root, extra frontmatter keys, per-story authors detail) — only keep the core
guarantees intact: Feature parents its stories, commit lists stay exhaustive,
`azure_devops_id` slots exist.

## Follow-up: pushing to Azure DevOps

When the user asks to create/update the work items, **generate a bulk plan**
from these files and apply it with `devops-utils azdo apply` (see *Bulk
operations* in the `azure-devops-work-items` skill) — one reviewable batch
with a single confirmation, instead of dozens of individually prompted
commands:

- One plan item per Feature (`ref:` = the file's `slug`) and per story, in
  order, with each story's `parent: ref:<feature-slug>` — **Feature is always
  the parent of its User Stories**. Ask the user which Epic (if any) the
  Features hang under.
- Map fields 1:1: `title`, description body, `tags`, `assigned_to`, and any
  `fields:` map verbatim; `status: implemented` → the project's done state
  (`Closed`/`Done` — template-specific), `in-progress` → `Active`.
- Link the code: a `links:` entry `{kind: commit, value: <sha>, repo: <repo>}`
  for **every hash in the story's `commits` list** — the list is exhaustive
  precisely so each commit ends up linked on the work item. All of an item's
  links go out in one request.
- Items that already carry an `azure_devops_id` become `id:` **update** items
  instead of creates — never duplicate.
- Review with `--dry-run` first if the user wants a look before the prompt;
  then apply and read the per-item results (`--out results.json`), and write
  every created id back into the matching file's `azure_devops_id` field.
