"""Pull-request operations against the Azure DevOps REST API.

Commit comments are intentionally absent: Azure DevOps has no documented REST
endpoint for them (the web UI uses an internal API). Comment on the pull
request containing the commit, or on the work item that links it, instead.
"""

from __future__ import annotations

from typing import Any

from devops_utils.core.azure_devops.client import AzureDevOpsClient

# CommentThreadStatus "active" / CommentType "text" as wire integers.
_THREAD_ACTIVE = 1
_COMMENT_TEXT = 1


def comment_on_pull_request(
    client: AzureDevOpsClient,
    project: str,
    repo: str,
    pull_request_id: int,
    text: str,
    *,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Comment on a pull request.

    Without ``thread_id`` a new (active) comment thread is created; with it the
    comment is appended to that existing thread as a reply.

    Returns a trimmed ``{thread_id, comment_id, status}`` dict.
    """
    base = f"{project}/_apis/git/repositories/{repo}/pullRequests/{pull_request_id}"
    comment = {"parentCommentId": 0, "content": text, "commentType": _COMMENT_TEXT}

    if thread_id is None:
        data = client.request(
            "POST",
            f"{base}/threads",
            json={"comments": [comment], "status": _THREAD_ACTIVE},
        )
        thread = data if isinstance(data, dict) else {}
        comments = thread.get("comments") or [{}]
        return {
            "thread_id": thread.get("id"),
            "comment_id": comments[0].get("id"),
            "status": thread.get("status"),
        }

    data = client.request("POST", f"{base}/threads/{thread_id}/comments", json=comment)
    created = data if isinstance(data, dict) else {}
    return {"thread_id": thread_id, "comment_id": created.get("id"), "status": None}
