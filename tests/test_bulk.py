"""Tests for the bulk work-item plan (validate/preview/apply) and `azdo apply`."""

import json

import httpx
import pytest
from click.testing import CliRunner

from devops_utils.cli.commands.azdo import azdo
from devops_utils.core.azure_devops import (
    AzureDevOpsClient,
    PlanError,
    apply_plan,
    load_plan,
    plan_preview,
    validate_plan,
)

ORG = "https://dev.azure.com/contoso"


def _client(handler):
    return AzureDevOpsClient(
        org_url=ORG, token="tkn", transport=httpx.MockTransport(handler)
    )


def _echo_ids(store, start=100):
    """MockTransport handler recording requests and minting sequential ids."""
    counter = {"next": start}

    def handler(request: httpx.Request) -> httpx.Response:
        store.append(request)
        if request.method == "POST" and "/workitems/$" in str(request.url):
            wi_id = counter["next"]
            counter["next"] += 1
        else:
            # PATCH /workitems/{id} — echo the id back.
            tail = str(request.url.path).rstrip("/").rsplit("/", 1)[-1]
            wi_id = int(tail) if tail.isdigit() else 0
        return httpx.Response(
            200, json={"id": wi_id, "fields": {}, "url": f"u/{wi_id}"}
        )

    return handler


def _patch_ops(request: httpx.Request) -> list[dict]:
    return json.loads(request.content.decode())


# --------------------------------------------------------------------------- #
# load / validate
# --------------------------------------------------------------------------- #
def test_load_plan_rejects_non_mapping():
    with pytest.raises(PlanError):
        load_plan("- just\n- a list\n")


def test_validate_requires_items():
    with pytest.raises(PlanError, match="items"):
        validate_plan({"project": "P"})


def test_validate_create_needs_type_title_project():
    with pytest.raises(PlanError) as err:
        validate_plan({"items": [{"ref": "a"}]})
    msg = str(err.value)
    assert "requires 'type'" in msg
    assert "requires 'title'" in msg
    assert "no project" in msg


def test_validate_update_needs_id_and_create_rejects_id():
    with pytest.raises(PlanError, match="update requires 'id'"):
        validate_plan({"project": "P", "items": [{"action": "update", "state": "X"}]})
    with pytest.raises(PlanError, match="must not carry 'id'"):
        validate_plan(
            {
                "project": "P",
                "items": [{"action": "create", "id": 1, "type": "Bug", "title": "t"}],
            }
        )


def test_validate_forward_ref_and_duplicate_ref():
    with pytest.raises(PlanError, match="does not point at an earlier item"):
        validate_plan(
            {
                "project": "P",
                "items": [
                    {"type": "Task", "title": "t", "parent": "ref:later"},
                    {"ref": "later", "type": "Feature", "title": "f"},
                ],
            }
        )
    with pytest.raises(PlanError, match="duplicate ref"):
        validate_plan(
            {
                "project": "P",
                "items": [
                    {"ref": "a", "type": "Task", "title": "1"},
                    {"ref": "a", "type": "Task", "title": "2"},
                ],
            }
        )


def test_validate_link_rules():
    with pytest.raises(PlanError, match="kind must be one of"):
        validate_plan(
            {
                "project": "P",
                "items": [
                    {
                        "type": "Task",
                        "title": "t",
                        "links": [{"kind": "nope", "value": 1}],
                    }
                ],
            }
        )
    with pytest.raises(PlanError, match="requires 'repo'"):
        validate_plan(
            {
                "project": "P",
                "items": [
                    {
                        "type": "Task",
                        "title": "t",
                        "links": [{"kind": "commit", "value": "abc"}],
                    }
                ],
            }
        )


def test_validate_unknown_keys_warn_not_fail():
    items, warnings = validate_plan(
        {
            "project": "P",
            "items": [{"type": "Task", "title": "t", "Custom.RiskLevel": "High"}],
        }
    )
    assert len(items) == 1
    assert any("Custom.RiskLevel" in w and "fields" in w for w in warnings)


def test_defaults_merge_item_wins_fields_keywise():
    items, _ = validate_plan(
        {
            "project": "P",
            "defaults": {
                "type": "User Story",
                "area_path": "P\\Team",
                "fields": {"Custom.Source": "git", "Custom.RiskLevel": "Low"},
            },
            "items": [
                {"title": "s1", "fields": {"Custom.RiskLevel": "High"}},
                {"title": "f1", "type": "Feature"},
            ],
        }
    )
    assert items[0]["type"] == "User Story"
    assert items[0]["fields"] == {"Custom.Source": "git", "Custom.RiskLevel": "High"}
    assert items[1]["type"] == "Feature"
    assert items[1]["area_path"] == "P\\Team"


def test_plan_preview_summarizes():
    items, _ = validate_plan(
        {
            "project": "P",
            "items": [
                {
                    "ref": "f",
                    "type": "Feature",
                    "title": "t",
                    "links": [{"kind": "hyperlink", "value": "https://x"}],
                    "comments": ["a", "b"],
                }
            ],
        }
    )
    (entry,) = plan_preview(items)
    assert entry["action"] == "create"
    assert entry["links"] == ["hyperlink:https://x"]
    assert entry["comments"] == 2


# --------------------------------------------------------------------------- #
# apply
# --------------------------------------------------------------------------- #
def test_apply_creates_hierarchy_state_links_comments():
    reqs: list[httpx.Request] = []
    results = apply_plan(
        _client(_echo_ids(reqs)),
        {
            "project": "P",
            "items": [
                {
                    "ref": "feat",
                    "type": "Feature",
                    "title": "F",
                    "state": "Closed",
                    "links": [
                        {"kind": "hyperlink", "value": "https://a"},
                        {"kind": "build", "value": "9"},
                    ],
                    "comments": ["imported"],
                },
                {
                    "ref": "story",
                    "type": "User Story",
                    "title": "S",
                    "parent": "ref:feat",
                },
            ],
        },
    )
    assert [r["status"] for r in results] == ["created", "created"]
    assert results[0]["id"] == 100
    assert results[1]["id"] == 101

    creates = [r for r in reqs if r.method == "POST"]
    patches = [r for r in reqs if r.method == "PATCH"]
    assert len(creates) == 2
    # Follow-up state patch on the created feature.
    state_ops = _patch_ops(patches[0])
    assert state_ops == [
        {"op": "add", "path": "/fields/System.State", "value": "Closed"}
    ]
    # Both links land in ONE patch request.
    link_ops = _patch_ops(patches[1])
    assert len(link_ops) == 2
    assert {op["value"]["rel"] for op in link_ops} == {"Hyperlink", "ArtifactLink"}
    # Comment patch.
    assert _patch_ops(patches[2])[0]["path"] == "/fields/System.History"
    # The story's create carries a parent relation to the feature's new id.
    story_ops = json.loads(creates[1].content.decode())
    parent_op = next(op for op in story_ops if op["path"] == "/relations/-")
    assert parent_op["value"]["url"].endswith("/workItems/100")


def test_apply_update_passes_fields_through():
    reqs: list[httpx.Request] = []
    results = apply_plan(
        _client(_echo_ids(reqs)),
        {"items": [{"id": 7, "fields": {"Custom.RiskLevel": "Low"}}]},
    )
    assert results == [
        {"ref": None, "action": "update", "id": 7, "url": "u/7", "status": "updated"}
    ]
    ops = _patch_ops(reqs[0])
    assert ops == [{"op": "add", "path": "/fields/Custom.RiskLevel", "value": "Low"}]


def test_apply_continues_after_failure_and_fails_dependents():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "$Feature" in str(request.url):
            return httpx.Response(500, json={"message": "boom"})
        return httpx.Response(200, json={"id": 200, "fields": {}, "url": "u/200"})

    results = apply_plan(
        _client(handler),
        {
            "project": "P",
            "items": [
                {"ref": "feat", "type": "Feature", "title": "F"},
                {"type": "User Story", "title": "S", "parent": "ref:feat"},
                {"type": "Bug", "title": "B"},
            ],
        },
    )
    assert [r["status"] for r in results] == ["failed", "failed", "created"]
    assert "ref:feat" in results[1]["error"]


def test_apply_stop_on_error_skips_rest():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "boom"})

    results = apply_plan(
        _client(handler),
        {
            "project": "P",
            "items": [
                {"type": "Feature", "title": "F"},
                {"type": "Bug", "title": "B"},
            ],
        },
        stop_on_error=True,
    )
    assert [r["status"] for r in results] == ["failed", "skipped"]


# --------------------------------------------------------------------------- #
# CLI: azdo apply
# --------------------------------------------------------------------------- #
PLAN_YAML = """\
project: P
items:
  - ref: feat
    type: Feature
    title: F
  - type: User Story
    title: S
    parent: ref:feat
"""


def _run_apply(tmp_path, args, monkeypatch=None, stub=None, input=None):
    plan = tmp_path / "plan.yml"
    plan.write_text(PLAN_YAML, encoding="utf-8")
    if monkeypatch is not None:
        monkeypatch.setattr(
            "devops_utils.cli.commands.azdo.tools.azdo_apply_plan", stub
        )
    return CliRunner().invoke(azdo, ["apply", str(plan), *args], input=input)


def test_cli_apply_dry_run_reviews_without_calling(tmp_path, monkeypatch):
    calls = []
    result = _run_apply(
        tmp_path,
        ["--dry-run"],
        monkeypatch,
        lambda *a, **k: calls.append(a),
    )
    assert result.exit_code == 0, result.output
    assert "About to apply 2 operation(s)" in result.stderr
    assert "dry run" in result.stderr
    assert calls == []


def test_cli_apply_declined_confirmation_does_nothing(tmp_path, monkeypatch):
    calls = []
    result = _run_apply(
        tmp_path, [], monkeypatch, lambda *a, **k: calls.append(a), input="n\n"
    )
    assert result.exit_code == 0, result.output
    assert calls == []


def test_cli_apply_yes_outputs_results(tmp_path, monkeypatch):
    stub_results = [{"ref": "feat", "action": "create", "id": 1, "status": "created"}]
    result = _run_apply(tmp_path, ["--yes"], monkeypatch, lambda *a, **k: stub_results)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == stub_results


def test_cli_apply_failure_sets_exit_code(tmp_path, monkeypatch):
    stub_results = [
        {
            "ref": "feat",
            "action": "create",
            "id": None,
            "status": "failed",
            "error": "x",
        }
    ]
    result = _run_apply(tmp_path, ["--yes"], monkeypatch, lambda *a, **k: stub_results)
    assert result.exit_code == 1
    assert "1 item(s) failed" in result.stderr


def test_cli_apply_out_writes_results_file(tmp_path, monkeypatch):
    stub_results = [{"ref": "feat", "action": "create", "id": 1, "status": "created"}]
    out = tmp_path / "results.json"
    result = _run_apply(
        tmp_path,
        ["--yes", "--out", str(out)],
        monkeypatch,
        lambda *a, **k: stub_results,
    )
    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text(encoding="utf-8")) == stub_results


def test_cli_apply_invalid_plan_errors_before_confirmation(tmp_path):
    plan = tmp_path / "plan.yml"
    plan.write_text("items:\n  - title: no type or project\n", encoding="utf-8")
    result = CliRunner().invoke(azdo, ["apply", str(plan), "--yes"])
    assert result.exit_code != 0
    assert "invalid plan" in result.output + result.stderr
