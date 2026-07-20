# AGENTS.md

## Agent skills

### Azure DevOps work items

Create/comment/tag work items, add references (commit/PR/branch/work-item/hyperlink)
and attachments, list repos, and list/search work items — cloud + on-prem. Config
via env vars; no machine credentials. See `docs/agents/azure-devops.md`.

### Issue tracker

Issues and PRDs are tracked in this repo's GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
