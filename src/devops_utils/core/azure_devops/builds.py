"""Build (pipeline run) queries against the Azure DevOps REST API.

Uses only documented, non-preview Build endpoints so it works on both
Services (cloud) and Server (on-prem).
"""

from __future__ import annotations

from typing import Any

from devops_utils.core.azure_devops.client import AzureDevOpsClient


def _trim_build(build: dict[str, Any]) -> dict[str, Any]:
    """Shrink a raw build to the fields agents care about."""
    definition = build.get("definition") or {}
    links = build.get("_links") or {}
    return {
        "id": build.get("id"),
        "number": build.get("buildNumber"),
        "definition": definition.get("name"),
        "status": build.get("status"),
        "result": build.get("result"),
        "branch": build.get("sourceBranch"),
        "requested_for": (build.get("requestedFor") or {}).get("displayName"),
        "queue_time": build.get("queueTime"),
        "finish_time": build.get("finishTime"),
        "web_url": (links.get("web") or {}).get("href"),
    }


def _branch_ref(branch: str) -> str:
    """Expand a short branch name to the full ref the Build API filters on."""
    return branch if branch.startswith("refs/") else f"refs/heads/{branch}"


def list_builds(
    client: AzureDevOpsClient,
    project: str,
    *,
    definitions: list[int] | None = None,
    branch: str | None = None,
    statuses: list[str] | None = None,
    results: list[str] | None = None,
    top: int = 25,
) -> list[dict[str, Any]]:
    """List builds in a project, newest first (API default order).

    Args:
        definitions: Optional pipeline definition ids to filter on.
        branch: Optional source branch (short names get ``refs/heads/`` prefixed).
        statuses: Optional status filter values (``inProgress``, ``completed``,
            ``notStarted``, ``cancelling``, ``postponed``).
        results: Optional result filter values (``succeeded``,
            ``partiallySucceeded``, ``failed``, ``canceled``).
        top: Maximum number of builds to return.
    """
    params: dict[str, Any] = {"$top": top}
    if definitions:
        params["definitions"] = ",".join(str(d) for d in definitions)
    if branch:
        params["branchName"] = _branch_ref(branch)
    if statuses:
        params["statusFilter"] = ",".join(statuses)
    if results:
        params["resultFilter"] = ",".join(results)

    data = client.request("GET", f"{project}/_apis/build/builds", params=params)
    builds = data.get("value", []) if isinstance(data, dict) else []
    return [_trim_build(build) for build in builds]


def get_build(client: AzureDevOpsClient, project: str, build_id: int) -> dict[str, Any]:
    """Fetch a single build by id (trimmed)."""
    data = client.request("GET", f"{project}/_apis/build/builds/{build_id}")
    return _trim_build(data if isinstance(data, dict) else {})


def list_definitions(
    client: AzureDevOpsClient,
    project: str,
    *,
    name: str | None = None,
    top: int = 25,
) -> list[dict[str, Any]]:
    """List build (pipeline) definitions in a project.

    Args:
        name: Optional definition name filter; ``*`` wildcards are supported by
            the API (e.g. ``CI*``).
        top: Maximum number of definitions to return.
    """
    params: dict[str, Any] = {"$top": top}
    if name:
        params["name"] = name
    data = client.request("GET", f"{project}/_apis/build/definitions", params=params)
    definitions = data.get("value", []) if isinstance(data, dict) else []
    return [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "path": d.get("path"),
            "type": d.get("type"),
            "queue_status": d.get("queueStatus"),
            "web_url": ((d.get("_links") or {}).get("web") or {}).get("href"),
        }
        for d in definitions
    ]


def _trim_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Shrink a timeline issue to its type (error/warning) and message."""
    return {"type": issue.get("type"), "message": issue.get("message")}


def get_build_timeline(
    client: AzureDevOpsClient, project: str, build_id: int
) -> list[dict[str, Any]]:
    """Fetch a build's timeline: its stages/phases/jobs/tasks with status.

    Each record carries a ``log_id`` (when the step produced a log) that can be
    passed to :func:`get_build_log`, and ``issues`` with the step's error and
    warning messages — the fastest way to locate why a run failed.

    Returns:
        Timeline records sorted by their ``order``, trimmed to ``{id, parent_id,
        type, name, state, result, log_id, start_time, finish_time, issues}``.
    """
    data = client.request(
        "GET", f"{project}/_apis/build/builds/{build_id}/timeline"
    )
    records = data.get("records", []) if isinstance(data, dict) else []
    trimmed = [
        {
            "id": rec.get("id"),
            "parent_id": rec.get("parentId"),
            "type": rec.get("type"),
            "name": rec.get("name"),
            "state": rec.get("state"),
            "result": rec.get("result"),
            "log_id": (rec.get("log") or {}).get("id"),
            "start_time": rec.get("startTime"),
            "finish_time": rec.get("finishTime"),
            "issues": [_trim_issue(i) for i in rec.get("issues") or []],
            "_order": rec.get("order") or 0,
        }
        for rec in records
    ]
    trimmed.sort(key=lambda rec: rec["_order"])
    for rec in trimmed:
        del rec["_order"]
    return trimmed


def list_build_logs(
    client: AzureDevOpsClient, project: str, build_id: int
) -> list[dict[str, Any]]:
    """List a build's logs as ``{id, line_count}`` entries.

    Use ``line_count`` with :func:`get_build_log`'s ``start_line`` to tail a
    large log instead of downloading it whole.
    """
    data = client.request("GET", f"{project}/_apis/build/builds/{build_id}/logs")
    logs = data.get("value", []) if isinstance(data, dict) else []
    return [{"id": log.get("id"), "line_count": log.get("lineCount")} for log in logs]


def get_build_log(
    client: AzureDevOpsClient,
    project: str,
    build_id: int,
    log_id: int,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Fetch a build log's content as plain text.

    Args:
        start_line / end_line: Optional line range. To tail, set ``start_line``
            to ``line_count - N`` (from :func:`list_build_logs`).
    """
    params: dict[str, Any] = {}
    if start_line is not None:
        params["startLine"] = start_line
    if end_line is not None:
        params["endLine"] = end_line
    data = client.request(
        "GET",
        f"{project}/_apis/build/builds/{build_id}/logs/{log_id}",
        params=params or None,
    )
    if isinstance(data, str):
        return data
    # Some servers return {"value": [line, ...]} JSON instead of text.
    if isinstance(data, dict):
        return "\n".join(str(line) for line in data.get("value", []))
    return "" if data is None else str(data)


def add_build_tags(
    client: AzureDevOpsClient, project: str, build_id: int, tags: list[str]
) -> list[str]:
    """Add tags to a build and return the build's resulting tag list."""
    if not tags:
        raise ValueError("tags must not be empty")
    data = client.request(
        "POST", f"{project}/_apis/build/builds/{build_id}/tags", json=tags
    )
    if isinstance(data, dict):
        return list(data.get("value", []))
    return list(data or [])
