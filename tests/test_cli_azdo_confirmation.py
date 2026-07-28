"""Tests for the CLI write confirmation gate (human-in-the-loop).

Every ``devops-utils azdo`` write command previews the pending change and
either confirms interactively, honors ``--yes``/``--dry-run``, or defers to
``DEVOPS_UTILS_SKIP_CONFIRMATION`` — mirroring the MCP elicitation gate in
``devops_utils.mcp.server``. These tests stub the underlying ``tools.azdo_*``
calls so nothing hits the network.
"""

from click.testing import CliRunner

from devops_utils.cli.commands.azdo import azdo


def _run(args, input=None):
    return CliRunner().invoke(azdo, args, input=input)


def test_dry_run_previews_and_does_not_call_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: calls.append((a, k)),
    )
    result = _run(["comment", "7", "hi", "--dry-run"])
    assert result.exit_code == 0
    assert "dry run" in result.output
    assert calls == []


def test_declining_confirmation_does_not_call_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: calls.append((a, k)),
    )
    result = _run(["comment", "7", "hi"], input="n\n")
    assert result.exit_code == 0
    assert calls == []


def test_accepting_confirmation_calls_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: calls.append((a, k)) or {"id": 7},
    )
    result = _run(["comment", "7", "hi"], input="y\n")
    assert result.exit_code == 0
    assert calls == [((7, "hi"), {})]


def test_yes_flag_skips_prompt(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: calls.append((a, k)) or {"id": 7},
    )
    result = _run(["comment", "7", "hi", "--yes"])
    assert result.exit_code == 0
    assert calls == [((7, "hi"), {})]


def test_skip_confirmation_env_skips_prompt(monkeypatch):
    monkeypatch.setenv("DEVOPS_UTILS_SKIP_CONFIRMATION", "1")
    calls = []
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: calls.append((a, k)) or {"id": 7},
    )
    result = _run(["comment", "7", "hi"])
    assert result.exit_code == 0
    assert calls == [((7, "hi"), {})]


def test_build_tag_dry_run_does_not_call_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_tag_build",
        lambda *a, **k: calls.append((a, k)),
    )
    result = _run(["build-tag", "42", "flaky", "--project", "proj", "--dry-run"])
    assert result.exit_code == 0
    assert calls == []


def test_read_command_has_no_confirmation_options():
    result = _run(["get", "--help"])
    assert "--yes" not in result.output
    assert "--dry-run" not in result.output
