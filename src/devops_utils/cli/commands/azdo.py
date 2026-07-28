"""``devops-utils azdo`` — interact with Azure DevOps work items (cloud + on-prem).

Config comes from the environment (no machine credentials are read):
``AZURE_DEVOPS_ORG_URL``, ``AZURE_DEVOPS_TOKEN``, and optional
``AZURE_DEVOPS_AUTH_SCHEME`` (``bearer``/``pat``) and ``AZURE_DEVOPS_API_VERSION``.
"""

import json
from typing import Any

import click

from devops_utils.agent import tools
from devops_utils.core.azure_devops.workitems import LINK_KINDS
from devops_utils.core.confirmation import skip_confirmation

_YES_OPTION = click.option(
    "--yes", "-y", is_flag=True, help="Skip confirmation prompt."
)
_DRY_RUN_OPTION = click.option(
    "--dry-run", is_flag=True, help="Preview the change without applying it."
)


def _echo(result: Any) -> None:
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


def _confirm_or_dry_run(preview: dict[str, Any], *, yes: bool, dry_run: bool) -> bool:
    """Show the pending write; return True if the caller should proceed."""
    click.echo(f"About to write: {json.dumps(preview, ensure_ascii=False)}")
    if dry_run:
        click.echo("(dry run — not applied)")
        return False
    if yes or skip_confirmation():
        return True
    return click.confirm("Apply this change?", default=False)


@click.group("azdo")
def azdo() -> None:
    """Interact with Azure DevOps work items and repositories."""


def _resolve_assignee(assigned_to: str | None, mine: bool) -> str | None:
    """Combine --assigned-to and --mine (the WIQL @Me macro shortcut)."""
    if mine and assigned_to:
        raise click.UsageError("--mine and --assigned-to are mutually exclusive")
    return "@Me" if mine else assigned_to


_FIELD_OPTION = click.option(
    "--field",
    "field_pairs",
    multiple=True,
    metavar="NAME=VALUE",
    help="Set a custom/extra field by reference name (repeatable), "
    "e.g. --field Custom.RiskLevel=High.",
)


def _parse_fields(pairs: tuple[str, ...]) -> dict[str, str] | None:
    """Turn repeated ``NAME=VALUE`` strings into a fields dict."""
    if not pairs:
        return None
    fields: dict[str, str] = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep:
            raise click.UsageError(f"--field must be NAME=VALUE, got {pair!r}")
        fields[name] = value
    return fields


@azdo.command("repos")
@click.option("--project", default=None, help="Scope to a single team project.")
@click.option("--name", default=None, help="Filter repos by name substring.")
def repos(project: str | None, name: str | None) -> None:
    """List Git repositories."""
    _echo(tools.azdo_list_repositories(project, name_filter=name))


@azdo.command("list")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--state", "states", multiple=True, help="Filter by state (repeatable).")
@click.option(
    "--type", "types", multiple=True, help="Filter by work-item type (repeatable)."
)
@click.option("--assigned-to", default=None, help="Filter by assignee.")
@click.option(
    "--mine", is_flag=True, help="Only items assigned to me (WIQL @Me macro)."
)
@click.option(
    "--tag", "tags", multiple=True, help="Require a tag (repeatable, AND semantics)."
)
@click.option(
    "--area-path", default=None, help="Filter by area path (includes sub-areas)."
)
@click.option(
    "--iteration-path",
    default=None,
    help="Filter by iteration/sprint path (includes sub-iterations).",
)
@click.option("--top", default=50, show_default=True, help="Max items to return.")
def list_(
    project: str,
    states: tuple[str, ...],
    types: tuple[str, ...],
    assigned_to: str | None,
    mine: bool,
    tags: tuple[str, ...],
    area_path: str | None,
    iteration_path: str | None,
    top: int,
) -> None:
    """List work items in a project."""
    _echo(
        tools.azdo_list_work_items(
            project,
            states=list(states) or None,
            types=list(types) or None,
            assigned_to=_resolve_assignee(assigned_to, mine),
            tags=list(tags) or None,
            area_path=area_path,
            iteration_path=iteration_path,
            top=top,
        )
    )


@azdo.command("search")
@click.option("--project", required=True, help="Team project name or id.")
@click.argument("text")
@click.option("--state", "states", multiple=True, help="Filter by state (repeatable).")
@click.option(
    "--type", "types", multiple=True, help="Filter by work-item type (repeatable)."
)
@click.option("--assigned-to", default=None, help="Filter by assignee.")
@click.option(
    "--mine", is_flag=True, help="Only items assigned to me (WIQL @Me macro)."
)
@click.option(
    "--tag", "tags", multiple=True, help="Require a tag (repeatable, AND semantics)."
)
@click.option(
    "--area-path", default=None, help="Filter by area path (includes sub-areas)."
)
@click.option(
    "--iteration-path",
    default=None,
    help="Filter by iteration/sprint path (includes sub-iterations).",
)
@click.option("--top", default=50, show_default=True, help="Max items to return.")
def search(
    project: str,
    text: str,
    states: tuple[str, ...],
    types: tuple[str, ...],
    assigned_to: str | None,
    mine: bool,
    tags: tuple[str, ...],
    area_path: str | None,
    iteration_path: str | None,
    top: int,
) -> None:
    """Text-search work items by title/description."""
    _echo(
        tools.azdo_search_work_items(
            project,
            text,
            states=list(states) or None,
            types=list(types) or None,
            assigned_to=_resolve_assignee(assigned_to, mine),
            tags=list(tags) or None,
            area_path=area_path,
            iteration_path=iteration_path,
            top=top,
        )
    )


@azdo.command("get")
@click.argument("work_item_id", type=int)
@click.option(
    "--relations",
    is_flag=True,
    help="Include relations (parent/child links, hyperlinks, attachments).",
)
def get(work_item_id: int, relations: bool) -> None:
    """Fetch a single work item by id."""
    _echo(tools.azdo_get_work_item(work_item_id, relations=relations))


@azdo.command("create")
@click.option("--project", required=True, help="Team project name or id.")
@click.option(
    "--type", "work_item_type", required=True, help="Work-item type, e.g. Bug/Task."
)
@click.option("--title", required=True, help="Work-item title.")
@click.option("--description", default=None, help="HTML description.")
@click.option("--tag", "tags", multiple=True, help="Tag (repeatable).")
@click.option("--area-path", default=None, help="Area path.")
@click.option("--iteration-path", default=None, help="Iteration path.")
@click.option("--assigned-to", default=None, help="Assignee (email or display name).")
@click.option(
    "--parent", type=int, default=None, help="Parent work-item id to create under."
)
@_FIELD_OPTION
@_YES_OPTION
@_DRY_RUN_OPTION
def create(
    project: str,
    work_item_type: str,
    title: str,
    description: str | None,
    tags: tuple[str, ...],
    area_path: str | None,
    iteration_path: str | None,
    assigned_to: str | None,
    parent: int | None,
    field_pairs: tuple[str, ...],
    yes: bool,
    dry_run: bool,
) -> None:
    """Create a work item."""
    fields = _parse_fields(field_pairs)
    if not _confirm_or_dry_run(
        {
            "action": "create",
            "project": project,
            "type": work_item_type,
            "title": title,
            "description": description,
            "tags": list(tags) or None,
            "area_path": area_path,
            "iteration_path": iteration_path,
            "assigned_to": assigned_to,
            "parent": parent,
            "fields": fields,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(
        tools.azdo_create_work_item(
            project,
            work_item_type,
            title,
            description=description,
            tags=list(tags) or None,
            area_path=area_path,
            iteration_path=iteration_path,
            assigned_to=assigned_to,
            parent=parent,
            fields=fields,
        )
    )


@azdo.command("comment")
@click.argument("work_item_id", type=int)
@click.argument("text")
@_YES_OPTION
@_DRY_RUN_OPTION
def comment(work_item_id: int, text: str, yes: bool, dry_run: bool) -> None:
    """Add a comment to a work item."""
    if not _confirm_or_dry_run(
        {"action": "comment", "work_item_id": work_item_id, "text": text},
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(tools.azdo_comment_work_item(work_item_id, text))


@azdo.command("tag")
@click.argument("work_item_id", type=int)
@click.argument("tags", nargs=-1, required=True)
@click.option(
    "--mode",
    type=click.Choice(["add", "replace"]),
    default="add",
    show_default=True,
    help="Merge with or replace existing tags.",
)
@_YES_OPTION
@_DRY_RUN_OPTION
def tag(
    work_item_id: int, tags: tuple[str, ...], mode: str, yes: bool, dry_run: bool
) -> None:
    """Set tags on a work item."""
    if not _confirm_or_dry_run(
        {
            "action": "tag",
            "work_item_id": work_item_id,
            "tags": list(tags),
            "mode": mode,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(tools.azdo_set_work_item_tags(work_item_id, list(tags), mode))


@azdo.command("update")
@click.argument("work_item_id", type=int)
@click.option("--state", default=None, help="New state, e.g. Active/Resolved/Closed.")
@click.option(
    "--assigned-to", default=None, help="New assignee (email or display name)."
)
@click.option("--title", default=None, help="New title.")
@click.option("--description", default=None, help="New HTML description.")
@click.option("--area-path", default=None, help="New area path.")
@click.option("--iteration-path", default=None, help="New iteration/sprint path.")
@_FIELD_OPTION
@_YES_OPTION
@_DRY_RUN_OPTION
def update(
    work_item_id: int,
    state: str | None,
    assigned_to: str | None,
    title: str | None,
    description: str | None,
    area_path: str | None,
    iteration_path: str | None,
    field_pairs: tuple[str, ...],
    yes: bool,
    dry_run: bool,
) -> None:
    """Update a work item's state, assignee, title, description, area, iteration, or custom fields."""
    fields = _parse_fields(field_pairs)
    if (
        state is None
        and assigned_to is None
        and title is None
        and description is None
        and area_path is None
        and iteration_path is None
        and fields is None
    ):
        raise click.UsageError(
            "give at least one of --state/--assigned-to/--title/--description/"
            "--area-path/--iteration-path/--field"
        )
    if not _confirm_or_dry_run(
        {
            "action": "update",
            "work_item_id": work_item_id,
            "state": state,
            "assigned_to": assigned_to,
            "title": title,
            "description": description,
            "area_path": area_path,
            "iteration_path": iteration_path,
            "fields": fields,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(
        tools.azdo_update_work_item(
            work_item_id,
            state=state,
            assigned_to=assigned_to,
            title=title,
            description=description,
            area_path=area_path,
            iteration_path=iteration_path,
            fields=fields,
        )
    )


@azdo.command("link")
@click.argument("work_item_id", type=int)
@click.option(
    "--kind",
    required=True,
    type=click.Choice(list(LINK_KINDS)),
    help="Reference kind.",
)
@click.option(
    "--value",
    required=True,
    help="SHA / PR id / branch / build id / work-item id / URL.",
)
@click.option(
    "--project", default=None, help="Required for commit/pull_request/branch."
)
@click.option("--repo", default=None, help="Required for commit/pull_request/branch.")
@click.option("--comment", default=None, help="Optional note on the relation.")
@_YES_OPTION
@_DRY_RUN_OPTION
def link(
    work_item_id: int,
    kind: str,
    value: str,
    project: str | None,
    repo: str | None,
    comment: str | None,
    yes: bool,
    dry_run: bool,
) -> None:
    """Add a reference (commit, PR, branch, build, work item, or hyperlink)."""
    if not _confirm_or_dry_run(
        {
            "action": "link",
            "work_item_id": work_item_id,
            "kind": kind,
            "value": value,
            "project": project,
            "repo": repo,
            "comment": comment,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(
        tools.azdo_add_work_item_link(
            work_item_id, kind, value, project=project, repo=repo, comment=comment
        )
    )


@azdo.command("unlink")
@click.argument("work_item_id", type=int)
@click.option(
    "--kind",
    required=True,
    type=click.Choice(list(LINK_KINDS)),
    help="Reference kind.",
)
@click.option(
    "--value",
    required=True,
    help="SHA / PR id / branch / build id / work-item id / URL.",
)
@click.option(
    "--project", default=None, help="Required for commit/pull_request/branch."
)
@click.option("--repo", default=None, help="Required for commit/pull_request/branch.")
@_YES_OPTION
@_DRY_RUN_OPTION
def unlink(
    work_item_id: int,
    kind: str,
    value: str,
    project: str | None,
    repo: str | None,
    yes: bool,
    dry_run: bool,
) -> None:
    """Remove a reference (commit, PR, branch, build, work item, or hyperlink)."""
    if not _confirm_or_dry_run(
        {
            "action": "unlink",
            "work_item_id": work_item_id,
            "kind": kind,
            "value": value,
            "project": project,
            "repo": repo,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(
        tools.azdo_remove_work_item_link(
            work_item_id, kind, value, project=project, repo=repo
        )
    )


@azdo.command("builds")
@click.option("--project", required=True, help="Team project name or id.")
@click.option(
    "--definition",
    "definitions",
    multiple=True,
    type=int,
    help="Filter by pipeline definition id (repeatable).",
)
@click.option("--branch", default=None, help="Filter by source branch (e.g. main).")
@click.option(
    "--status",
    "statuses",
    multiple=True,
    help="Filter by status, e.g. inProgress/completed (repeatable).",
)
@click.option(
    "--result",
    "results",
    multiple=True,
    help="Filter by result, e.g. succeeded/failed (repeatable).",
)
@click.option("--top", default=25, show_default=True, help="Max builds to return.")
def builds(
    project: str,
    definitions: tuple[int, ...],
    branch: str | None,
    statuses: tuple[str, ...],
    results: tuple[str, ...],
    top: int,
) -> None:
    """List builds (pipeline runs) in a project."""
    _echo(
        tools.azdo_list_builds(
            project,
            definitions=list(definitions) or None,
            branch=branch,
            statuses=list(statuses) or None,
            results=list(results) or None,
            top=top,
        )
    )


@azdo.command("build")
@click.argument("build_id", type=int)
@click.option("--project", required=True, help="Team project name or id.")
def build(build_id: int, project: str) -> None:
    """Fetch a single build by id."""
    _echo(tools.azdo_get_build(project, build_id))


@azdo.command("definitions")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--name", default=None, help="Definition name filter; supports *.")
@click.option("--top", default=25, show_default=True, help="Max definitions.")
def definitions(project: str, name: str | None, top: int) -> None:
    """List build (pipeline) definitions."""
    _echo(tools.azdo_list_build_definitions(project, name=name, top=top))


@azdo.command("timeline")
@click.argument("build_id", type=int)
@click.option("--project", required=True, help="Team project name or id.")
def timeline(build_id: int, project: str) -> None:
    """Show a build's timeline (stages/jobs/tasks, results, issues, log ids)."""
    _echo(tools.azdo_get_build_timeline(project, build_id))


@azdo.command("logs")
@click.argument("build_id", type=int)
@click.option("--project", required=True, help="Team project name or id.")
def logs(build_id: int, project: str) -> None:
    """List a build's logs (id + line count)."""
    _echo(tools.azdo_list_build_logs(project, build_id))


@azdo.command("log")
@click.argument("build_id", type=int)
@click.argument("log_id", type=int)
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--start-line", type=int, default=None, help="First line to fetch.")
@click.option("--end-line", type=int, default=None, help="Last line to fetch.")
def log(
    build_id: int,
    log_id: int,
    project: str,
    start_line: int | None,
    end_line: int | None,
) -> None:
    """Print a build log's content (optionally a line range)."""
    click.echo(
        tools.azdo_get_build_log(
            project, build_id, log_id, start_line=start_line, end_line=end_line
        )
    )


@azdo.command("files")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--repo", required=True, help="Repository name or id.")
@click.option(
    "--pattern",
    default="*",
    show_default=True,
    help="Path glob, e.g. '*.yml' or 'src/*/pipeline*'.",
)
@click.option("--branch", default=None, help="Branch (defaults to repo default).")
@click.option("--top", default=100, show_default=True, help="Max matches.")
def files(project: str, repo: str, pattern: str, branch: str | None, top: int) -> None:
    """Find files in a repository by path glob (no Search extension needed)."""
    _echo(
        tools.azdo_find_repo_files(
            project, repo, path_pattern=pattern, branch=branch, top=top
        )
    )


@azdo.command("code-search")
@click.argument("text")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--repo", default=None, help="Scope to a repository.")
@click.option("--branch", default=None, help="Scope to a branch.")
@click.option("--top", default=25, show_default=True, help="Max results.")
def code_search_cmd(
    text: str, project: str, repo: str | None, branch: str | None, top: int
) -> None:
    """Search code content (Search extension; cloud always, on-prem if installed)."""
    _echo(tools.azdo_code_search(project, text, repo=repo, branch=branch, top=top))


@azdo.command("build-tag")
@click.argument("build_id", type=int)
@click.argument("tags", nargs=-1, required=True)
@click.option("--project", required=True, help="Team project name or id.")
@_YES_OPTION
@_DRY_RUN_OPTION
def build_tag(
    build_id: int, tags: tuple[str, ...], project: str, yes: bool, dry_run: bool
) -> None:
    """Add tags to a build."""
    if not _confirm_or_dry_run(
        {
            "action": "build-tag",
            "project": project,
            "build_id": build_id,
            "tags": list(tags),
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(tools.azdo_tag_build(project, build_id, list(tags)))


@azdo.command("pr-comment")
@click.argument("pull_request_id", type=int)
@click.argument("text")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--repo", required=True, help="Repository name or id.")
@click.option(
    "--thread",
    "thread_id",
    type=int,
    default=None,
    help="Existing thread id to reply to; omit to start a new thread.",
)
@_YES_OPTION
@_DRY_RUN_OPTION
def pr_comment(
    pull_request_id: int,
    text: str,
    project: str,
    repo: str,
    thread_id: int | None,
    yes: bool,
    dry_run: bool,
) -> None:
    """Comment on a pull request (new thread or reply)."""
    if not _confirm_or_dry_run(
        {
            "action": "pr-comment",
            "project": project,
            "repo": repo,
            "pull_request_id": pull_request_id,
            "text": text,
            "thread_id": thread_id,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(
        tools.azdo_comment_pull_request(
            project, repo, pull_request_id, text, thread_id=thread_id
        )
    )


@azdo.command("attach")
@click.argument("work_item_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--comment", default=None, help="Optional note on the attachment.")
@_YES_OPTION
@_DRY_RUN_OPTION
def attach(
    work_item_id: int, file_path: str, comment: str | None, yes: bool, dry_run: bool
) -> None:
    """Upload a local file and attach it to a work item."""
    if not _confirm_or_dry_run(
        {
            "action": "attach",
            "work_item_id": work_item_id,
            "file_path": file_path,
            "comment": comment,
        },
        yes=yes,
        dry_run=dry_run,
    ):
        return
    _echo(tools.azdo_add_work_item_attachment(work_item_id, file_path, comment=comment))
