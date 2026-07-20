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


def _echo(result: Any) -> None:
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@click.group("azdo")
def azdo() -> None:
    """Interact with Azure DevOps work items and repositories."""


@azdo.command("repos")
@click.option("--project", default=None, help="Scope to a single team project.")
def repos(project: str | None) -> None:
    """List Git repositories."""
    _echo(tools.azdo_list_repositories(project))


@azdo.command("list")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--state", "states", multiple=True, help="Filter by state (repeatable).")
@click.option(
    "--type", "types", multiple=True, help="Filter by work-item type (repeatable)."
)
@click.option("--assigned-to", default=None, help="Filter by assignee.")
@click.option("--top", default=50, show_default=True, help="Max items to return.")
def list_(
    project: str,
    states: tuple[str, ...],
    types: tuple[str, ...],
    assigned_to: str | None,
    top: int,
) -> None:
    """List work items in a project."""
    _echo(
        tools.azdo_list_work_items(
            project,
            states=list(states) or None,
            types=list(types) or None,
            assigned_to=assigned_to,
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
@click.option("--top", default=50, show_default=True, help="Max items to return.")
def search(
    project: str,
    text: str,
    states: tuple[str, ...],
    types: tuple[str, ...],
    top: int,
) -> None:
    """Text-search work items by title/description."""
    _echo(
        tools.azdo_search_work_items(
            project,
            text,
            states=list(states) or None,
            types=list(types) or None,
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
) -> None:
    """Create a work item."""
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
        )
    )


@azdo.command("comment")
@click.argument("work_item_id", type=int)
@click.argument("text")
def comment(work_item_id: int, text: str) -> None:
    """Add a comment to a work item."""
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
def tag(work_item_id: int, tags: tuple[str, ...], mode: str) -> None:
    """Set tags on a work item."""
    _echo(tools.azdo_set_work_item_tags(work_item_id, list(tags), mode))


@azdo.command("update")
@click.argument("work_item_id", type=int)
@click.option("--state", default=None, help="New state, e.g. Active/Resolved/Closed.")
@click.option(
    "--assigned-to", default=None, help="New assignee (email or display name)."
)
@click.option("--title", default=None, help="New title.")
@click.option("--description", default=None, help="New HTML description.")
def update(
    work_item_id: int,
    state: str | None,
    assigned_to: str | None,
    title: str | None,
    description: str | None,
) -> None:
    """Update a work item's state, assignee, title, or description."""
    if state is None and assigned_to is None and title is None and description is None:
        raise click.UsageError(
            "give at least one of --state/--assigned-to/--title/--description"
        )
    _echo(
        tools.azdo_update_work_item(
            work_item_id,
            state=state,
            assigned_to=assigned_to,
            title=title,
            description=description,
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
    "--value", required=True, help="SHA / PR id / branch / work-item id / URL."
)
@click.option(
    "--project", default=None, help="Required for commit/pull_request/branch."
)
@click.option("--repo", default=None, help="Required for commit/pull_request/branch.")
@click.option("--comment", default=None, help="Optional note on the relation.")
def link(
    work_item_id: int,
    kind: str,
    value: str,
    project: str | None,
    repo: str | None,
    comment: str | None,
) -> None:
    """Add a reference (commit, PR, branch, work item, or hyperlink)."""
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
    "--value", required=True, help="SHA / PR id / branch / work-item id / URL."
)
@click.option(
    "--project", default=None, help="Required for commit/pull_request/branch."
)
@click.option("--repo", default=None, help="Required for commit/pull_request/branch.")
def unlink(
    work_item_id: int,
    kind: str,
    value: str,
    project: str | None,
    repo: str | None,
) -> None:
    """Remove a reference (commit, PR, branch, work item, or hyperlink)."""
    _echo(
        tools.azdo_remove_work_item_link(
            work_item_id, kind, value, project=project, repo=repo
        )
    )


@azdo.command("attach")
@click.argument("work_item_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--comment", default=None, help="Optional note on the attachment.")
def attach(work_item_id: int, file_path: str, comment: str | None) -> None:
    """Upload a local file and attach it to a work item."""
    _echo(tools.azdo_add_work_item_attachment(work_item_id, file_path, comment=comment))
