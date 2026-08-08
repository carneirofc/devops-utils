# Wire it into an AI agent

Everything the CLI does is also available to an agent — as MCP tools, as
ready-made skills and subagents, or as plain Python callables. This page covers
getting an agent (Claude Code, primarily) talking to your Azure DevOps
organization.

## One command to set it all up

```bash
devops-utils setup all
```

That installs the bundled **skills**, the Claude Code **subagents**, and an
Azure DevOps **env scaffold**, defaulting to user scope (`~/.claude`). Nothing
needs to be installed first:

```bash
uvx --from "devops-utils[all]" devops-utils setup all
```

Registering the MCP server is **opt-in** — the skills drive the `devops-utils
azdo` CLI through `uvx`, so many setups need no server entry at all:

```bash
devops-utils setup all --with-mcp     # ... and register the MCP server
devops-utils setup all --project      # scope to this repo (./.claude, ./.mcp.json)
```

Individual steps, or an arbitrary directory:

```bash
devops-utils setup skills --dest ./agent-skills
devops-utils setup agents            # ~/.claude/agents/*.md
devops-utils setup mcp --dest .
devops-utils setup env
devops-utils setup tracker --project-name MyProject --done-state Closed
```

### Nothing is clobbered silently

When a target already exists, setup asks about it one item at a time:

```console
$ devops-utils setup all
wrote  ~/.claude/skills/azure-devops-research/SKILL.md
overwrite ~/.claude/agents/azdo-build-analyst.md? [y]es / [n]o / [a]ll / [q]uit / [d]iff: n
skip   ~/.claude/agents/azdo-build-analyst.md (kept existing)
```

`y` overwrites, `n` keeps, `a` overwrites all remaining, `q` stops asking and
keeps the rest, `d` shows a diff of the bundled version against yours first.
Files identical to the bundled copy are reported as `same` and never prompt. An
`a`/`q` answer carries across the remaining steps of `setup all`.

`--force` (or `-y`/`--yes`) answers yes to everything. Unattended runs — no
terminal, or `DEVOPS_UTILS_SKIP_CONFIRMATION` set — keep every existing file and
exit 0, so CI never blocks on a prompt or refreshes by surprise; pass `--force`
there if a refresh is what you want.

## What gets installed

### Skills

| Skill | For |
| --- | --- |
| `azure-devops` | Create, comment, tag, link and attach to work items |
| `azure-devops-research` | Read-only status research: pending items, build failures, repo search |
| `find-workitems` | Query recipes — by type, tag, `--parent`, area path |
| `setup-issue-tracker` | Guided, validated setup of a repo's tracker config |
| `git-history-workitems` | Mine git history into a Feature/Story backlog, ready for `azdo apply` |
| `sanitize` | Mask secrets in a Kubernetes manifest |

### Subagents

`setup agents` installs three **read-only** Azure DevOps research subagents for
Claude Code:

- **`azdo-workitem-analyst`** — pending items, assigned-to-me via the WIQL `@Me`
  macro, type/tag/state filters, following relations.
- **`azdo-build-analyst`** — definitions, run status by branch/result, failure
  diagnosis via timeline plus log tailing.
- **`azdo-repo-analyst`** — repo, file-path and code search.

They read; they never write. Writes stay with the main assistant, gated by the
MCP server's human confirmation.

## Registering the MCP server

`setup mcp` writes the zero-install `uvx` launcher — only `uv` has to be
present:

```json
{
  "mcpServers": {
    "devops-utils": {
      "command": "uvx",
      "args": ["--from", "devops-utils[mcp]", "devops-utils-mcp"],
      "env": {}
    }
  }
}
```

Pass `--no-uvx` to register the bare `devops-utils-mcp` console script instead
(requires `pip install "devops-utils[mcp]"` so it's on `PATH`). Existing
`mcpServers` entries for other servers are merged, not replaced, and an existing
`devops-utils` entry prompts first.

The server reads the same environment variables as the CLI
({doc}`install`) — the process that launches your agent must have them
exported, or put them in the entry's `env` block.

### Writes ask a human first

The MCP write tools (`azdo_create_work_item`, `azdo_update_work_item`,
`azdo_comment_work_item`, `azdo_set_work_item_tags`, `azdo_add_work_item_link`,
`azdo_remove_work_item_link`, `azdo_add_work_item_attachment`, `azdo_tag_build`,
`azdo_comment_pull_request`, `azdo_apply_plan`) describe the pending change and
apply it only when you accept the MCP **elicitation**. Declining writes nothing
and returns a `cancelled` status.

If the client can't prompt — elicitation unsupported, or a non-interactive run —
the write is **blocked** rather than silently applied, unless
`DEVOPS_UTILS_SKIP_CONFIRMATION` is truthy. Read tools are never gated.

## Use it as a Claude Code plugin

The same skills and subagents ship as a Claude Code **plugin** named
`devops-utils`, which namespaces them (`devops-utils:azure-devops-research`,
`devops-utils:azdo-workitem-analyst`, …) instead of installing bare names:

```text
/plugin marketplace add carneirofc/devops-utils
/plugin install devops-utils@carneirofc
/reload-plugins
```

(`carneirofc/devops-utils` is GitHub shorthand; a local checkout path works
too.)

The plugin ships **only** skills and agents. The subagents call the MCP tools
(`mcp__devops-utils__azdo_*`), so using them still needs
`devops-utils setup mcp`. The skills themselves work without it, driving the
CLI through `uvx`. MCP is deliberately not bundled: a plugin-scoped server would
rename those tools and break the agents that call them.

## Point issue-tracker skills at Azure DevOps

Skills in the style of [mattpocock/skills](https://github.com/mattpocock/skills)
(triage, wayfinder, to-tickets, …) read a repo-local config file,
`docs/agents/issue-tracker.md`, to learn how to talk to the issue tracker —
GitHub's `gh` CLI by default. To point them at Azure DevOps work items instead,
run in the target repo:

```bash
devops-utils setup tracker --project-name MyProject --done-state Closed \
  --org-url https://dev.azure.com/myorg \
  --parent-epic 1400 --area-path 'MyProject\MyTeam' --default-tag my-repo
```

This writes `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`,
mapping every tracker operation — create, comment, labels→tags, close, claim,
blocking links, PR references — onto `devops-utils azdo` and the `azdo_*` MCP
tools.

- `--done-state` is whatever "closed" is called in your process template
  (`Closed`, `Done`, `Resolved`, …).
- The optional org URL, parent Epic, area path and repeatable default tags land
  in a *Defaults for this repo* table that agents apply on every create and
  query. New items land under the right Epic with the right area and tags, and
  "what's pending?" searches surface this repo's items first.

For a guided flow that asks for each value and validates it against the live
organization, use the bundled `setup-issue-tracker` skill. The
`find-workitems` skill holds the matching query recipes.

## Without an agent framework

The tools are plain Python functions — no MCP, no framework:

```python
from devops_utils.agent import tools

builds = tools.azdo_list_builds("MyProject", branch="main", results=["failed"], top=5)
timeline = tools.azdo_get_build_timeline("MyProject", builds[0]["id"])
```

Their docstrings are written to be read by an LLM, so they register cleanly with
whatever tool-calling layer you already use. Full signatures are in the
{doc}`API reference <../api/devops_utils.agent.tools>`.
