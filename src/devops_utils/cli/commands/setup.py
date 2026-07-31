"""``devops-utils setup`` — install skills and wire the MCP server into an agent.

Copies the bundled agent skills into an agent's skills directory, optionally
registers the MCP server (``setup mcp`` / ``setup all --with-mcp``; the entry
launches ``uvx --from "devops-utils[mcp]" devops-utils-mcp`` unless ``--no-uvx``),
and writes an Azure DevOps env-var scaffold. Defaults target Claude Code at user
scope (``~/.claude``); ``--project`` targets the current repo and ``--dest`` an
arbitrary directory.

``setup tracker`` is the per-repo companion: it writes an Azure DevOps
``docs/agents/issue-tracker.md`` + ``triage-labels.md`` so mattpocock-style
skills drive work items through ``devops-utils azdo`` instead of ``gh``.
"""

from pathlib import Path

import click

from devops_utils.agent import install


def _scope_options(fn):
    """Attach the shared ``--user/--project`` and ``--force`` options."""
    fn = click.option(
        "--project",
        "project",
        is_flag=True,
        help="Target the current repo instead of the user home config.",
    )(fn)
    fn = click.option(
        "--force",
        is_flag=True,
        help="Overwrite existing files instead of skipping them.",
    )(fn)
    return fn


def _report(written: list[Path], skipped: list[Path]) -> None:
    for path in written:
        click.echo(f"wrote  {path}")
    for path in skipped:
        click.echo(f"skip   {path} (exists; use --force)")


def _skills_target(
    project: bool, dest: str | None, claude_layout: bool
) -> tuple[Path, str]:
    """Resolve the skills base dir and layout for the chosen scope."""
    if dest is not None:
        return Path(dest), ("claude" if claude_layout else "flat")
    base = Path.cwd() / ".claude" if project else Path.home() / ".claude"
    return base, "claude"


@click.group("setup")
def setup() -> None:
    """Install skills and configure an agent (skills, MCP server, env)."""


@setup.command("skills")
@_scope_options
@click.option("--dest", default=None, help="Install into this directory (flat layout).")
@click.option(
    "--claude-layout",
    is_flag=True,
    help="With --dest, use the Claude <name>/SKILL.md layout instead of flat.",
)
def skills_cmd(
    project: bool, force: bool, dest: str | None, claude_layout: bool
) -> None:
    """Copy the bundled agent skills into an agent's skills directory."""
    base, layout = _skills_target(project, dest, claude_layout)
    written, skipped = install.install_skills(base, layout=layout, force=force)
    _report(written, skipped)


@setup.command("agents")
@_scope_options
@click.option("--dest", default=None, help="Install into this directory's agents/.")
def agents_cmd(project: bool, force: bool, dest: str | None) -> None:
    """Copy the bundled Claude Code subagents into an agents directory.

    Installs the read-only Azure DevOps analyst agents (work items, builds,
    repos) as <base>/agents/<name>.md — user scope ~/.claude by default,
    ./.claude with --project.
    """
    if dest is not None:
        base = Path(dest)
    else:
        base = Path.cwd() / ".claude" if project else Path.home() / ".claude"
    written, skipped = install.install_agents(base, force=force)
    _report(written, skipped)


@setup.command("mcp")
@_scope_options
@click.option("--dest", default=None, help="Write .mcp.json into this directory.")
@click.option(
    "--no-uvx",
    is_flag=True,
    help="Register the on-PATH devops-utils-mcp console script instead of the "
    "zero-install uvx launcher (requires pip install 'devops-utils[mcp]').",
)
def mcp_cmd(project: bool, force: bool, dest: str | None, no_uvx: bool) -> None:
    """Register the devops-utils MCP server in the agent's MCP config.

    By default the entry launches the server through
    ``uvx --from "devops-utils[mcp]" devops-utils-mcp`` — zero-install, only
    ``uv`` needs to be present. ``--no-uvx`` writes the bare
    ``devops-utils-mcp`` command for installed-package setups.
    """
    if dest is not None:
        path = Path(dest) / ".mcp.json"
    elif project:
        path = Path.cwd() / ".mcp.json"
    else:
        path = Path.home() / ".claude.json"
    path, changed = install.merge_mcp_config(path, force=force, use_uvx=not no_uvx)
    if changed:
        click.echo(f"wrote  {path} (mcpServers.{install.MCP_SERVER_NAME})")
    else:
        click.echo(
            f"skip   {path} ({install.MCP_SERVER_NAME} already set; use --force)"
        )


@setup.command("env")
@_scope_options
@click.option(
    "--dest", default=None, help="Write the env scaffold into this directory."
)
def env_cmd(project: bool, force: bool, dest: str | None) -> None:
    """Write an Azure DevOps env-var scaffold."""
    if dest is not None:
        path = Path(dest) / ".env.devops-utils.example"
    elif project:
        path = Path.cwd() / ".env.devops-utils.example"
    else:
        path = Path.home() / ".devops-utils.env.example"
    result = install.write_env_scaffold(path, force=force)
    if result is not None:
        click.echo(f"wrote  {result}")
    else:
        click.echo(f"skip   {path} (exists; use --force)")


@setup.command("plugin")
@click.option(
    "--dest",
    default=None,
    help="Repository root to generate the plugin tree into (defaults to cwd).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files instead of skipping them.",
)
def plugin_cmd(dest: str | None, force: bool) -> None:
    """Generate the Claude Code plugin + marketplace tree for this repo.

    Lays the bundled skills/agents out as a plugin named ``devops-utils`` so
    Claude Code lists them namespaced (``devops-utils:azure-devops-research``,
    ``devops-utils:azdo-workitem-analyst``, …). Writes
    ``plugins/devops-utils/`` (skills, agents, plugin.json) plus
    ``.claude-plugin/marketplace.json`` at the repo root. Install with
    ``/plugin marketplace add carneirofc/devops-utils`` then
    ``/plugin install devops-utils@carneirofc``.

    The agents' MCP tools still come from ``setup mcp`` + the ``devops-utils-mcp``
    server (``pip install "devops-utils[mcp]"``); MCP is not bundled in the plugin.
    """
    base = Path(dest) if dest is not None else Path.cwd()
    written, skipped = install.install_plugin(base, force=force)
    _report(written, skipped)


@setup.command("tracker")
@click.option(
    "--project-name",
    required=True,
    prompt="Azure DevOps project name",
    help="Azure DevOps team project the tracker config points at.",
)
@click.option(
    "--done-state",
    default="Closed",
    show_default=True,
    help="State meaning 'closed' in the project's process template.",
)
@click.option(
    "--dest",
    default=None,
    help="Repository root to install into (defaults to the current directory).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files instead of skipping them.",
)
def tracker_cmd(
    project_name: str, done_state: str, dest: str | None, force: bool
) -> None:
    """Point mattpocock-style skills at Azure DevOps for this repo.

    Writes docs/agents/issue-tracker.md and docs/agents/triage-labels.md so
    skills that read the repo's tracker config use `devops-utils azdo` (Azure
    DevOps work items) instead of the default GitHub `gh` CLI.
    """
    base = Path(dest) if dest is not None else Path.cwd()
    written, skipped = install.install_tracker(
        base, project_name, done_state=done_state, force=force
    )
    _report(written, skipped)


@setup.command("all")
@_scope_options
@click.option("--dest", default=None, help="Install everything into this directory.")
@click.option(
    "--claude-layout",
    is_flag=True,
    help="With --dest, use the Claude <name>/SKILL.md skills layout.",
)
@click.option(
    "--with-mcp",
    is_flag=True,
    help="Also register the MCP server (uvx launcher; see 'setup mcp').",
)
@click.pass_context
def all_cmd(
    ctx: click.Context,
    project: bool,
    force: bool,
    dest: str | None,
    claude_layout: bool,
    with_mcp: bool,
) -> None:
    """Install skills, agents, and the env scaffold; MCP only with --with-mcp.

    MCP registration is opt-in: the skills already document running everything
    through ``uvx``, so most setups need no server entry at all. Pass
    ``--with-mcp`` (or run ``setup mcp``) to register the uvx-launched server.
    """
    ctx.invoke(
        skills_cmd, project=project, force=force, dest=dest, claude_layout=claude_layout
    )
    ctx.invoke(agents_cmd, project=project, force=force, dest=dest)
    if with_mcp:
        ctx.invoke(mcp_cmd, project=project, force=force, dest=dest, no_uvx=False)
    else:
        click.echo("skip   MCP server registration (opt in with --with-mcp)")
    ctx.invoke(env_cmd, project=project, force=force, dest=dest)
