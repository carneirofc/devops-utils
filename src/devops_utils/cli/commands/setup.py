"""``devops-utils setup`` — install skills and wire the MCP server into an agent.

Copies the bundled agent skills into an agent's skills directory, registers the
``devops-utils-mcp`` server in the agent's MCP config, and writes an Azure DevOps
env-var scaffold. Defaults target Claude Code at user scope (``~/.claude``);
``--project`` targets the current repo and ``--dest`` an arbitrary directory.
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
    """Install skills, wire the MCP server, and write the env scaffold."""
    ctx.invoke(
        skills_cmd, project=project, force=force, dest=dest, claude_layout=claude_layout
    )
    ctx.invoke(mcp_cmd, project=project, force=force, dest=dest)
    ctx.invoke(env_cmd, project=project, force=force, dest=dest)
