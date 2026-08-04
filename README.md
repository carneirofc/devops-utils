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

**Recommended — no install at all.** With [uv](https://docs.astral.sh/uv/),
`uvx` fetches the package (and the extra you name) into a cached, throwaway
environment per invocation:

```bash
uvx --from "devops-utils[azure]" devops-utils azdo list --project MyProject --mine
uvx --from "devops-utils[mcp]" devops-utils-mcp          # MCP server
uvx --from "devops-utils[all]" devops-utils --help       # every surface
```

The extra is not optional: `azdo` needs `[azure]`, the MCP server needs
`[mcp]`, and `[all]` covers everything. Pin it for reproducibility
(`"devops-utils[azure]==0.8.0"`). Worth an alias if you use it often:

```bash
alias devops-utils='uvx --from "devops-utils[all]" devops-utils'
```

Or install it the usual way:

```bash
# core + CLI
pip install devops-utils

# with optional surfaces
pip install "devops-utils[mcp]"   # MCP server
pip install "devops-utils[tui]"   # Textual TUI
pip install "devops-utils[qt]"    # PySide6 desktop UI
pip install "devops-utils[azure]" # Azure DevOps work-item tools
pip install "devops-utils[all]"   # everything

# or as an isolated, always-on-PATH tool
uv tool install "devops-utils[all]"
```

For development this project uses uv:

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
# or, without installing:
uvx --from "devops-utils[mcp]" devops-utils-mcp
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
devops-utils azdo list --project MyProject --iteration-path 'MyProject\Sprint 3'
devops-utils azdo search --project MyProject "login timeout"
devops-utils azdo get 42 --full        # every raw field: description, dates, Custom.*
devops-utils azdo create --project MyProject --type Task --title "Fix flaky test" \
  --area-path 'MyProject\Payments' --field Custom.RiskLevel=High
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

### Bulk operations: `azdo apply`

`azdo apply` creates and updates many work items from one declarative
**plan file** (YAML or JSON) — hierarchy, links, comments and all — with a
single review-and-confirm step instead of one prompt per command:

```bash
devops-utils azdo apply plan.yml            # preview, confirm once, apply
devops-utils azdo apply plan.yml --dry-run  # preview only, change nothing
devops-utils azdo apply plan.yml --yes --out results.json
cat plan.yml | devops-utils azdo apply -    # read the plan from stdin
```

A plan is a `project`, optional `defaults` merged into every item, and an
ordered list of `items`. An item without `id` is a **create**; with `id` it is
an **update**. Later items can point at earlier ones with `ref:<name>`:

```yaml
project: MyProject
defaults:
  area_path: MyProject\Platform
  fields:                      # any field by reference name, incl. Custom.*
    Custom.Source: git-history
items:
  - ref: feat                  # name other items can reference
    type: Feature
    title: Payment retries
    state: Closed              # applied after create (state machines allow it)
    tags: [payments, backend]
  - type: User Story
    title: Retry failed captures
    parent: ref:feat           # parented under the feature created above
    assigned_to: dev@example.com
    links:
      - {kind: commit, repo: MyRepo, value: 0a1b2c3d}
      - {kind: hyperlink, value: "https://wiki/retries"}
    comments: ["Imported from git history."]
  - id: 42                     # existing item -> update
    state: Resolved
    fields: {Custom.RiskLevel: Low}
```

The schema is deliberately loose: named keys cover the common fields, anything
else goes under `fields:` by reference name (unknown top-level keys produce a
warning in the preview, not an error). All of an item's links are sent in one
request; failures don't stop the run (dependents of a failed `ref` fail with a
clear message; use `--stop-on-error` to halt instead). Per-item results —
`created` / `updated` / `failed` / `skipped` plus the new ids — are printed as
JSON on stdout, and the exit code is non-zero if anything failed.

The same engine is exposed as the `azdo_apply_plan` MCP/agent tool, gated by
the usual human confirmation.

Results are JSON on stdout and nothing else — write commands send their preview
and confirmation prompt to stderr — so `devops-utils azdo get 42 --full | jq`
works. Output is UTF-8 whatever the shell's code page, so accented text needs no
`chcp` / `PYTHONUTF8` preamble.

The same operations are exposed as MCP tools (`azdo_*`) and framework-agnostic
agent callables in `devops_utils.agent.tools`, all reading the env vars above.


Set up an agent
---------------

`devops-utils setup` installs the bundled skills and Claude Code subagents and
writes an Azure DevOps env scaffold. Defaults target Claude Code at user scope
(`~/.claude`). Registering the MCP server is **opt-in** (`--with-mcp` /
`setup mcp`) — the skills run every command through `uvx`, so most setups need
no server entry at all.

```bash
# Skills + agents + env scaffold, for the current user
devops-utils setup all
# same thing without installing:
uvx --from "devops-utils[all]" devops-utils setup all

# ... also registering the MCP server
devops-utils setup all --with-mcp

# Scope to the current repo (./.claude, ./.mcp.json)
devops-utils setup all --project

# Individual steps, or an arbitrary directory
devops-utils setup skills --dest ./agent-skills
devops-utils setup agents          # ~/.claude/agents/*.md
devops-utils setup mcp --dest .
devops-utils setup env
```

`setup mcp` registers the zero-install `uvx` launcher by default — only `uv`
needs to be present:

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
(requires `pip install "devops-utils[mcp]"` so it is on `PATH`).

`setup agents` installs three **read-only** Azure DevOps research subagents
for Claude Code — `azdo-workitem-analyst` (pending items, assigned-to-me via
the WIQL `@Me` macro, type/tag filters), `azdo-build-analyst` (definitions,
run status, failure diagnosis via timeline + log tailing), and
`azdo-repo-analyst` (repo/file/code search). Writes stay with the main
assistant, gated by the MCP server's human confirmation.

Nothing is clobbered silently. When a target already exists, setup asks about it
one item at a time — `y` (overwrite), `n` (keep), `a` (overwrite all remaining),
`q` (stop asking and keep the rest), or `d` to see a diff of the bundled version
against yours first. Files identical to the bundled copy are reported as `same`
and never prompt.

```console
$ devops-utils setup all
wrote  ~/.claude/skills/azure-devops-research/SKILL.md
overwrite ~/.claude/agents/azdo-build-analyst.md? [y]es / [n]o / [a]ll / [q]uit / [d]iff: n
skip   ~/.claude/agents/azdo-build-analyst.md (kept existing)
```

`--force` (or `-y`/`--yes`) answers yes to everything and prompts for nothing.
An answer of `a`/`q` during `setup all` carries across its remaining steps.
Unattended runs — no terminal, or `DEVOPS_UTILS_SKIP_CONFIRMATION` set — keep
every existing file and exit 0, so CI never blocks on a prompt or overwrites by
surprise; pass `--force` there if you do want a refresh.

`setup mcp` prompts before replacing an existing `mcpServers.devops-utils`
entry and merges into any existing config without clobbering other servers.


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

The plugin ships only the skills and agents. The bundled **subagents** call the
Azure DevOps MCP tools (`mcp__devops-utils__azdo_*`), so using them needs the
server registered — `devops-utils setup mcp` writes the `uvx`-launched entry
shown under *Set up an agent*. The skills themselves work without it (they
drive the `devops-utils azdo` CLI via `uvx`). MCP is intentionally not bundled in the plugin: a
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
devops-utils setup tracker --project-name MyProject --done-state Closed \
  --org-url https://dev.azure.com/myorg \
  --parent-epic 1400 --area-path 'MyProject\MyTeam' --default-tag my-repo
```

This writes `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`
mapping every tracker operation (create, comment, labels→tags, close, claim,
blocking links, PR references) to `devops-utils azdo` / the `azdo_*` MCP tools.
`--done-state` is the state meaning "closed" in your process template
(`Closed`, `Done`, `Resolved`, …). The optional org URL / parent Epic /
area path / default tags (all repeatable-flag or omit-for-fallback) land in a
"Defaults for this repo" table that agents apply on every create and query —
new items go under the right Epic with the right area/tags, and
pending-issue searches are scoped so this repo's items surface first. For a
guided flow that asks for each value and validates it against the live
organization, use the bundled `setup-issue-tracker` skill; the
`azure-devops-find-workitems` skill holds the matching query recipes
(by type, tags, `--parent`, area path).


Author
------

Cláudio Ferreira Carneiro - carneirofc @ claudiofcarneiro@gmail.com


Licence
-------

devops-utils is licensed under the MIT License. See [LICENSE](LICENSE).
