Description
-----------

![Linting and Static](https://github.com/carneirofc/devops-utils/actions/workflows/lint.yml/badge.svg)
![Latest tag](https://img.shields.io/github/tag/carneirofc/devops-utils.svg?style=flat)
[![Latest release](https://img.shields.io/github/release/carneirofc/devops-utils.svg?style=flat)](https://github.com/carneirofc/devops-utils/releases)
[![PyPI version fury.io](https://badge.fury.io/py/devops-utils.svg)](https://pypi.python.org/pypi/devops-utils/)
[![Documentation](https://img.shields.io/badge/docs-github.io-blue.svg?style=flat)](https://carneirofc.github.io/devops-utils/)

A set of utility tools for DevOps, built around a dependency-free core that is
exposed through several optional surfaces: a **CLI**, an **MCP server**,
**agent tools**, a **Claude Code plugin**, a **TUI**, and a **Qt UI**.

Two things it does today:

- **Azure DevOps, made scriptable and agent-friendly** — work items, builds,
  repositories and pull requests over plain REST, on cloud and on-prem alike,
  with clean JSON on stdout and a human confirmation in front of every write.
- **Kubernetes manifest sanitizing** — mask every `Secret` value so a manifest
  can be pasted into a ticket, a chat, or an LLM prompt.

Requires Python 3.12+.

📖 **Full documentation: <https://carneirofc.github.io/devops-utils/>**


Install
-------

**Recommended — no install at all.** With [uv](https://docs.astral.sh/uv/),
`uvx` fetches the package and the extra you name into a cached, throwaway
environment per invocation:

```bash
uvx --from "devops-utils[azure]" devops-utils azdo list --project MyProject --mine
uvx --from "devops-utils[mcp]" devops-utils-mcp          # MCP server
uvx --from "devops-utils[all]" devops-utils --help       # every surface
```

The extra is not optional: `azdo` needs `[azure]`, the MCP server needs `[mcp]`,
and `[all]` covers everything. Or install it the usual way:

```bash
pip install "devops-utils[all]"        # or [azure] / [mcp] / [tui] / [qt]
uv tool install "devops-utils[all]"    # isolated, always on PATH
```

Details, the full extras table, and Azure DevOps credential setup:
[Install and configure](https://carneirofc.github.io/devops-utils/guide/install.html).


A quick taste
-------------

```bash
# Mask every Secret value in a Kubernetes manifest, print to stdout
devops-utils sanitize manifest.yml -o -

# What's assigned to me and still open?
devops-utils azdo list --project MyProject --mine --state Active

# Why did the last build on main fail?
devops-utils azdo builds --project MyProject --branch main --result failed --top 1
devops-utils azdo timeline 1234 --project MyProject

# File a bug under an Epic, linked to the offending commit
devops-utils azdo create --project MyProject --type Bug --parent 1400 \
  --title "Checkout times out at 30s" --tag payments
devops-utils azdo link 42 --kind commit --project MyProject --repo MyRepo --value 0a1b2c3d

# Create a whole Feature/Story/Task tree from one plan file
devops-utils azdo apply plan.yml --dry-run

# Install the bundled agent skills and Claude Code subagents
devops-utils setup all
```

Azure DevOps access is configured entirely through environment variables
(`AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_TOKEN`, …) — no credentials are ever read
from the machine.


Documentation
-------------

| Guide | What's in it |
| --- | --- |
| [Install and configure](https://carneirofc.github.io/devops-utils/guide/install.html) | Extras, `uvx`, cloud + on-prem credential setup |
| [Azure DevOps from the command line](https://carneirofc.github.io/devops-utils/guide/azure-devops.html) | Cookbook: finding work, changing work, diagnosing pipelines, repo search, `jq` recipes |
| [Bulk work items with a plan file](https://carneirofc.github.io/devops-utils/guide/bulk-plans.html) | `azdo apply` — hierarchies, links and comments in one reviewed batch |
| [Sanitize Kubernetes manifests](https://carneirofc.github.io/devops-utils/guide/sanitize.html) | Masking Secrets, and what to do with the result |
| [Wire it into an AI agent](https://carneirofc.github.io/devops-utils/guide/agents.html) | `setup`, MCP server, bundled skills and subagents, the Claude Code plugin, issue-tracker config |
| [Reference](https://carneirofc.github.io/devops-utils/agents/azure-devops.html) | Every parameter, link kind, field name and API detail |
| [API reference](https://carneirofc.github.io/devops-utils/api/devops_utils.html) | Generated from the source |


Use as a Claude Code plugin
---------------------------

The bundled skills and read-only Azure DevOps subagents also ship as a Claude
Code plugin, namespaced as `devops-utils:*`:

```text
/plugin marketplace add carneirofc/devops-utils
/plugin install devops-utils@carneirofc
/reload-plugins
```

The subagents call the MCP tools, so they also need
`devops-utils setup mcp` — see
[Wire it into an AI agent](https://carneirofc.github.io/devops-utils/guide/agents.html).


Development
-----------

```bash
uv sync --all-extras --dev
uv run pytest
uv run sphinx-build -W --keep-going -b html docs _site   # build the docs
```

The committed plugin tree (`plugins/devops-utils/`,
`.claude-plugin/marketplace.json`) is generated from the bundled sources;
re-run `devops-utils setup plugin --force` after changing a skill or agent (a
test enforces they stay in sync).


Author
------

Cláudio Ferreira Carneiro - carneirofc @ claudiofcarneiro@gmail.com


Licence
-------

devops-utils is licensed under the MIT License. See [LICENSE](LICENSE).
