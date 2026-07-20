"""``devops-utils azdo`` — interact with Azure DevOps work items (cloud + on-prem).

Config comes from the environment (no machine credentials are read):
``AZURE_DEVOPS_ORG_URL``, ``AZURE_DEVOPS_TOKEN``, and optional
``AZURE_DEVOPS_AUTH_SCHEME`` (``bearer``/``pat``) and ``AZURE_DEVOPS_API_VERSION``.
"""

import json
from typing import Any

import click

from devops_utils.agent import tools


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
@click.option("--type", "types", multiple=True, help="Filter by work-item type (repeatable).")
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
@click.option("--type", "types", multiple=True, help="Filter by work-item type (repeatable).")
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
            project, text, states=list(states) or None, types=list(types) or None, top=top
        )
    )


@azdo.command("get")
@click.argument("work_item_id", type=int)
def get(work_item_id: int) -> None:
    """Fetch a single work item by id."""
    _echo(tools.azdo_get_work_item(work_item_id))


@azdo.command("create")
@click.option("--project", required=True, help="Team project name or id.")
@click.option("--type", "work_item_type", required=True, help="Work-item type, e.g. Bug/Task.")
@click.option("--title", required=True, help="Work-item title.")
@click.option("--description", default=None, help="HTML description.")
@click.option("--tag", "tags", multiple=True, help="Tag (repeatable).")
@click.option("--area-path", default=None, help="Area path.")
@click.option("--iteration-path", default=None, help="Iteration path.")
@click.option("--assigned-to", default=None, help="Assignee (email or display name).")
def create(
    project: str,
    work_item_type: str,
    title: str,
    description: str | None,
    tags: tuple[str, ...],
    area_path: str | None,
    iteration_path: str | None,
    assigned_to: str | None,
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


@azdo.command("link")
@click.argument("work_item_id", type=int)
@click.option(
    "--kind",
    required=True,
    type=click.Choice(["commit", "pull_request", "branch", "work_item", "hyperlink"]),
    help="Reference kind.",
)
@click.option("--value", required=True, help="SHA / PR id / branch / work-item id / URL.")
@click.option("--project", default=None, help="Required for commit/pull_request/branch.")
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


@azdo.command("attach")
@click.argument("work_item_id", type=int)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--comment", default=None, help="Optional note on the attachment.")
def attach(work_item_id: int, file_path: str, comment: str | None) -> None:
    """Upload a local file and attach it to a work item."""
    _echo(tools.azdo_add_work_item_attachment(work_item_id, file_path, comment=comment))
