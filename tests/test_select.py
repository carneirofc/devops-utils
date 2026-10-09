"""Tests for shell-neutral output (``--output`` / ``--select``) — no jq needed."""

import json

import pytest
from click.testing import CliRunner

from devops_utils.cli.commands.azdo import azdo
from devops_utils.core.select import render, select

ITEM = {
    "id": 1400,
    "title": "Checkout",
    "fields": {"Microsoft.VSTS.Scheduling.StartDate": "2026-01-05T00:00:00Z"},
    "relations": [{"kind": "parent", "target": 1399}],
}


def test_select_single_path_returns_bare_value():
    assert select(ITEM, ["fields/Microsoft.VSTS.Scheduling.StartDate"]) == (
        "2026-01-05T00:00:00Z"
    )


def test_select_many_paths_keys_by_last_segment():
    assert select(ITEM, ["id", "relations/0/target"]) == {"id": 1400, "target": 1399}


def test_select_missing_path_is_none_and_lists_project_per_item():
    assert select([ITEM, {"id": 2}], ["title"]) == ["Checkout", None]


@pytest.mark.parametrize(
    ("value", "mode", "expected"),
    [
        (ITEM, "id", "1400"),
        ([ITEM, {"id": 2}], "id", "1400\n2"),
        ("2026-01-05", "raw", "2026-01-05"),
        (["a", 1, None], "raw", "a\n1\n"),
    ],
)
def test_render_modes(value, mode, expected):
    assert render(value, mode) == expected


def test_render_json_is_default_shape():
    assert json.loads(render(ITEM)) == ITEM


def test_cli_get_select_raw(monkeypatch):
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_get_work_item",
        lambda *a, **k: ITEM,
    )
    result = CliRunner().invoke(
        azdo,
        [
            "get",
            "1400",
            "--full",
            "--select",
            "fields/Microsoft.VSTS.Scheduling.StartDate",
            "-o",
            "raw",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == "2026-01-05T00:00:00Z\n"


def test_cli_create_output_id_keeps_stdout_pure(monkeypatch):
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_create_work_item",
        lambda *a, **k: {"id": 42, "title": "x"},
    )
    result = CliRunner().invoke(
        azdo,
        [
            "create",
            "--project",
            "P",
            "--type",
            "Epic",
            "--title",
            "x",
            "-y",
            "-o",
            "id",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == "42\n"
    assert "About to write" in result.stderr
