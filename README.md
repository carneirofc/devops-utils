Description
-----------

![Linting and Static](https://github.com/carneirofc/devops-utils/actions/workflows/lint.yml/badge.svg)
![Latest tag](https://img.shields.io/github/tag/carneirofc/devops-utils.svg?style=flat)
[![Latest release](https://img.shields.io/github/release/carneirofc/devops-utils.svg?style=flat)](https://github.com/carneirofc/devops-utils/releases)
[![PyPI version fury.io](https://badge.fury.io/py/devops-utils.svg)](https://pypi.python.org/pypi/devops-utils/)
[![Read the Docs](https://readthedocs.org/projects/spack/badge/?version=latest)](https://carneirofc.github.io/devops-utils/)

A set of utility tools for DevOps, built around a dependency-free core that is
exposed through several optional surfaces: a **CLI**, a **Qt UI**, a **TUI**, an
**MCP server**, and **agent tools**.

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
devops-utils azdo repos --project MyProject
devops-utils azdo list --project MyProject --state Active --type Bug
devops-utils azdo search --project MyProject "login timeout"
devops-utils azdo create --project MyProject --type Task --title "Fix flaky test"
devops-utils azdo comment 42 "Investigating."
devops-utils azdo tag 42 backend urgent
devops-utils azdo link 42 --kind commit --project MyProject --repo MyRepo --value <sha>
devops-utils azdo attach 42 ./trace.log
```

The same operations are exposed as MCP tools (`azdo_*`) and framework-agnostic
agent callables in `devops_utils.agent.tools`, all reading the env vars above.


Author
------

Cláudio Ferreira Carneiro - carneirofc @ claudiofcarneiro@gmail.com


Licence
-------

devops-utils is licensed under the MIT License. See [LICENSE](LICENSE).
