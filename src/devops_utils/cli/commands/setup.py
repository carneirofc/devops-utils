"""``devops-utils setup`` — install skills and wire the MCP server into an agent.

Copies the bundled agent skills into an agent's skills directory, registers the
``devops-utils-mcp`` server in the agent's MCP config, and writes an Azure DevOps
env-var scaffold. Defaults target Claude Code at user scope (``~/.claude``);
``--project`` targets the current repo and ``--dest`` an arbitrary directory.

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
def mcp_cmd(project: bool, force: bool, dest: str | None) -> None:
    """Register the devops-utils MCP server in the agent's MCP config."""
    if dest is not None:
        path = Path(dest) / ".mcp.json"
    elif project:
        path = Path.cwd() / ".mcp.json"
    else:
        path = Path.home() / ".claude.json"
    path, changed = install.merge_mcp_config(path, force=force)
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
@click.pass_context
def all_cmd(
    ctx: click.Context,
    project: bool,
    force: bool,
    dest: str | None,
    claude_layout: bool,
) -> None:
    """Install skills, agents, wire the MCP server, and write the env scaffold."""
    ctx.invoke(
        skills_cmd, project=project, force=force, dest=dest, claude_layout=claude_layout
    )
    ctx.invoke(agents_cmd, project=project, force=force, dest=dest)
    ctx.invoke(mcp_cmd, project=project, force=force, dest=dest)
    ctx.invoke(env_cmd, project=project, force=force, dest=dest)
