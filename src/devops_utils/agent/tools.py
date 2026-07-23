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


def azdo_list_repositories(
    project: str | None = None, name_filter: str | None = None
) -> list[dict[str, Any]]:
    """List Git repositories, optionally scoped to a single project.

    Args:
        project: Optional team project name or id. Omit to list org-wide.
        name_filter: Optional case-insensitive substring to filter repo names.

    Returns:
        A list of ``{id, name, project, default_branch, web_url}`` dicts.
    """
    from devops_utils.core.azure_devops import list_repositories

    return list_repositories(_azdo_client(), project, name_filter=name_filter)


def azdo_list_work_items(
    project: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    assigned_to: str | None = None,
    tags: list[str] | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List work items in a project, filtered by state/type/assignee/tags.

    Args:
        project: Team project name or id.
        states: Optional states to include (e.g. ``["Active", "New"]``).
            "Pending" work is the non-closed states of the process template.
        types: Optional work-item types (e.g. ``["Bug", "Task"]``).
        assigned_to: Optional assignee (email or display name). Pass ``"@Me"``
            to use the WIQL macro that resolves the authenticated identity —
            i.e. "assigned to me" without knowing the user's email.
        tags: Optional tags; each must be present (AND semantics).
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
        tags=tags,
        top=top,
    )


def azdo_search_work_items(
    project: str,
    text: str,
    states: list[str] | None = None,
    types: list[str] | None = None,
    assigned_to: str | None = None,
    tags: list[str] | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """Text-search work items by title/description within a project.

    Args:
        project: Team project name or id.
        text: Text to match against title and description.
        states: Optional states to include.
        types: Optional work-item types.
        assigned_to: Optional assignee; ``"@Me"`` means the authenticated user.
        tags: Optional tags; each must be present (AND semantics).
        top: Maximum number of items to return.

    Returns:
        A list of trimmed work-item dicts.
    """
    from devops_utils.core.azure_devops import search_work_items

    return search_work_items(
        _azdo_client(),
        project,
        text,
        states=states,
        types=types,
        assigned_to=assigned_to,
        tags=tags,
        top=top,
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
    """Add a reference to a work item (commit, PR, branch, build, work item, or URL).

    Args:
        work_item_id: The work-item id to attach the reference to.
        kind: One of ``commit``, ``pull_request``, ``branch`` (need ``project`` +
            ``repo``), ``build`` (``value`` = build id, no project/repo needed),
            ``work_item``/``parent``/``child``/``predecessor``/
            ``successor`` (``value`` = target work-item id), ``hyperlink``
            (``value`` = raw URL).
        value: Commit SHA / PR id / branch name / build id / work-item id / URL
            per ``kind``.
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
            ``build`` (``value`` = build id),
            ``work_item``/``parent``/``child``/``predecessor``/``successor``
            (``value`` = target work-item id), ``hyperlink`` (``value`` = URL).
        value: Commit SHA / PR id / branch name / build id / work-item id / URL
            per ``kind``.
        project: Team project (required for commit/pull_request/branch).
        repo: Repository name or id (required for commit/pull_request/branch).

    Returns:
        The updated work item (trimmed).
    """
    from devops_utils.core.azure_devops import remove_link

    return remove_link(
        _azdo_client(), work_item_id, kind, value, project=project, repo=repo
    )


def azdo_list_builds(
    project: str,
    definitions: list[int] | None = None,
    branch: str | None = None,
    statuses: list[str] | None = None,
    results: list[str] | None = None,
    top: int = 25,
) -> list[dict[str, Any]]:
    """List builds (pipeline runs) in a project, newest first.

    Args:
        project: Team project name or id.
        definitions: Optional pipeline definition ids to filter on.
        branch: Optional source branch (short names like ``main`` are expanded
            to ``refs/heads/main``).
        statuses: Optional statuses (``inProgress``, ``completed``,
            ``notStarted``, ``cancelling``, ``postponed``).
        results: Optional results (``succeeded``, ``partiallySucceeded``,
            ``failed``, ``canceled``).
        top: Maximum number of builds to return.

    Returns:
        A list of ``{id, number, definition, status, result, branch,
        requested_for, queue_time, finish_time, web_url}`` dicts. Use the ``id``
        to link a build to a work item (``azdo_add_work_item_link`` kind
        ``build``) or to tag it.
    """
    from devops_utils.core.azure_devops import list_builds

    return list_builds(
        _azdo_client(),
        project,
        definitions=definitions,
        branch=branch,
        statuses=statuses,
        results=results,
        top=top,
    )


def azdo_get_build(project: str, build_id: int) -> dict[str, Any]:
    """Fetch a single build (pipeline run) by id.

    Args:
        project: Team project name or id.
        build_id: The build id.

    Returns:
        A trimmed build dict (see ``azdo_list_builds``).
    """
    from devops_utils.core.azure_devops import get_build

    return get_build(_azdo_client(), project, build_id)


def azdo_tag_build(project: str, build_id: int, tags: list[str]) -> list[str]:
    """Add tags to a build (builds have no comments; tags are the annotation).

    Args:
        project: Team project name or id.
        build_id: The build id.
        tags: Tags to add.

    Returns:
        The build's resulting tag list.
    """
    from devops_utils.core.azure_devops import add_build_tags

    return add_build_tags(_azdo_client(), project, build_id, tags)


def azdo_list_build_definitions(
    project: str, name: str | None = None, top: int = 25
) -> list[dict[str, Any]]:
    """List build (pipeline) definitions in a project.

    Args:
        project: Team project name or id.
        name: Optional name filter; supports ``*`` wildcards (e.g. ``CI*``).
        top: Maximum number of definitions to return.

    Returns:
        A list of ``{id, name, path, type, queue_status, web_url}`` dicts. Use
        the ``id`` with ``azdo_list_builds(definitions=[id])`` to list its runs.
    """
    from devops_utils.core.azure_devops import list_definitions

    return list_definitions(_azdo_client(), project, name=name, top=top)


def azdo_get_build_timeline(project: str, build_id: int) -> list[dict[str, Any]]:
    """Fetch a build's timeline: stages/jobs/tasks with state, result, and issues.

    The fastest way to diagnose a failed run: find the record with
    ``result == "failed"``, read its ``issues`` (error/warning messages), and
    fetch only its ``log_id`` via ``azdo_get_build_log``.

    Args:
        project: Team project name or id.
        build_id: The build id.

    Returns:
        Ordered records of ``{id, parent_id, type, name, state, result, log_id,
        start_time, finish_time, issues}``.
    """
    from devops_utils.core.azure_devops import get_build_timeline

    return get_build_timeline(_azdo_client(), project, build_id)


def azdo_list_build_logs(project: str, build_id: int) -> list[dict[str, Any]]:
    """List a build's logs as ``{id, line_count}`` entries.

    Use ``line_count`` to tail with ``azdo_get_build_log(start_line=
    line_count - N)`` instead of downloading a large log whole.

    Args:
        project: Team project name or id.
        build_id: The build id.
    """
    from devops_utils.core.azure_devops import list_build_logs

    return list_build_logs(_azdo_client(), project, build_id)


def azdo_get_build_log(
    project: str,
    build_id: int,
    log_id: int,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Fetch a build log's content as plain text.

    Prefer a line range over the whole log: get ``line_count`` from
    ``azdo_list_build_logs`` and tail with ``start_line = line_count - 200``.

    Args:
        project: Team project name or id.
        build_id: The build id.
        log_id: The log id (from the timeline record or ``azdo_list_build_logs``).
        start_line / end_line: Optional line range to fetch.
    """
    from devops_utils.core.azure_devops import get_build_log

    return get_build_log(
        _azdo_client(),
        project,
        build_id,
        log_id,
        start_line=start_line,
        end_line=end_line,
    )


def azdo_find_repo_files(
    project: str,
    repo: str,
    path_pattern: str = "*",
    branch: str | None = None,
    top: int = 100,
) -> list[dict[str, Any]]:
    """Find files in a repository by path glob (works on cloud and on-prem).

    Args:
        project: Team project name or id.
        repo: Repository name or id.
        path_pattern: Glob matched against the repo-relative path or basename,
            e.g. ``*.yml``, ``src/*/pipeline*``.
        branch: Optional branch (defaults to the repo default branch).
        top: Maximum number of matches to return.

    Returns:
        A list of ``{path, size, commit, url}`` dicts.
    """
    from devops_utils.core.azure_devops import find_repo_items

    return find_repo_items(
        _azdo_client(),
        project,
        repo,
        path_pattern=path_pattern,
        branch=branch,
        top=top,
    )


def azdo_code_search(
    project: str,
    text: str,
    repo: str | None = None,
    branch: str | None = None,
    top: int = 25,
) -> list[dict[str, Any]]:
    """Search code content across a project's repositories.

    Uses the Search extension (always present on cloud; may be missing on-prem
    — the error says so, and ``azdo_find_repo_files`` is the fallback).

    Args:
        project: Team project name or id.
        text: Search text; code-search syntax works (e.g. ``def:Foo``,
            ``ext:yml pipeline``).
        repo: Optional repository name to scope to.
        branch: Optional branch to scope to.
        top: Maximum number of results.

    Returns:
        A list of ``{path, repo, project, matches}`` dicts.
    """
    from devops_utils.core.azure_devops import code_search

    return code_search(_azdo_client(), project, text, repo=repo, branch=branch, top=top)


def azdo_comment_pull_request(
    project: str,
    repo: str,
    pull_request_id: int,
    text: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Comment on a pull request (new thread, or reply to an existing one).

    Note: commits cannot be commented on via the REST API — comment on the PR
    containing the commit, or on the work item that links it.

    Args:
        project: Team project name or id.
        repo: Repository name or id.
        pull_request_id: The pull-request id.
        text: Comment body.
        thread_id: Optional existing thread id to reply to; omit to start a
            new (active) comment thread.

    Returns:
        A ``{thread_id, comment_id, status}`` dict.
    """
    from devops_utils.core.azure_devops import comment_on_pull_request

    return comment_on_pull_request(
        _azdo_client(), project, repo, pull_request_id, text, thread_id=thread_id
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
