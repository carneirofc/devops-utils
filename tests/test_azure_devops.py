"""Tests for the Azure DevOps client and work-item helpers (mocked transport)."""

import base64
import json

import httpx
import pytest

from devops_utils.core.azure_devops import (
    AzureDevOpsClient,
    AzureDevOpsError,
    add_attachment,
    add_link,
    create_work_item,
    search_work_items,
    set_tags,
    update_work_item,
)

ORG = "https://dev.azure.com/contoso"


def _client(handler, **kwargs):
    return AzureDevOpsClient(
        org_url=ORG,
        token="tkn",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _record(store):
    """Return a MockTransport handler that records requests and echoes JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode() if request.content else ""
        store.append(request)
        # Default: echo an empty work item shell.
        return httpx.Response(
            200, json={"id": 42, "fields": {}, "url": "u", "_body": body}
        )

    return handler


# --------------------------------------------------------------------------- #
# auth + config
# --------------------------------------------------------------------------- #
def test_bearer_auth_header():
    reqs: list[httpx.Request] = []
    create_work_item(_client(_record(reqs)), "Proj", "Task", "hi")
    assert reqs[0].headers["Authorization"] == "Bearer tkn"


def test_pat_auth_header_uses_basic():
    reqs: list[httpx.Request] = []
    create_work_item(_client(_record(reqs), auth_scheme="pat"), "Proj", "Task", "hi")
    expected = "Basic " + base64.b64encode(b":tkn").decode()
    assert reqs[0].headers["Authorization"] == expected


def test_from_env_requires_token(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_ORG_URL", ORG)
    monkeypatch.delenv("AZURE_DEVOPS_TOKEN", raising=False)
    with pytest.raises(ValueError, match="AZURE_DEVOPS_TOKEN"):
        AzureDevOpsClient.from_env()


def test_api_version_injected():
    reqs: list[httpx.Request] = []
    create_work_item(_client(_record(reqs), api_version="6.0"), "Proj", "Task", "hi")
    assert reqs[0].url.params["api-version"] == "6.0"


def test_non_2xx_raises():
    def handler(request):
        return httpx.Response(404, text="nope")

    with pytest.raises(AzureDevOpsError) as exc:
        create_work_item(_client(handler), "Proj", "Task", "hi")
    assert exc.value.status_code == 404


# --------------------------------------------------------------------------- #
# create / tags
# --------------------------------------------------------------------------- #
def test_create_sends_json_patch():
    reqs: list[httpx.Request] = []
    create_work_item(
        _client(_record(reqs)),
        "Proj",
        "Bug",
        "Title",
        description="desc",
        tags=["a", "b"],
    )
    req = reqs[0]
    assert req.method == "POST"
    assert req.url.path.endswith("/Proj/_apis/wit/workitems/$Bug")
    assert req.headers["Content-Type"] == "application/json-patch+json"
    ops = json.loads(req.content)
    paths = {op["path"]: op["value"] for op in ops}
    assert paths["/fields/System.Title"] == "Title"
    assert paths["/fields/System.Tags"] == "a; b"


def test_set_tags_add_merges_existing():
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"fields": {"System.Tags": "keep; old"}})
        return httpx.Response(200, json={"id": 1, "fields": {}})

    set_tags(_client(handler), 1, ["old", "new"], mode="add")
    patch = [c for c in calls if c.method == "PATCH"][0]
    value = json.loads(patch.content)[0]["value"]
    # existing preserved, duplicate 'old' not repeated, 'new' appended
    assert value == "keep; old; new"


# --------------------------------------------------------------------------- #
# update
# --------------------------------------------------------------------------- #
def test_update_sends_json_patch():
    reqs: list[httpx.Request] = []
    update_work_item(
        _client(_record(reqs)),
        42,
        state="Closed",
        assigned_to="dev@contoso.com",
        title="New title",
        description="<p>d</p>",
    )
    req = reqs[0]
    assert req.method == "PATCH"
    assert req.url.path.endswith("/_apis/wit/workitems/42")
    assert req.headers["Content-Type"] == "application/json-patch+json"
    paths = {op["path"]: op["value"] for op in json.loads(req.content)}
    assert paths == {
        "/fields/System.State": "Closed",
        "/fields/System.AssignedTo": "dev@contoso.com",
        "/fields/System.Title": "New title",
        "/fields/System.Description": "<p>d</p>",
    }


def test_update_single_field_only_patches_that_field():
    reqs: list[httpx.Request] = []
    update_work_item(_client(_record(reqs)), 42, state="Resolved")
    ops = json.loads(reqs[0].content)
    assert ops == [{"op": "add", "path": "/fields/System.State", "value": "Resolved"}]


def test_update_requires_at_least_one_field():
    with pytest.raises(ValueError, match="nothing to update"):
        update_work_item(_client(_record([])), 42)


# --------------------------------------------------------------------------- #
# links (references)
# --------------------------------------------------------------------------- #
def _repo_handler(store):
    def handler(request):
        store.append(request)
        if "git/repositories" in request.url.path:
            return httpx.Response(
                200, json={"id": "repo-guid", "project": {"id": "proj-guid"}}
            )
        return httpx.Response(200, json={"id": 7, "fields": {}})

    return handler


def test_add_commit_link_builds_vstfs_uri():
    reqs: list[httpx.Request] = []
    add_link(
        _client(_repo_handler(reqs)), 7, "commit", "abc123", project="Proj", repo="R"
    )
    patch = [r for r in reqs if r.method == "PATCH"][0]
    rel = json.loads(patch.content)[0]["value"]
    assert rel["rel"] == "ArtifactLink"
    assert rel["url"] == "vstfs:///Git/Commit/proj-guid%2Frepo-guid%2Fabc123"


def test_add_pull_request_link_uri():
    reqs: list[httpx.Request] = []
    add_link(
        _client(_repo_handler(reqs)), 7, "pull_request", "55", project="Proj", repo="R"
    )
    rel = json.loads([r for r in reqs if r.method == "PATCH"][0].content)[0]["value"]
    assert rel["url"] == "vstfs:///Git/PullRequestId/proj-guid%2Frepo-guid%2F55"


def test_add_branch_link_uri():
    reqs: list[httpx.Request] = []
    add_link(
        _client(_repo_handler(reqs)), 7, "branch", "main", project="Proj", repo="R"
    )
    rel = json.loads([r for r in reqs if r.method == "PATCH"][0].content)[0]["value"]
    assert rel["url"] == "vstfs:///Git/Ref/proj-guid%2Frepo-guid%2FGBmain"


def test_hyperlink_link():
    reqs: list[httpx.Request] = []
    add_link(_client(_record(reqs)), 7, "hyperlink", "https://x.test")
    rel = json.loads(reqs[0].content)[0]["value"]
    assert rel == {"rel": "Hyperlink", "url": "https://x.test"}


def test_work_item_link_uses_related():
    reqs: list[httpx.Request] = []
    add_link(_client(_record(reqs)), 7, "work_item", "99")
    rel = json.loads(reqs[0].content)[0]["value"]
    assert rel["rel"] == "System.LinkTypes.Related"
    assert rel["url"].endswith("/_apis/wit/workItems/99")


@pytest.mark.parametrize(
    ("kind", "relation"),
    [
        ("parent", "System.LinkTypes.Hierarchy-Reverse"),
        ("child", "System.LinkTypes.Hierarchy-Forward"),
        ("predecessor", "System.LinkTypes.Dependency-Reverse"),
        ("successor", "System.LinkTypes.Dependency-Forward"),
    ],
)
def test_hierarchy_and_dependency_link_relations(kind, relation):
    reqs: list[httpx.Request] = []
    add_link(_client(_record(reqs)), 7, kind, "99")
    rel = json.loads(reqs[0].content)[0]["value"]
    assert rel["rel"] == relation
    assert rel["url"].endswith("/_apis/wit/workItems/99")


def test_commit_link_requires_project_and_repo():
    with pytest.raises(ValueError, match="requires both"):
        add_link(_client(_record([])), 7, "commit", "abc")


def test_invalid_link_kind():
    with pytest.raises(ValueError, match="kind must be one of"):
        add_link(_client(_record([])), 7, "bogus", "x")


# --------------------------------------------------------------------------- #
# attachments (2-step)
# --------------------------------------------------------------------------- #
def test_add_attachment_two_step(tmp_path):
    f = tmp_path / "log.txt"
    f.write_bytes(b"hello")
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/_apis/wit/attachments"):
            return httpx.Response(201, json={"id": "att", "url": "https://att.test/1"})
        return httpx.Response(200, json={"id": 7, "fields": {}})

    add_attachment(_client(handler), 7, str(f), comment="see log")

    upload = calls[0]
    assert upload.method == "POST"
    assert upload.url.params["fileName"] == "log.txt"
    assert upload.content == b"hello"

    patch = calls[1]
    rel = json.loads(patch.content)[0]["value"]
    assert rel["rel"] == "AttachedFile"
    assert rel["url"] == "https://att.test/1"
    assert rel["attributes"]["comment"] == "see log"


# --------------------------------------------------------------------------- #
# search (WIQL)
# --------------------------------------------------------------------------- #
def test_search_uses_wiql_contains():
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/_apis/wit/wiql"):
            return httpx.Response(200, json={"workItems": [{"id": 3}]})
        return httpx.Response(
            200,
            json={"value": [{"id": 3, "fields": {"System.Title": "found"}}]},
        )

    results = search_work_items(_client(handler), "Proj", "needle", types=["Bug"])
    wiql = json.loads(calls[0].content)["query"]
    assert "CONTAINS 'needle'" in wiql
    assert "[System.WorkItemType] IN ('Bug')" in wiql
    assert results == [
        {
            "id": 3,
            "type": None,
            "title": "found",
            "state": None,
            "assigned_to": None,
            "tags": None,
            "url": None,
        }
    ]


def test_wiql_escapes_single_quotes():
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"workItems": []})

    search_work_items(_client(handler), "Proj", "O'Brien")
    wiql = json.loads(calls[0].content)["query"]
    assert "O''Brien" in wiql
