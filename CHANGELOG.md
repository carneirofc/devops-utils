# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **`setup mcp` writes the `uvx` launcher by default.** The registered
  `mcpServers` entry is now `uvx --from "devops-utils[mcp]" devops-utils-mcp`
  (zero-install; only `uv` must be present) instead of the bare
  `devops-utils-mcp` console script. `--no-uvx` restores the on-`PATH` entry
  for installed-package setups.
- **`setup all` no longer registers the MCP server by default.** The skills
  drive everything through `uvx`, so most setups need no server entry;
  registration is opt-in via `setup all --with-mcp` (or `setup mcp`). A skip
  line in the output points at the flag.

### Added

- **New bundled skill: `git-history-workitems`.** Mines the repository's git
  history — commit messages, diffs, authors, tags — into per-year markdown
  Feature / User Story files under `docs/workitems/history/<year>/`. Commits
  are grouped into Features semantically (subsystem + goal, not temporal
  proximity). The skill asks the user which language to write the content in
  before reading any history, and each story records its **exhaustive** commit
  list (hash + verbatim subject) so every commit can be linked to its work
  item. Each item carries derived tags, `first_commit`/`last_commit`,
  implementation status, the author roster, an `assigned_to` pick, and an
  empty `azure_devops_id` slot so a later push via the
  `azure-devops-work-items` skill can create Features, parent their User
  Stories, link commits, and update instead of duplicating on re-runs. Ships
  in `setup skills` and in the Claude Code plugin
  (`devops-utils:git-history-workitems`); committed plugin tree regenerated.

## [0.8.1] - 2026-07-30

### Changed

- **Skill docs cover every settable work-item field.** The bundled
  `azure-devops-work-items` skill (and the `docs/agents/azure-devops.md`
  reference) gained a *Scheduling* section documenting the fields no named
  parameter reaches — `Microsoft.VSTS.Scheduling.StartDate`/`.TargetDate`
  (the Delivery Plans pair), `.DueDate`, `.FinishDate`, `.Effort`,
  `.StoryPoints`, `.OriginalEstimate`/`.RemainingWork`/`.CompletedWork`, plus
  `Microsoft.VSTS.Common.Priority`/`.Severity`/`.BusinessValue` — with their
  types, the ISO-8601 value format, and CLI + Python examples. Also: a
  per-kind example for every `link` kind (including the re-parent
  unlink/link pair), create-time area/iteration examples, a full
  "scheduled Epic → Feature → Story" walkthrough, and an explicit note that
  `--field NAME=VALUE` sends strings while the `fields` dict preserves JSON
  types. Committed plugin tree regenerated to match.
- **`uvx` is the documented default way to run the tools.** README leads with
  `uvx --from "devops-utils[azure]" devops-utils azdo …` (and
  `uvx --from "devops-utils[mcp]" devops-utils-mcp`) before `pip install`,
  covers `uv tool install` and the `uvx`-based `mcpServers` entry to use
  instead of the `devops-utils-mcp`-on-`PATH` one that `setup mcp` writes. The
  bundled skills (`azure-devops-work-items`, `azure-devops-research`) and the
  Azure DevOps tracker template say the same, so an agent whose `PATH` has no
  `devops-utils` knows to prefix its commands rather than give up. The extra is
  called out as mandatory in each spot.

## [0.8.0] - 2026-07-29

### Added

- **`azdo get --full`.** Adds `rev` and a `fields` map of every raw field, keyed
  by reference name, on top of the trimmed shape — the way to read
  `System.Description`, `Microsoft.VSTS.Scheduling.*` dates, or a `Custom.*`
  value without hand-rolling a REST call. Custom fields have been *writable*
  since 0.7.0 (`--field NAME=VALUE`) but not readable; that asymmetry is gone.
  Composes with `--relations`; both come out of the response body already
  fetched, so there is no extra request and no REST `fields=` selector (which
  the server rejects alongside `$expand`). `list`/`search` stay trimmed by
  design. Also `azdo_get_work_item(..., full=True)` on the MCP/agent tools.

### Fixed

- **`UnicodeEncodeError` on Windows when CLI output is redirected.** A piped or
  redirected stdout defaults to the ANSI code page (`cp1252`), so echoing a
  work-item title containing `←`/`→` — or the CLI's own `(dry run — not
  applied)` — crashed the command mid-write. stdout/stderr are now reconfigured
  to UTF-8 with `errors="backslashreplace"` (`devops_utils.core.encoding`), so
  unencodable characters degrade to an escape sequence instead of raising.
- **No shell preamble is needed for accented text.** The hardening now runs from
  the `devops-utils` console script *before* Click parses `argv`, so eager
  options (`--help`, `--version`) that print during parsing are covered too, and
  `devops-utils-mcp` hardens its stderr log channel (its stdout/stdin carry
  framed JSON-RPC that the MCP SDK owns and must stay byte-exact, so those are
  deliberately left alone). `sanitize` also pins `encoding="utf-8"` on its
  manifest read and write instead of inheriting the platform default — reading a
  UTF-8 manifest as `cp1252` silently mojibaked non-secret values and wrote the
  corruption back out. Together these replace the
  `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` exports callers were using. (`chcp
  65001` was never part of the fix: a real Windows console writes through
  `WriteConsoleW` regardless of code page — only *redirected* streams ever
  crashed.)

  A `devops-utils` shim installed before this release has the old entry point
  baked in; re-run `uv tool upgrade devops-utils` (or `pip install -e .`) to
  pick up the pre-parse hardening.

### Changed

- **Write previews moved to stderr.** `azdo` write commands printed
  `About to write: {...}`, the `(dry run — not applied)` marker, and the
  `Apply this change?` prompt on stdout, ahead of the JSON result — so
  `azdo create … | jq` failed with `Invalid numeric literal` *after the write
  had already happened*, which invited double-creates on retry. stdout is now
  the JSON result and nothing else; `--dry-run` and a declined prompt leave it
  empty.

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
