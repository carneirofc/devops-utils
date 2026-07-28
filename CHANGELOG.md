# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Skills and subagents now prescribe the `Epic → Feature → User Story`
  backlog pattern.** `azure-devops-work-items` gains a hierarchy section
  (create top-down with `parent`, never orphan a Feature/Story, per-process
  type mapping for Scrum/CMMI/Basic); `azure-devops-research` and
  `azdo-workitem-analyst` gain the read-side counterpart (walk `parent`/`child`
  relations, roll status up, flag hierarchy breaks). Plugin tree regenerated.

## [0.7.0] - 2026-07-28

### Added

- **Area path / iteration path support.** `azdo create`/`update` set
  `System.AreaPath`/`System.IterationPath` via `--area-path`/`--iteration-path`;
  `azdo list`/`search` filter by them (WIQL `UNDER`, matching the node and
  everything nested under it). Same params on the `azdo_*` MCP/agent tools.
- **Custom field support.** `azdo create`/`update` accept arbitrary
  process-/org-specific fields via repeatable `--field NAME=VALUE` (CLI) or a
  `fields` dict (`azdo_create_work_item`/`azdo_update_work_item`), keyed by
  field reference name.

### Changed

- **Work items now return `area_path` and `iteration_path`.** The trimmed
  work-item shape gains both fields, so callers can read an item's area/sprint
  instead of only filtering by them.
- Skills, subagent instructions, and docs updated for the new parameters; the
  `azure-devops-work-items` skill's human-in-the-loop section was also
  corrected — it still described seven gated MCP tools and an ungated CLI,
  both superseded in 0.6.0.

## [0.6.0] - 2026-07-28

### Added

- **CLI write confirmation.** `devops-utils azdo` write commands (`create`,
  `comment`, `tag`, `update`, `link`, `unlink`, `build-tag`, `pr-comment`,
  `attach`) now preview the pending change and prompt for confirmation before
  calling Azure DevOps. Use `--yes`/`-y` to skip the prompt or `--dry-run` to
  preview without applying; `DEVOPS_UTILS_SKIP_CONFIRMATION` also skips it.

### Changed

- **MCP write gate now covers all nine write tools.** `azdo_tag_build` and
  `azdo_comment_pull_request` previously bypassed the MCP human-confirmation
  gate; they're now wrapped the same as the other seven work-item writes.
  The shared `DEVOPS_UTILS_SKIP_CONFIRMATION` check moved to
  `devops_utils.core.confirmation` so the CLI and MCP server use one
  implementation.

## [0.5.0] - 2026-07-24

### Added

- **Claude Code plugin packaging.** The bundled skills and subagents now also
  ship as a plugin named `devops-utils`, so Claude Code lists them namespaced
  (`devops-utils:azure-devops-research`, `devops-utils:azdo-workitem-analyst`, …)
  instead of under bare names. A new `devops-utils setup plugin` command
  generates the committed plugin tree (`plugins/devops-utils/`) and a bundled
  marketplace (`.claude-plugin/marketplace.json`); install with
  `/plugin marketplace add carneirofc/devops-utils` then
  `/plugin install devops-utils@carneirofc`. The MCP server is deliberately not
  bundled (a plugin-scoped server would rename the `mcp__devops-utils__azdo_*`
  tools the agents call) — MCP stays wired via `setup mcp`.

### Changed

- `azdo-workitem-analyst` agent pinned to `model: sonnet` for predictable
  work-item research behavior regardless of the main conversation's model.
- Expanded the `azure-devops-research` and `sanitize-manifest` skills with
  concrete worked examples (CLI + Python calls with realistic inputs/outputs)
  to match the completeness of the `azure-devops-work-items` skill.

## [0.4.0] - 2026-07-22

### Added

- Bundled **Claude Code subagents** for read-only Azure DevOps research,
  installed by the new `devops-utils setup agents` subcommand (also part of
  `setup all`): `azdo-workitem-analyst` (work-item status, pending items,
  assigned-to-me, type/tag filters), `azdo-build-analyst` (pipeline
  definitions, run status, failure diagnosis), and `azdo-repo-analyst`
  (repo/file/code search). Sources: `src/devops_utils/agent/agents/*.md`.
- Build introspection tools across CLI/MCP/agent surfaces:
  `azdo_list_build_definitions` (`azdo definitions`), `azdo_get_build_timeline`
  (`azdo timeline` — stages/jobs/tasks with results, error/warning issues, and
  log ids), `azdo_list_build_logs` (`azdo logs` — log ids + line counts), and
  `azdo_get_build_log` (`azdo log` — plain-text content with optional
  `start_line`/`end_line` for tailing large logs).
- Work-item research filters: `tags` on list and search (AND semantics,
  repeatable `--tag`), `assigned_to` on search, and the WIQL `@Me` macro —
  `assigned_to="@Me"` / `--mine` — resolving "assigned to me" server-side
  without a configured email.
- Repository search tiers: `name_filter` on `azdo_list_repositories`
  (`azdo repos --name`), `azdo_find_repo_files` (`azdo files` — path-glob
  search via the Git Items API, no extension needed), and `azdo_code_search`
  (`azdo code-search` — content search via the Search extension; the cloud
  `almsearch` host is derived automatically and servers without the extension
  get a clear error pointing at the fallback).
- New skill `azure-devops-research` with read-only research playbooks (my
  pending items, build failure diagnosis, repo/file/code search) installed by
  `setup skills`.

## [0.3.0] - 2026-07-21

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

### Changed

- CI: bump `actions/checkout@v4` → `@v5` and `astral-sh/setup-uv@v3` → `@v7`
  across the lint, security and deploy workflows, moving them onto Node 24 and
  clearing the Node 20 deprecation warnings.
- Pre-commit: bump hooks to match the project toolchain — `pre-commit-hooks`
  `v4.6.0` → `v6.0.0`, `ruff-pre-commit` `v0.6.9` → `v0.15.22`, `mirrors-mypy`
  `v1.11.2` → `v2.3.0`, and rename the deprecated `ruff` hook id to
  `ruff-check`. Aligns local formatting/linting with CI and fixes the version
  drift that let pre-commit-formatted code fail the CI `ruff format --check`.
