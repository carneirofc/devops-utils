"""Thin, framework-agnostic agent-tool wrappers over the core logic.

These are plain callables with clear signatures and docstrings so they can be
registered with any agent framework (or the MCP server) without importing it.

The Azure DevOps wrappers build their client from environment variables
(``AZURE_DEVOPS_ORG_URL`` + ``AZURE_DEVOPS_TOKEN``) so a token never flows
through tool arguments or logs. See :mod:`devops_utils.core.azure_devops.client`.
"""

from typing import Any

import yaml

from devops_utils.core.sanitizer import sanitize as _sanitize


def sanitize_manifest(manifest: str) -> str:
    """Mask Secret values in a Kubernetes YAML manifest.

    Args:
        manifest: One or more Kubernetes YAML documents as a string.

    Returns:
        The manifest with every Secret's ``data``/``stringData`` values masked.
    """
    sanitized = _sanitize(manifest)
    return yaml.dump_all(sanitized, default_flow_style=False)


# --------------------------------------------------------------------------- #
# Azure DevOps work-item tools (cloud + on-prem)
# --------------------------------------------------------------------------- #
def _azdo_client() -> Any:
    from devops_utils.core.azure_devops import AzureDevOpsClient

    return AzureDevOpsClient.from_env()


def azdo_list_repositories(project: str | None = None) -> list[dict[str, Any]]:
    """List Git repositories, optionally scoped to a single project.

    Args:
        project: Optional team project name or id. Omit to list org-wide.

    Returns:
        A list of ``{id, name, project, default_branch, web_url}`` dicts.
    """
    from devops_utils.core.azure_devops import list_repositories

    return list_repositories(_azdo_client(), project)


def azdo_list_work_items(
    project: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    assigned_to: str | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List work items in a project, filtered by state/type/assignee.

    Args:
        project: Team project name or id.
        states: Optional states to include (e.g. ``["Active", "New"]``).
        types: Optional work-item types (e.g. ``["Bug", "Task"]``).
        assigned_to: Optional assignee (email or display name).
        top: Maximum number of items to return.

    Returns:
        A list of trimmed work-item dicts.
    """
    from devops_utils.core.azure_devops import list_work_items

    return list_work_items(
        _azdo_client(),
        project,
        states=states,
        types=types,
        assigned_to=assigned_to,
        top=top,
    )


def azdo_search_work_items(
    project: str,
    text: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """Text-search work items by title/description within a project.

    Args:
        project: Team project name or id.
        text: Text to match against title and description.
        states: Optional states to include.
        types: Optional work-item types.
        top: Maximum number of items to return.

    Returns:
        A list of trimmed work-item dicts.
    """
    from devops_utils.core.azure_devops import search_work_items

    return search_work_items(
        _azdo_client(), project, text, states=states, types=types, top=top
    )


def azdo_get_work_item(work_item_id: int, relations: bool = False) -> dict[str, Any]:
    """Fetch a single work item by id.

    Args:
        work_item_id: The work-item id.
        relations: When true, include the item's relations (parent/child links,
            related work items, hyperlinks, attachments, commit/PR/branch links)
            as a ``relations`` list of ``{kind, target, ...}`` dicts.

    Returns:
        A trimmed work-item dict.
    """
    from devops_utils.core.azure_devops import get_work_item

    return get_work_item(_azdo_client(), work_item_id, relations=relations)


def azdo_create_work_item(
    project: str,
    work_item_type: str,
    title: str,
    description: str | None = None,
    tags: list[str] | None = None,
    area_path: str | None = None,
    iteration_path: str | None = None,
    assigned_to: str | None = None,
    parent: int | None = None,
) -> dict[str, Any]:
    """Create a work item.

    Args:
        project: Team project name or id.
        work_item_type: e.g. ``Bug``, ``Task``, ``User Story``.
        title: Work-item title.
        description: Optional HTML description.
        tags: Optional list of tags.
        area_path / iteration_path: Optional classification nodes.
        assigned_to: Optional assignee (email or display name).
        parent: Optional parent work-item id; creates the item directly under
            it in the hierarchy (e.g. a Task under a User Story).

    Returns:
        The created work item (trimmed).
    """
    from devops_utils.core.azure_devops import create_work_item

    return create_work_item(
        _azdo_client(),
        project,
        work_item_type,
        title,
        description=description,
        tags=tags,
        area_path=area_path,
        iteration_path=iteration_path,
        assigned_to=assigned_to,
        parent=parent,
    )


def azdo_comment_work_item(work_item_id: int, text: str) -> dict[str, Any]:
    """Add a comment to a work item.

    Args:
        work_item_id: The work-item id.
        text: Comment body.

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import add_comment

    return add_comment(_azdo_client(), work_item_id, text)


def azdo_set_work_item_tags(
    work_item_id: int, tags: list[str], mode: str = "add"
) -> dict[str, Any]:
    """Set tags on a work item.

    Args:
        work_item_id: The work-item id.
        tags: Tags to apply.
        mode: ``"add"`` merges with existing tags; ``"replace"`` overwrites.

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import set_tags

    return set_tags(_azdo_client(), work_item_id, tags, mode)


def azdo_update_work_item(
    work_item_id: int,
    state: str | None = None,
    assigned_to: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Update mutable fields of an existing work item.

    Args:
        work_item_id: The work-item id.
        state: New state (process-template-specific, e.g. ``Closed``, ``Done``,
            ``Resolved``, ``Active``).
        assigned_to: New assignee (email or display name).
        title: New title.
        description: New description (HTML).

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import update_work_item

    return update_work_item(
        _azdo_client(),
        work_item_id,
        state=state,
        assigned_to=assigned_to,
        title=title,
        description=description,
    )


def azdo_add_work_item_link(
    work_item_id: int,
    kind: str,
    value: str,
    project: str | None = None,
    repo: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """Add a reference to a work item (repo commit, PR, branch, work item, or URL).

    Args:
        work_item_id: The work-item id to attach the reference to.
        kind: One of ``commit``, ``pull_request``, ``branch`` (need ``project`` +
            ``repo``), ``work_item``/``parent``/``child``/``predecessor``/
            ``successor`` (``value`` = target work-item id), ``hyperlink``
            (``value`` = raw URL).
        value: Commit SHA / PR id / branch name / work-item id / URL per ``kind``.
        project: Team project (required for commit/pull_request/branch).
        repo: Repository name or id (required for commit/pull_request/branch).
        comment: Optional note stored on the relation.

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import add_link

    return add_link(
        _azdo_client(),
        work_item_id,
        kind,
        value,
        project=project,
        repo=repo,
        comment=comment,
    )


def azdo_remove_work_item_link(
    work_item_id: int,
    kind: str,
    value: str,
    project: str | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    """Remove a reference from a work item (e.g. detach its parent before re-parenting).

    Args:
        work_item_id: The work-item id to remove the reference from.
        kind: Same kinds as ``azdo_add_work_item_link``: ``commit``,
            ``pull_request``, ``branch`` (need ``project`` + ``repo``),
            ``work_item``/``parent``/``child``/``predecessor``/``successor``
            (``value`` = target work-item id), ``hyperlink`` (``value`` = URL).
        value: Commit SHA / PR id / branch name / work-item id / URL per ``kind``.
        project: Team project (required for commit/pull_request/branch).
        repo: Repository name or id (required for commit/pull_request/branch).

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import remove_link

    return remove_link(
        _azdo_client(), work_item_id, kind, value, project=project, repo=repo
    )


def azdo_add_work_item_attachment(
    work_item_id: int, file_path: str, comment: str | None = None
) -> dict[str, Any]:
    """Upload a local file and attach it to a work item.

    Args:
        work_item_id: The work-item id.
        file_path: Path to a local file to upload.
        comment: Optional note stored on the attachment relation.

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import add_attachment

    return add_attachment(_azdo_client(), work_item_id, file_path, comment=comment)
