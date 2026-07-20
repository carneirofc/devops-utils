"""Git repository queries against the Azure DevOps REST API."""

from __future__ import annotations

from typing import Any

from devops_utils.core.azure_devops.client import AzureDevOpsClient


def list_repositories(
    client: AzureDevOpsClient, project: str | None = None
) -> list[dict[str, Any]]:
    """List Git repositories, optionally scoped to a single project.

    Returns a trimmed list of ``{id, name, project, default_branch, web_url}``.
    """
    path = f"{project}/_apis/git/repositories" if project else "_apis/git/repositories"
    data = client.request("GET", path)
    repos = data.get("value", []) if isinstance(data, dict) else []
    return [
        {
            "id": repo.get("id"),
            "name": repo.get("name"),
            "project": (repo.get("project") or {}).get("name"),
            "default_branch": repo.get("defaultBranch"),
            "web_url": repo.get("webUrl"),
        }
        for repo in repos
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
