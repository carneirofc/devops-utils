# AGENTS.md

## Installing skills

`devops-utils setup` installs the bundled skills into an agent's skills
directory, registers the `devops-utils-mcp` server, and writes an Azure DevOps
env scaffold. `setup all` does all three; `--project` scopes to the current repo
instead of `~/.claude`. See `src/devops_utils/cli/commands/setup.py`.

`devops-utils setup tracker --project-name X` writes an Azure DevOps
`docs/agents/issue-tracker.md` + `triage-labels.md` into a target repo so
mattpocock-style skills drive Azure DevOps work items through `devops-utils azdo`
instead of the default `gh` CLI. Templates: `src/devops_utils/agent/trackers/`.

## MCP server

`src/devops_utils/mcp/server.py` targets the MCP Python SDK v2 (`mcp>=2`):
`from mcp.server import MCPServer`. The v1 `mcp.server.fastmcp.FastMCP` path no
longer exists. Tools are registered from `devops_utils.agent.tools`. When you
add or remove a tool, update the count in `tests/test_mcp_server.py`.

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

## Verification

Run the same checks CI runs (`.github/workflows/lint.yml`, `security.yml`):

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check . && uv run ruff format --check .   # ruff also formats Python blocks in .md
uv run mypy
uv run bandit -r src
uv run pre-commit run --all-files                   # also type-checks docs/conf.py
```

## Child Index

No child AGENTS.md files. The package is small enough for this root doc to own
the whole tree.
