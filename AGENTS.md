# AGENTS.md

## Installing skills

`devops-utils setup` installs the bundled skills into an agent's skills
directory, registers the `devops-utils-mcp` server, and writes an Azure DevOps
env scaffold. `setup all` does all three; `--project` scopes to the current repo
instead of `~/.claude`. See `src/devops_utils/cli/commands/setup.py`.

## Agent skills

### Azure DevOps work items

Create/comment/tag work items, add references (commit/PR/branch/work-item/hyperlink)
and attachments, list repos, and list/search work items — cloud + on-prem. Config
via env vars; no machine credentials. Skill: `src/devops_utils/agent/skills/azure-devops.md`;
reference: `docs/agents/azure-devops.md`.

### Issue tracker

Issues and PRDs are tracked in this repo's GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
