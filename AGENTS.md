# AGENTS.md

## Installing skills

`devops-utils setup` installs the bundled skills into an agent's skills
directory, installs the bundled Claude Code subagents, and writes an Azure
DevOps env scaffold. `setup all` does those three; MCP-server registration is
opt-in (`setup all --with-mcp` or `setup mcp`) and defaults to the
zero-install `uvx --from "devops-utils[mcp]" devops-utils-mcp` launcher
(`--no-uvx` writes the on-PATH console script instead). `--project` scopes to
the current repo instead of `~/.claude`.
See `src/devops_utils/cli/commands/setup.py`.

`devops-utils setup agents` installs three read-only Azure DevOps research
subagents (`azdo-workitem-analyst`, `azdo-build-analyst`, `azdo-repo-analyst`)
as `agents/<name>.md`. Sources: `src/devops_utils/agent/agents/`.

`devops-utils setup tracker --project-name X` writes an Azure DevOps
`docs/agents/issue-tracker.md` + `triage-labels.md` into a target repo so
mattpocock-style skills drive Azure DevOps work items through `devops-utils azdo`
instead of the default `gh` CLI. Templates: `src/devops_utils/agent/trackers/`.

## Agent skills

### Azure DevOps work items

Create/comment/tag work items, add references (commit/PR/branch/work-item/hyperlink)
and attachments, list repos, and list/search work items — cloud + on-prem. Config
via env vars; no machine credentials. Skill: `src/devops_utils/agent/skills/azure-devops.md`;
reference: `docs/agents/azure-devops.md`.

### Azure DevOps research

Read-only status research: pending / assigned-to-me (`@Me`) / type+tag work-item
filters, build definitions and run status, failure diagnosis via timeline and
log tailing, and repo/file/code search.
Skill: `src/devops_utils/agent/skills/azure-devops-research.md`.

### Git history → work items

Mine the repository's git history (messages, diffs, authors, tags) into
per-year markdown Feature / User Story files — semantic grouping, commit
ranges, derived tags, `assigned_to` from authors — ready to push to Azure
DevOps via the work-items skill.
Skill: `src/devops_utils/agent/skills/git-history-workitems.md`.

### Issue tracker

Issues and PRDs are tracked in this repo's GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
