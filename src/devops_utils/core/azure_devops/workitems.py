"""Work-item operations against the Azure DevOps REST API.

All functions are pure in the sense that they take an explicit
:class:`AzureDevOpsClient`; nothing here reads global state or machine creds.

Design notes for cross-compat (cloud + on-prem Server):
- Comments use the ``System.History`` field patch, which every server supports,
  rather than the preview-only ``/comments`` endpoint.
- Search uses WIQL ``CONTAINS`` rather than the Search extension (a separate host
  that is not always present on-prem).
"""

from __future__ import annotations

import os
from typing import Any

from devops_utils.core.azure_devops.client import AzureDevOpsClient
from devops_utils.core.azure_devops.repos import resolve_repo

JSON_PATCH = "application/json-patch+json"

# Reference kinds accepted by :func:`add_link`.
LINK_KINDS = (
    "commit",
    "pull_request",
    "branch",
    "build",
    "work_item",
    "parent",
    "child",
    "predecessor",
    "successor",
    "hyperlink",
)

# Work-item-to-work-item relation names, keyed by link kind.
WORK_ITEM_RELATIONS = {
    "work_item": "System.LinkTypes.Related",
    "parent": "System.LinkTypes.Hierarchy-Reverse",
    "child": "System.LinkTypes.Hierarchy-Forward",
    "predecessor": "System.LinkTypes.Dependency-Reverse",
    "successor": "System.LinkTypes.Dependency-Forward",
}

# Inverse of WORK_ITEM_RELATIONS, for turning raw relations back into kinds.
_RELATION_KINDS = {rel: kind for kind, rel in WORK_ITEM_RELATIONS.items()}

# vstfs URL prefixes identifying the artifact behind an ArtifactLink.
_ARTIFACT_KINDS = {
    "vstfs:///Git/Commit/": "commit",
    "vstfs:///Git/PullRequestId/": "pull_request",
    "vstfs:///Git/Ref/": "branch",
    "vstfs:///Build/Build/": "build",
}


def _trim(item: dict[str, Any]) -> dict[str, Any]:
    """Shrink a raw work item to the fields agents care about."""
    fields = item.get("fields", {}) if isinstance(item, dict) else {}
    return {
        "id": item.get("id"),
        "type": fields.get("System.WorkItemType"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "assigned_to": (fields.get("System.AssignedTo") or {}).get("displayName")
        if isinstance(fields.get("System.AssignedTo"), dict)
        else fields.get("System.AssignedTo"),
        "tags": fields.get("System.Tags"),
        "url": item.get("url"),
    }


def create_work_item(
    client: AzureDevOpsClient,
    project: str,
    work_item_type: str,
    title: str,
    *,
    description: str | None = None,
    tags: list[str] | None = None,
    area_path: str | None = None,
    iteration_path: str | None = None,
    assigned_to: str | None = None,
    parent: int | None = None,
) -> dict[str, Any]:
    """Create a work item and return the trimmed result.

    Args:
        project: Team project name or id.
        work_item_type: e.g. ``Bug``, ``Task``, ``User Story``.
        title: Work-item title (``System.Title``).
        description: Optional ``System.Description`` (HTML).
        tags: Optional list of tags.
        area_path / iteration_path: Optional classification nodes.
        assigned_to: Optional identity (email or display name).
        parent: Optional parent work-item id; links the new item under it.
    """
    ops: list[dict[str, Any]] = [_add("/fields/System.Title", title)]
    if description:
        ops.append(_add("/fields/System.Description", description))
    if tags:
        ops.append(_add("/fields/System.Tags", "; ".join(tags)))
    if area_path:
        ops.append(_add("/fields/System.AreaPath", area_path))
    if iteration_path:
        ops.append(_add("/fields/System.IterationPath", iteration_path))
    if assigned_to:
        ops.append(_add("/fields/System.AssignedTo", assigned_to))
    if parent is not None:
        rel, url, _ = _build_relation(client, "parent", str(parent), None, None)
        ops.append(_add("/relations/-", {"rel": rel, "url": url}))

    data = client.request(
        "POST",
        f"{project}/_apis/wit/workitems/${work_item_type}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def get_work_item(
    client: AzureDevOpsClient, work_item_id: int, *, relations: bool = False
) -> dict[str, Any]:
    """Fetch a single work item (trimmed).

    Args:
        relations: When true, include the item's relations (parent/child links,
            related work items, hyperlinks, attachments, artifact links) as a
            ``relations`` list of ``{kind, target, ...}`` dicts.
    """
    params = {"$expand": "relations"} if relations else None
    data = client.request("GET", f"_apis/wit/workitems/{work_item_id}", params=params)
    trimmed = _trim(data)
    if relations:
        raw = data.get("relations") or [] if isinstance(data, dict) else []
        trimmed["relations"] = [_trim_relation(rel) for rel in raw]
    return trimmed


def add_comment(
    client: AzureDevOpsClient, work_item_id: int, text: str
) -> dict[str, Any]:
    """Add a comment to a work item via the ``System.History`` field."""
    ops = [_add("/fields/System.History", text)]
    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def set_tags(
    client: AzureDevOpsClient,
    work_item_id: int,
    tags: list[str],
    mode: str = "add",
) -> dict[str, Any]:
    """Set work-item tags.

    Args:
        tags: Tags to apply.
        mode: ``"add"`` merges with existing tags; ``"replace"`` overwrites.
    """
    if mode not in ("add", "replace"):
        raise ValueError(f"mode must be 'add' or 'replace', got {mode!r}")

    final = list(tags)
    if mode == "add":
        current = client.request("GET", f"_apis/wit/workitems/{work_item_id}")
        existing_raw = (current.get("fields", {}) or {}).get("System.Tags", "")
        existing = [t.strip() for t in existing_raw.split(";") if t.strip()]
        seen = {t.lower() for t in existing}
        final = existing + [t for t in tags if t.lower() not in seen]

    ops = [_add("/fields/System.Tags", "; ".join(final))]
    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def update_work_item(
    client: AzureDevOpsClient,
    work_item_id: int,
    *,
    state: str | None = None,
    assigned_to: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Update mutable fields of an existing work item.

    Args:
        state: New ``System.State`` (process-template-specific, e.g. ``Closed``,
            ``Done``, ``Resolved``).
        assigned_to: New assignee identity (email or display name).
        title: New ``System.Title``.
        description: New ``System.Description`` (HTML).

    Raises:
        ValueError: If no field to update was given.
    """
    ops: list[dict[str, Any]] = []
    if state is not None:
        ops.append(_add("/fields/System.State", state))
    if assigned_to is not None:
        ops.append(_add("/fields/System.AssignedTo", assigned_to))
    if title is not None:
        ops.append(_add("/fields/System.Title", title))
    if description is not None:
        ops.append(_add("/fields/System.Description", description))
    if not ops:
        raise ValueError(
            "nothing to update: give at least one of "
            "state/assigned_to/title/description"
        )

    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def add_link(
    client: AzureDevOpsClient,
    work_item_id: int,
    kind: str,
    value: str,
    *,
    project: str | None = None,
    repo: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """Add a reference (relation) to a work item.

    Args:
        kind: One of ``commit``, ``pull_request``, ``branch`` (all need
            ``project`` + ``repo``), ``build`` (``value`` = build id),
            ``work_item`` / ``parent`` / ``child`` / ``predecessor`` /
            ``successor`` (``value`` = target work-item id),
            or ``hyperlink`` (``value`` = raw URL).
        value: Commit SHA / PR id / branch name / build id / work-item id / URL
            per ``kind``.
        project: Team project (required for commit/pull_request/branch).
        repo: Repository name or id (required for commit/pull_request/branch).
        comment: Optional note stored on the relation.
    """
    rel, url, name = _build_relation(client, kind, value, project, repo)

    attributes: dict[str, Any] = {}
    if name:
        attributes["name"] = name
    if comment:
        attributes["comment"] = comment

    relation: dict[str, Any] = {"rel": rel, "url": url}
    if attributes:
        relation["attributes"] = attributes

    ops = [_add("/relations/-", relation)]
    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def remove_link(
    client: AzureDevOpsClient,
    work_item_id: int,
    kind: str,
    value: str,
    *,
    project: str | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    """Remove a reference (relation) from a work item.

    Accepts the same ``kind``/``value`` pairs as :func:`add_link`. The relation
    is located by matching its rel type and URL, then removed by index with a
    guarding ``test`` op (the REST API only removes relations by index).

    Raises:
        ValueError: If no matching relation exists on the work item.
    """
    rel, url, _ = _build_relation(client, kind, value, project, repo)

    data = client.request(
        "GET",
        f"_apis/wit/workitems/{work_item_id}",
        params={"$expand": "relations"},
    )
    existing = data.get("relations") or [] if isinstance(data, dict) else []
    index = next(
        (
            i
            for i, r in enumerate(existing)
            if r.get("rel") == rel and (r.get("url") or "").lower() == url.lower()
        ),
        None,
    )
    if index is None:
        present = [_trim_relation(r) for r in existing]
        raise ValueError(
            f"work item {work_item_id} has no {kind!r} relation to {value!r}; "
            f"existing relations: {present}"
        )

    ops = [
        {
            "op": "test",
            "path": f"/relations/{index}/url",
            "value": existing[index]["url"],
        },
        {"op": "remove", "path": f"/relations/{index}"},
    ]
    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def add_attachment(
    client: AzureDevOpsClient,
    work_item_id: int,
    file_path: str,
    *,
    comment: str | None = None,
) -> dict[str, Any]:
    """Upload a local file and attach it to a work item (2-step)."""
    with open(file_path, "rb") as fh:
        content = fh.read()
    file_name = os.path.basename(file_path)

    uploaded = client.request(
        "POST",
        "_apis/wit/attachments",
        params={"fileName": file_name},
        content=content,
        content_type="application/octet-stream",
    )
    attachment_url = uploaded.get("url") if isinstance(uploaded, dict) else None
    if not attachment_url:
        raise RuntimeError("Attachment upload did not return a url")

    attributes: dict[str, Any] = {"name": file_name}
    if comment:
        attributes["comment"] = comment
    relation = {"rel": "AttachedFile", "url": attachment_url, "attributes": attributes}

    ops = [_add("/relations/-", relation)]
    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)


def query_wiql(
    client: AzureDevOpsClient, project: str, wiql: str, top: int = 50
) -> list[int]:
    """Run a WIQL query and return the matching work-item ids."""
    data = client.request(
        "POST",
        f"{project}/_apis/wit/wiql",
        params={"$top": top},
        json={"query": wiql},
    )
    rows = data.get("workItems", []) if isinstance(data, dict) else []
    return [row["id"] for row in rows if "id" in row]


def list_work_items(
    client: AzureDevOpsClient,
    project: str,
    *,
    states: list[str] | None = None,
    types: list[str] | None = None,
    assigned_to: str | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """List work items in a project, optionally filtered by state/type/assignee."""
    clauses = [f"[System.TeamProject] = '{_esc(project)}'"]
    if states:
        clauses.append(_in_clause("System.State", states))
    if types:
        clauses.append(_in_clause("System.WorkItemType", types))
    if assigned_to:
        clauses.append(f"[System.AssignedTo] = '{_esc(assigned_to)}'")
    # WIQL, not SQL; all interpolated values pass through _esc(). nosec B608
    wiql = (
        "SELECT [System.Id] FROM WorkItems WHERE "  # nosec B608
        + " AND ".join(clauses)
        + " ORDER BY [System.ChangedDate] DESC"
    )
    ids = query_wiql(client, project, wiql, top=top)
    return _get_batch(client, ids)


def search_work_items(
    client: AzureDevOpsClient,
    project: str,
    text: str,
    *,
    states: list[str] | None = None,
    types: list[str] | None = None,
    top: int = 50,
) -> list[dict[str, Any]]:
    """Text-search work items by title/description using WIQL ``CONTAINS``."""
    term = _esc(text)
    clauses = [
        f"[System.TeamProject] = '{_esc(project)}'",
        f"([System.Title] CONTAINS '{term}' OR [System.Description] CONTAINS '{term}')",
    ]
    if states:
        clauses.append(_in_clause("System.State", states))
    if types:
        clauses.append(_in_clause("System.WorkItemType", types))
    # WIQL, not SQL; all interpolated values pass through _esc(). nosec B608
    wiql = (
        "SELECT [System.Id] FROM WorkItems WHERE "  # nosec B608
        + " AND ".join(clauses)
        + " ORDER BY [System.ChangedDate] DESC"
    )
    ids = query_wiql(client, project, wiql, top=top)
    return _get_batch(client, ids)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _add(path: str, value: Any) -> dict[str, Any]:
    return {"op": "add", "path": path, "value": value}


def _build_relation(
    client: AzureDevOpsClient,
    kind: str,
    value: str,
    project: str | None,
    repo: str | None,
) -> tuple[str, str, str | None]:
    """Resolve a link ``kind``/``value`` pair to ``(rel, url, name)``."""
    if kind not in LINK_KINDS:
        raise ValueError(f"kind must be one of {LINK_KINDS}, got {kind!r}")

    if kind == "build":
        # Build artifact URIs carry only the build id; no project/repo needed.
        return "ArtifactLink", f"vstfs:///Build/Build/{value}", "Build"
    if kind in ("commit", "pull_request", "branch"):
        if not project or not repo:
            raise ValueError(f"kind {kind!r} requires both 'project' and 'repo'")
        ids = resolve_repo(client, project, repo)
        artifact = f"{ids['project_id']}%2F{ids['repo_id']}%2F"
        if kind == "commit":
            return (
                "ArtifactLink",
                f"vstfs:///Git/Commit/{artifact}{value}",
                "Fixed in Commit",
            )
        if kind == "pull_request":
            return (
                "ArtifactLink",
                f"vstfs:///Git/PullRequestId/{artifact}{value}",
                "Pull Request",
            )
        return "ArtifactLink", f"vstfs:///Git/Ref/{artifact}GB{value}", "Branch"
    if kind in WORK_ITEM_RELATIONS:
        rel = WORK_ITEM_RELATIONS[kind]
        return rel, client._url(f"_apis/wit/workItems/{value}"), None
    return "Hyperlink", value, None  # hyperlink


def _trim_relation(relation: dict[str, Any]) -> dict[str, Any]:
    """Shrink a raw relation to ``{kind, target, ...}`` for agents.

    Work-item relations get the target work-item id as an int; everything else
    keeps its URL. Unknown rel types pass through with the raw rel as ``kind``.
    """
    rel = relation.get("rel", "")
    url = relation.get("url", "")
    attributes = relation.get("attributes") or {}

    target: Any = url
    if rel in _RELATION_KINDS:
        kind = _RELATION_KINDS[rel]
        tail = url.rstrip("/").rsplit("/", 1)[-1]
        target = int(tail) if tail.isdigit() else url
    elif rel == "Hyperlink":
        kind = "hyperlink"
    elif rel == "AttachedFile":
        kind = "attachment"
    elif rel == "ArtifactLink":
        kind = next(
            (k for prefix, k in _ARTIFACT_KINDS.items() if url.startswith(prefix)),
            "artifact",
        )
    else:
        kind = rel

    trimmed: dict[str, Any] = {"kind": kind, "target": target}
    if attributes.get("name"):
        trimmed["name"] = attributes["name"]
    if attributes.get("comment"):
        trimmed["comment"] = attributes["comment"]
    return trimmed


def _esc(value: str) -> str:
    """Escape single quotes for embedding in a WIQL string literal."""
    return value.replace("'", "''")


def _in_clause(field: str, values: list[str]) -> str:
    joined = ", ".join(f"'{_esc(v)}'" for v in values)
    return f"[{field}] IN ({joined})"


def _get_batch(client: AzureDevOpsClient, ids: list[int]) -> list[dict[str, Any]]:
    if not ids:
        return []
    joined = ",".join(str(i) for i in ids)
    data = client.request("GET", "_apis/wit/workitems", params={"ids": joined})
    items = data.get("value", []) if isinstance(data, dict) else []
    return [_trim(item) for item in items]
