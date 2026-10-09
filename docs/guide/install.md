# Install and configure

devops-utils is a small core with several optional surfaces bolted on: a CLI, an
MCP server, a Textual TUI, a Qt desktop UI, framework-agnostic agent callables,
and a Claude Code plugin. You install only the surfaces you use.

Requires **Python 3.12+**.

## The fastest path: no install at all

With [uv](https://docs.astral.sh/uv/) present, `uvx` fetches the package and the
extra you name into a cached, throwaway environment per invocation:

```bash
uvx --from "devops-utils[azure]" devops-utils azdo list --project MyProject --mine
uvx --from "devops-utils[mcp]" devops-utils-mcp          # MCP server
uvx --from "devops-utils[all]" devops-utils --help       # every surface
```

The extra is **not** optional — `azdo` needs `[azure]`, the MCP server needs
`[mcp]`, and `[all]` covers everything. Pin it when reproducibility matters:

```bash
uvx --from "devops-utils[azure]==0.11.0" devops-utils azdo list --project MyProject
```

If you reach for it often, an alias pays for itself:

```bash
alias devops-utils='uvx --from "devops-utils[all]" devops-utils'
```

## Installing it properly

```bash
pip install devops-utils              # core + CLI (sanitize, setup)

pip install "devops-utils[azure]"     # Azure DevOps work items, builds, repos
pip install "devops-utils[mcp]"       # MCP server
pip install "devops-utils[tui]"       # Textual TUI
pip install "devops-utils[qt]"        # PySide6 desktop UI
pip install "devops-utils[all]"       # everything

uv tool install "devops-utils[all]"   # isolated, always on PATH
```

| Extra | Pulls in | Unlocks |
| --- | --- | --- |
| *(none)* | `pyyaml`, `click` | `devops-utils sanitize`, `devops-utils setup` |
| `azure` | `httpx` | `devops-utils azdo …`, the `azdo_*` agent callables |
| `mcp` | `mcp` | the `devops-utils-mcp` server |
| `tui` | `textual` | the `devops-utils-tui` TUI |
| `qt` | `PySide6` | the `devops-utils-qt` desktop UI |
| `all` | all of the above | every surface |

For working on devops-utils itself:

```bash
uv sync --all-extras --dev
```

## Configuring Azure DevOps access

Credentials are **never** read from the machine — no `az` CLI, no credential
files, no Windows credential store. Every surface (CLI, MCP server, agent
callables) reads the same four environment variables:

```bash
export AZURE_DEVOPS_ORG_URL="https://dev.azure.com/your-org"
export AZURE_DEVOPS_TOKEN="<bearer-token-or-pat>"
export AZURE_DEVOPS_AUTH_SCHEME="bearer"   # or "pat" for a raw Personal Access Token
export AZURE_DEVOPS_API_VERSION="7.1"      # lower it for older on-prem servers
```

On-premises Azure DevOps Server works the same way; point the URL at the
collection instead:

```bash
export AZURE_DEVOPS_ORG_URL="https://tfs.example.com/tfs/DefaultCollection"
export AZURE_DEVOPS_AUTH_SCHEME="pat"
export AZURE_DEVOPS_API_VERSION="6.0"
```

### Env file (recommended on Windows)

Instead of exporting variables, put them in an env file. The CLI and the MCP
server load the **first existing** one of:

1. the path in `DEVOPS_UTILS_ENV_FILE`
2. `./.env.devops-utils` — project scope; add it to `.gitignore`
3. `~/.devops-utils.env` — user scope (`%USERPROFILE%\.devops-utils.env` on
   Windows)

```text
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_TOKEN=<bearer-token-or-pat>
AZURE_DEVOPS_AUTH_SCHEME=pat
```

Real environment variables always win, files are never merged, and only
`AZURE_DEVOPS_*` keys are read. An org URL from a file is ignored unless the
token in effect comes from the same file, so a cloned repository's
`.env.devops-utils` can't redirect your token to another server.

`devops-utils setup env` writes a commented scaffold to copy
(`~/.devops-utils.env.example`, or `.env.devops-utils.example` with
`--project`); save the filled-in copy without the `.example` suffix.

### Windows

The env file is the simplest route: Claude Desktop and Claude Code start the
MCP server without your PowerShell session's `$env:` variables, and `setx`
only reaches processes started after it. For a one-off shell session:

```powershell
$env:AZURE_DEVOPS_ORG_URL = 'https://dev.azure.com/your-org'
$env:AZURE_DEVOPS_TOKEN   = '<bearer-token-or-pat>'
```

`uvx` ships as a real `.exe` with uv (`winget install astral-sh.uv`), so the MCP
entry `setup mcp` writes needs no `cmd /c` wrapper; `setup mcp` warns when the
launcher isn't on `PATH`.

A fifth variable, `DEVOPS_UTILS_SKIP_CONFIRMATION`, turns off the
human-in-the-loop prompt that guards every write — see
{doc}`azure-devops` for what that gate does before you set it.

## Checking it works

```bash
devops-utils --version
devops-utils azdo repos --project MyProject --name api   # first read-only call
```

A misconfigured token surfaces as an HTTP 401/203 from the first command; a
wrong `AZURE_DEVOPS_API_VERSION` on an old on-prem server surfaces as a
404 on an otherwise valid route.
