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

Existing files are never clobbered silently: each one is offered for
overwrite individually (``y``/``n``/``a``ll/``q``uit/``d``iff), unless
``--force``/``--yes`` answers yes to everything or the run is unattended (no
tty, or ``DEVOPS_UTILS_SKIP_CONFIRMATION``), in which case they are kept.
"""

import difflib
from pathlib import Path

import click

from devops_utils.agent import install
from devops_utils.core.confirmation import skip_confirmation

#: ``ctx.meta`` key holding the run's shared :class:`_Overwriter`. ``ctx.meta``
#: spans the whole invocation, so an "all"/"quit" answer given during
#: ``setup all`` still applies to the sub-commands it invokes afterwards.
_OVERWRITER_KEY = "devops_utils.setup.overwriter"

_PROMPT_CHOICES = ("y", "n", "a", "q", "d")


class _Overwriter:
    """Ask, once per existing target, whether it may be overwritten.

    Implements :data:`install.ConfirmOverwrite`. All output goes to **stderr**
    (like the ``azdo`` write gate) so stdout stays the machine-readable list of
    what was written.

    State is deliberately per-run, not per-file: ``a`` (all) and ``q`` (quit)
    have to carry across the remaining files — and across the sub-commands
    ``setup all`` chains together.
    """

    def __init__(self, assume_yes: bool = False) -> None:
        self.assume_yes = assume_yes
        self.quit = False
        #: Set after the first EOF: an unattended run must not keep re-prompting
        #: a stream that will never answer.
        self.unattended = skip_confirmation()

    def __call__(self, request: install.OverwriteRequest) -> bool:
        if self.assume_yes:
            return True
        if self.quit:
            return False
        if request.new_text == request.existing_text:
            click.echo(f"same   {request.label}", err=True)
            return False
        if self.unattended:
            return False

        while True:
            answer: str
            try:
                answer = click.prompt(
                    f"overwrite {request.label}? "
                    "[y]es / [n]o / [a]ll / [q]uit / [d]iff",
                    type=click.Choice(_PROMPT_CHOICES, case_sensitive=False),
                    default="n",
                    show_default=False,
                    show_choices=False,
                    err=True,
                ).lower()
            except (EOFError, click.Abort):
                self.unattended = True
                click.echo(
                    "\n(not a terminal — keeping existing files; "
                    "use --force to overwrite)",
                    err=True,
                )
                return False
            if answer == "d":
                self._show_diff(request)
                continue
            if answer == "a":
                self.assume_yes = True
                return True
            if answer == "q":
                self.quit = True
                return False
            return answer == "y"

    @staticmethod
    def _show_diff(request: install.OverwriteRequest) -> None:
        """Print a unified diff of what the overwrite would change."""
        diff = difflib.unified_diff(
            request.existing_text.splitlines(),
            request.new_text.splitlines(),
            fromfile=f"{request.label} (existing)",
            tofile="bundled",
            lineterm="",
        )
        for line in diff:
            click.echo(line, err=True)


def _overwriter(ctx: click.Context, assume_yes: bool) -> _Overwriter:
    """Return the run's shared overwrite prompter, creating it on first use."""
    existing = ctx.meta.get(_OVERWRITER_KEY)
    if isinstance(existing, _Overwriter):
        if assume_yes:
            existing.assume_yes = True
        return existing
    created = _Overwriter(assume_yes=assume_yes)
    ctx.meta[_OVERWRITER_KEY] = created
    return created


def _force_option(fn):
    """Attach the shared ``--force``/``--yes`` overwrite options."""
    fn = click.option(
        "--yes",
        "-y",
        "yes",
        is_flag=True,
        help="Answer yes to every overwrite prompt (same as --force).",
    )(fn)
    fn = click.option(
        "--force",
        is_flag=True,
        help="Overwrite existing files without prompting.",
    )(fn)
    return fn


def _scope_options(fn):
    """Attach the shared ``--user/--project`` and overwrite options."""
    fn = click.option(
        "--project",
        "project",
        is_flag=True,
        help="Target the current repo instead of the user home config.",
    )(fn)
    fn = _force_option(fn)
    return fn


def _report(written: list[Path], skipped: list[Path]) -> None:
    for path in written:
        click.echo(f"wrote  {path}")
    for path in skipped:
        click.echo(f"skip   {path} (kept existing)")


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
@click.pass_context
def skills_cmd(
    ctx: click.Context,
    project: bool,
    force: bool,
    yes: bool,
    dest: str | None,
    claude_layout: bool,
) -> None:
    """Copy the bundled agent skills into an agent's skills directory."""
    base, layout = _skills_target(project, dest, claude_layout)
    written, skipped = install.install_skills(
        base, layout=layout, force=force, confirm=_overwriter(ctx, force or yes)
    )
    _report(written, skipped)


@setup.command("agents")
@_scope_options
@click.option("--dest", default=None, help="Install into this directory's agents/.")
@click.pass_context
def agents_cmd(
    ctx: click.Context, project: bool, force: bool, yes: bool, dest: str | None
) -> None:
    """Copy the bundled Claude Code subagents into an agents directory.

    Installs the read-only Azure DevOps analyst agents (work items, builds,
    repos) as <base>/agents/<name>.md — user scope ~/.claude by default,
    ./.claude with --project.
    """
    if dest is not None:
        base = Path(dest)
    else:
        base = Path.cwd() / ".claude" if project else Path.home() / ".claude"
    written, skipped = install.install_agents(
        base, force=force, confirm=_overwriter(ctx, force or yes)
    )
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
@click.pass_context
def mcp_cmd(
    ctx: click.Context,
    project: bool,
    force: bool,
    yes: bool,
    dest: str | None,
    no_uvx: bool,
) -> None:
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
    path, changed = install.merge_mcp_config(
        path,
        force=force,
        use_uvx=not no_uvx,
        confirm=_overwriter(ctx, force or yes),
    )
    if changed:
        click.echo(f"wrote  {path} (mcpServers.{install.MCP_SERVER_NAME})")
    else:
        click.echo(f"skip   {path} ({install.MCP_SERVER_NAME} left as-is)")


@setup.command("env")
@_scope_options
@click.option(
    "--dest", default=None, help="Write the env scaffold into this directory."
)
@click.pass_context
def env_cmd(
    ctx: click.Context, project: bool, force: bool, yes: bool, dest: str | None
) -> None:
    """Write an Azure DevOps env-var scaffold."""
    if dest is not None:
        path = Path(dest) / ".env.devops-utils.example"
    elif project:
        path = Path.cwd() / ".env.devops-utils.example"
    else:
        path = Path.home() / ".devops-utils.env.example"
    result = install.write_env_scaffold(
        path, force=force, confirm=_overwriter(ctx, force or yes)
    )
    if result is not None:
        click.echo(f"wrote  {result}")
    else:
        click.echo(f"skip   {path} (kept existing)")


@setup.command("plugin")
@click.option(
    "--dest",
    default=None,
    help="Repository root to generate the plugin tree into (defaults to cwd).",
)
@_force_option
@click.pass_context
def plugin_cmd(ctx: click.Context, dest: str | None, force: bool, yes: bool) -> None:
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
    written, skipped = install.install_plugin(
        base, force=force, confirm=_overwriter(ctx, force or yes)
    )
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
    "--org-url",
    default=None,
    help="Azure DevOps organization/collection URL recorded in the defaults "
    "table (AZURE_DEVOPS_ORG_URL stays authoritative at runtime).",
)
@click.option(
    "--parent-epic",
    default=None,
    type=int,
    help="Work-item id of the Epic new items are parented under by default.",
)
@click.option(
    "--area-path",
    default=None,
    help="Default area path for created items and scoped queries.",
)
@click.option(
    "--default-tag",
    "default_tags",
    multiple=True,
    help="Tag applied to every created item and used to scope queries (repeatable).",
)
@click.option(
    "--dest",
    default=None,
    help="Repository root to install into (defaults to the current directory).",
)
@_force_option
@click.pass_context
def tracker_cmd(
    ctx: click.Context,
    project_name: str,
    done_state: str,
    org_url: str | None,
    parent_epic: int | None,
    area_path: str | None,
    default_tags: tuple[str, ...],
    dest: str | None,
    force: bool,
    yes: bool,
) -> None:
    """Point mattpocock-style skills at Azure DevOps for this repo.

    Writes docs/agents/issue-tracker.md and docs/agents/triage-labels.md so
    skills that read the repo's tracker config use `devops-utils azdo` (Azure
    DevOps work items) instead of the default GitHub `gh` CLI. The optional
    org URL / parent Epic / area path / default tags land in the config's
    "Defaults for this repo" table, which agents apply on every create and
    query (see the setup-issue-tracker skill for a guided, validated flow).
    """
    base = Path(dest) if dest is not None else Path.cwd()
    written, skipped = install.install_tracker(
        base,
        project_name,
        done_state=done_state,
        org_url=org_url,
        parent_epic=parent_epic,
        area_path=area_path,
        default_tags=list(default_tags) or None,
        force=force,
        confirm=_overwriter(ctx, force or yes),
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
    yes: bool,
    dest: str | None,
    claude_layout: bool,
    with_mcp: bool,
) -> None:
    """Install skills, agents, and the env scaffold; MCP only with --with-mcp.

    MCP registration is opt-in: the skills already document running everything
    through ``uvx``, so most setups need no server entry at all. Pass
    ``--with-mcp`` (or run ``setup mcp``) to register the uvx-launched server.

    Overwrite answers are shared across the steps: one ``a``/``q`` covers the
    skills, agents, MCP entry, and env scaffold that follow it.
    """
    ctx.invoke(
        skills_cmd,
        project=project,
        force=force,
        yes=yes,
        dest=dest,
        claude_layout=claude_layout,
    )
    ctx.invoke(agents_cmd, project=project, force=force, yes=yes, dest=dest)
    if with_mcp:
        ctx.invoke(
            mcp_cmd, project=project, force=force, yes=yes, dest=dest, no_uvx=False
        )
    else:
        click.echo("skip   MCP server registration (opt in with --with-mcp)")
    ctx.invoke(env_cmd, project=project, force=force, yes=yes, dest=dest)
