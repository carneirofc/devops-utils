Description
-----------

![Linting and Static](https://github.com/carneirofc/devops-utils/actions/workflows/lint.yml/badge.svg)
![Latest tag](https://img.shields.io/github/tag/carneirofc/devops-utils.svg?style=flat)
[![Latest release](https://img.shields.io/github/release/carneirofc/devops-utils.svg?style=flat)](https://github.com/carneirofc/devops-utils/releases)
[![PyPI version fury.io](https://badge.fury.io/py/devops-utils.svg)](https://pypi.python.org/pypi/devops-utils/)
[![Read the Docs](https://readthedocs.org/projects/spack/badge/?version=latest)](https://carneirofc.github.io/devops-utils/)

A set of utility tools for DevOps, built around a dependency-free core that is
exposed through several optional surfaces: a **CLI**, a **Qt UI**, a **TUI**, an
**MCP server**, **agent tools**, and a **Claude Code plugin**.

Requires Python 3.12+.


Install
-------

```bash
# core + CLI
pip install devops-utils

# with optional surfaces
pip install "devops-utils[mcp]"   # MCP server
pip install "devops-utils[tui]"   # Textual TUI
pip install "devops-utils[qt]"    # PySide6 desktop UI
pip install "devops-utils[azure]" # Azure DevOps work-item tools
pip install "devops-utils[all]"   # everything
```

For development this project uses [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras --dev
```


Usage
-----

```bash
# Mask Secret values in a Kubernetes manifest, print to stdout
devops-utils sanitize manifest.yml -o -

# Write the sanitized manifest to a file
devops-utils sanitize manifest.yml -o manifest.sanitized.yml
```

Run the MCP server (requires the `mcp` extra):

```bash
devops-utils-mcp
```


Azure DevOps work items
-----------------------

A small, LLM-friendly interface to Azure DevOps work items, working against both
**Services (cloud)** and **Server (on-prem)**. Requires the `azure` extra.

Credentials are **never** read from the machine — supply a bearer token (or PAT)
out-of-band via environment variables:

```bash
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/your-org"   # or on-prem: https://server/tfs/DefaultCollection
export AZURE_DEVOPS_TOKEN="<bearer-token-or-pat>"
export AZURE_DEVOPS_AUTH_SCHEME="bearer"   # or "pat" for a raw Personal Access Token
export AZURE_DEVOPS_API_VERSION="7.1"      # lower for older on-prem servers
```

```bash
devops-utils azdo repos --project MyProject --name api
devops-utils azdo list --project MyProject --state Active --type Bug
devops-utils azdo list --project MyProject --mine --tag backend   # @Me macro
devops-utils azdo search --project MyProject "login timeout"
devops-utils azdo create --project MyProject --type Task --title "Fix flaky test"
devops-utils azdo update 42 --state Closed --assigned-to dev@example.com
devops-utils azdo comment 42 "Investigating."
devops-utils azdo tag 42 backend urgent
devops-utils azdo link 42 --kind commit --project MyProject --repo MyRepo --value <sha>
devops-utils azdo attach 42 ./trace.log
```

Pipeline and repository research (read-only):

```bash
devops-utils azdo definitions --project MyProject --name 'CI*'
devops-utils azdo builds --project MyProject --branch main --result failed
devops-utils azdo timeline 1234 --project MyProject     # stages/tasks + errors
devops-utils azdo logs 1234 --project MyProject          # log ids + line counts
devops-utils azdo log 1234 7 --project MyProject --start-line 800   # tail
devops-utils azdo files --project MyProject --repo MyRepo --pattern '*.yml'
devops-utils azdo code-search "connection pool" --project MyProject
```

`code-search` uses the Search extension (always available on cloud; on-prem
needs it installed — `files` is the portable fallback).

The same operations are exposed as MCP tools (`azdo_*`) and framework-agnostic
agent callables in `devops_utils.agent.tools`, all reading the env vars above.


Set up an agent
---------------

`devops-utils setup` installs the bundled skills and Claude Code subagents,
wires the `devops-utils-mcp` server into an agent's MCP config, and writes an
Azure DevOps env scaffold. Defaults target Claude Code at user scope
(`~/.claude`).

```bash
# Everything, for the current user (skills + agents + MCP server + env scaffold)
devops-utils setup all

# Scope to the current repo (./.claude, ./.mcp.json)
devops-utils setup all --project

# Individual steps, or an arbitrary directory
devops-utils setup skills --dest ./agent-skills
devops-utils setup agents          # ~/.claude/agents/*.md
devops-utils setup mcp --dest .
devops-utils setup env
```

`setup agents` installs three **read-only** Azure DevOps research subagents
for Claude Code — `azdo-workitem-analyst` (pending items, assigned-to-me via
the WIQL `@Me` macro, type/tag filters), `azdo-build-analyst` (definitions,
run status, failure diagnosis via timeline + log tailing), and
`azdo-repo-analyst` (repo/file/code search). Writes stay with the main
assistant, gated by the MCP server's human confirmation.

Use `--force` to overwrite existing files; `setup mcp` merges into any existing
config without clobbering other servers.


Use as a Claude Code plugin
---------------------------

The same skills and subagents also ship as a **Claude Code plugin** named
`devops-utils`, so Claude Code lists them under a distinguishing namespace —
`devops-utils:azure-devops-research`, `devops-utils:azdo-workitem-analyst`, and
so on — instead of bare, unqualified names. Install it from this repo's bundled
marketplace:

```text
/plugin marketplace add carneirofc/devops-utils
/plugin install devops-utils@carneirofc
/reload-plugins
```

(`carneirofc/devops-utils` is GitHub shorthand; a local checkout path works too:
`/plugin marketplace add /path/to/devops-utils`.)

The plugin ships only the skills and agents. Their Azure DevOps **MCP tools**
(`mcp__devops-utils__azdo_*`) still come from the `devops-utils-mcp` server, so a
working setup also needs `pip install "devops-utils[mcp]"` and
`devops-utils setup mcp`. MCP is intentionally not bundled in the plugin: a
plugin-scoped server would rename those tools and break the agents that call
them.

The committed plugin tree (`plugins/devops-utils/`, `.claude-plugin/marketplace.json`)
is generated from the bundled sources; re-run `devops-utils setup plugin --force`
after changing a skill or agent (a test enforces they stay in sync).


Use with mattpocock/skills
--------------------------

Skills like [mattpocock/skills](https://github.com/mattpocock/skills) (triage,
wayfinder, to-tickets, …) read a repo-local config file,
`docs/agents/issue-tracker.md`, to learn how to talk to the issue tracker —
GitHub's `gh` CLI by default. To point them at **Azure DevOps work items**
via devops-utils instead, run in the target repo:

```bash
devops-utils setup tracker --project-name MyProject --done-state Closed
```

This writes `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`
mapping every tracker operation (create, comment, labels→tags, close, claim,
blocking links, PR references) to `devops-utils azdo` / the `azdo_*` MCP tools.
`--done-state` is the state meaning "closed" in your process template
(`Closed`, `Done`, `Resolved`, …).


Author
------

Cláudio Ferreira Carneiro - carneirofc @ claudiofcarneiro@gmail.com


Licence
-------

devops-utils is licensed under the MIT License. See [LICENSE](LICENSE).
