# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Human-in-the-loop confirmation for work-item **write** tools on the MCP
  server: `azdo_create_work_item`, `azdo_comment_work_item`,
  `azdo_set_work_item_tags`, `azdo_update_work_item`, `azdo_add_work_item_link`,
  `azdo_remove_work_item_link`, and `azdo_add_work_item_attachment` now prompt
  the client for approval via MCP elicitation before mutating Azure DevOps.
  Declining returns a `cancelled` status without writing. When the client cannot
  prompt (elicitation unsupported / non-interactive), the write is **blocked**
  unless `DEVOPS_UTILS_SKIP_CONFIRMATION` is set to a truthy value
  (`1`/`true`/`yes`/`on`) to allow unattended automation. Read tools and the
  non-work-item writes (`azdo_tag_build`, `azdo_comment_pull_request`) are
  unaffected, as are the CLI and agent callables (already human/caller driven).

## [0.2.0] - 2026-07-20

### Added

- New `azdo link` kind `build`: reference a build (pipeline run) from a work
  item via `vstfs:///Build/Build/{id}` — needs only the build id, no
  project/repo. Read back by `azdo get --relations` and removable with
  `azdo unlink`.
- `azdo builds` / `azdo build` (CLI) and `azdo_list_builds` / `azdo_get_build`
  (MCP + agent callables): list and inspect builds (id, number, definition,
  status, result, branch) with definition/branch/status/result filters.
- `azdo build-tag` / `azdo_tag_build`: add tags to a build (builds have no
  comments; tags are the annotation mechanism).
- `azdo pr-comment` / `azdo_comment_pull_request`: post a comment thread on a
  pull request, or reply to an existing thread via `--thread`. Commit comments
  are documented as unsupported (Azure DevOps exposes no REST endpoint for
  them).

- `azdo create --parent <id>` / `azdo_create_work_item(parent=...)`: create a
  work item directly under a parent (e.g. a Task under a User Story) in one
  call.
- `azdo get --relations` / `azdo_get_work_item(relations=True)`: return the
  item's relations (parent/child, related, dependency, hyperlink, attachment
  and commit/PR/branch links) as trimmed `{kind, target, ...}` dicts.
- `azdo unlink` (CLI) / `azdo_remove_work_item_link` (MCP + agent callable):
  remove a reference using the same kind/value pairs as `link`, enabling
  re-parenting and link cleanup.

- `azdo update` (CLI) / `azdo_update_work_item` (MCP + agent callable): change
  an existing work item's state (close/resolve), assignee, title, or
  description.
- New `azdo link` kinds for hierarchy and dependencies: `parent`, `child`,
  `predecessor`, `successor` (native Azure DevOps relations, enabling
  wayfinder-style dependency maps).
- `devops-utils setup tracker`: writes an Azure DevOps
  `docs/agents/issue-tracker.md` + `triage-labels.md` into a target repo so
  mattpocock-style skills use Azure DevOps work items via `devops-utils azdo`
  instead of the default GitHub `gh` CLI. Bundled templates live in
  `src/devops_utils/agent/trackers/`.
