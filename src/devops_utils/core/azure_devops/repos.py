"""Git repository queries against the Azure DevOps REST API.

Three search tiers, from most to least portable:
- :func:`list_repositories` with ``name_filter`` — repo metadata, everywhere.
- :func:`find_repo_items` — file paths via the Git Items API, everywhere.
- :func:`code_search` — content search via the Search extension, which cloud
  always has but on-prem servers may lack (it fails with a clear error there).
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Any

from devops_utils.core.azure_devops.client import AzureDevOpsClient, AzureDevOpsError


def list_repositories(
    client: AzureDevOpsClient,
    project: str | None = None,
    *,
    name_filter: str | None = None,
) -> list[dict[str, Any]]:
    """List Git repositories, optionally scoped to a single project.

    Args:
        name_filter: Optional case-insensitive substring to filter repo names by.

    Returns a trimmed list of ``{id, name, project, default_branch, web_url}``.
    """
    path = f"{project}/_apis/git/repositories" if project else "_apis/git/repositories"
    data = client.request("GET", path)
    repos = data.get("value", []) if isinstance(data, dict) else []
    needle = (name_filter or "").lower()
    return [
        {
            "id": repo.get("id"),
            "name": repo.get("name"),
            "project": (repo.get("project") or {}).get("name"),
            "default_branch": repo.get("defaultBranch"),
            "web_url": repo.get("webUrl"),
        }
        for repo in repos
        if needle in (repo.get("name") or "").lower()
    ]


def find_repo_items(
    client: AzureDevOpsClient,
    project: str,
    repo: str,
    *,
    path_pattern: str = "*",
    branch: str | None = None,
    top: int = 100,
) -> list[dict[str, Any]]:
    """Find files in a repository by path pattern (no Search extension needed).

    Lists the full tree via the Git Items API and matches each path against
    ``path_pattern`` with ``fnmatch`` (``*`` also crosses ``/`` here because a
    bare filename pattern like ``*.yml`` should match at any depth).

    Args:
        path_pattern: Glob matched against the repo-relative path (leading
            ``/`` stripped), e.g. ``*.yml`` or ``src/*/pipeline*``.
        branch: Optional branch to list (defaults to the repo default branch).
        top: Maximum number of matches to return.

    Returns:
        A list of ``{path, size, commit, url}`` dicts for matching blobs.
    """
    params: dict[str, Any] = {"recursionLevel": "Full", "scopePath": "/"}
    if branch:
        params["versionDescriptor.version"] = branch
        params["versionDescriptor.versionType"] = "branch"
    data = client.request(
        "GET", f"{project}/_apis/git/repositories/{repo}/items", params=params
    )
    items = data.get("value", []) if isinstance(data, dict) else []

    matches: list[dict[str, Any]] = []
    for item in items:
        if item.get("isFolder") or item.get("gitObjectType") == "tree":
            continue
        path = (item.get("path") or "").lstrip("/")
        # Match against the full path and the basename so `*.yml` finds nested files.
        if not (fnmatch(path, path_pattern) or fnmatch(path.rsplit("/", 1)[-1], path_pattern)):
            continue
        matches.append(
            {
                "path": path,
                "size": item.get("size"),
                "commit": item.get("commitId"),
                "url": item.get("url"),
            }
        )
        if len(matches) >= top:
            break
    return matches


def _search_base_url(org_url: str) -> str:
    """Derive the Search-service base URL from the org URL.

    Cloud hosts the Search API on ``almsearch.dev.azure.com``; on-prem serves
    it from the collection URL itself.
    """
    return org_url.replace("://dev.azure.com", "://almsearch.dev.azure.com", 1)


def code_search(
    client: AzureDevOpsClient,
    project: str,
    text: str,
    *,
    repo: str | None = None,
    branch: str | None = None,
    top: int = 25,
) -> list[dict[str, Any]]:
    """Search code content via the Search extension API.

    Cloud (dev.azure.com) always has the extension; on-prem servers need the
    Code Search extension installed — without it this raises a clear error, and
    :func:`find_repo_items` / WIQL work-item search are the fallbacks.

    Args:
        text: Search text (supports the code-search syntax, e.g. ``def:Foo``).
        repo: Optional repository name to scope to.
        branch: Optional branch to scope to.
        top: Maximum number of results.

    Returns:
        A list of ``{path, repo, project, matches}`` dicts, where ``matches``
        counts content hits in the file.
    """
    body: dict[str, Any] = {
        "searchText": text,
        "$top": top,
        "filters": {"Project": [project]},
    }
    if repo:
        body["filters"]["Repository"] = [repo]
    if branch:
        body["filters"]["Branch"] = [branch]

    try:
        data = client.request(
            "POST",
            f"{project}/_apis/search/codesearchresults",
            json=body,
            base_url=_search_base_url(client.org_url),
        )
    except AzureDevOpsError as exc:
        if exc.status_code == 404:
            raise AzureDevOpsError(
                exc.status_code,
                exc.method,
                exc.url,
                "Code search requires the Search extension, which this server "
                "does not have. Use find_repo_items (file-path search) or "
                "search_work_items instead.",
            ) from exc
        raise

    results = data.get("results", []) if isinstance(data, dict) else []
    return [
        {
            "path": (res.get("path") or "").lstrip("/"),
            "repo": (res.get("repository") or {}).get("name"),
            "project": (res.get("project") or {}).get("name"),
            "matches": len((res.get("matches") or {}).get("content") or []),
        }
        for res in results
    ]


def resolve_repo(client: AzureDevOpsClient, project: str, repo: str) -> dict[str, str]:
    """Look up a repository by id or name and return its ids.

    Returns ``{"project_id": ..., "repo_id": ...}``. Both GUIDs are needed to
    build the ``vstfs://`` artifact URIs used for commit/PR/branch links.
    """
    data = client.request("GET", f"{project}/_apis/git/repositories/{repo}")
    if not isinstance(data, dict) or not data.get("id"):
        raise ValueError(f"Repository {repo!r} not found in project {project!r}")
    project_id = (data.get("project") or {}).get("id")
    if not project_id:
        raise ValueError(f"Could not resolve project id for repository {repo!r}")
    return {"project_id": str(project_id), "repo_id": str(data["id"])}
