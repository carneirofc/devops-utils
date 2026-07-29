"""Tests for the CLI write confirmation gate (human-in-the-loop).

Every ``devops-utils azdo`` write command previews the pending change and
either confirms interactively, honors ``--yes``/``--dry-run``, or defers to
``DEVOPS_UTILS_SKIP_CONFIRMATION`` — mirroring the MCP elicitation gate in
``devops_utils.mcp.server``. These tests stub the underlying ``tools.azdo_*``
calls so nothing hits the network.
"""

import json

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
    assert "dry run" in result.stderr
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


def test_write_keeps_stdout_pure_json(monkeypatch):
    """``azdo create … --yes | jq`` must work: the preview belongs on stderr."""
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: {"id": 7},
    )
    result = _run(["comment", "7", "hi", "--yes"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"id": 7}
    assert "About to write" in result.stderr


def test_dry_run_writes_nothing_to_stdout(monkeypatch):
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: {"id": 7},
    )
    result = _run(["comment", "7", "hi", "--dry-run"])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_confirmation_prompt_is_on_stderr(monkeypatch):
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_comment_work_item",
        lambda *a, **k: {"id": 7},
    )
    result = _run(["comment", "7", "hi"], input="y\n")
    assert result.exit_code == 0
    assert "Apply this change?" in result.stderr
    # ``result.stdout`` also carries the runner's echo of the simulated
    # keystrokes — that is a CliRunner artifact (a real terminal echoes typed
    # input itself), so check for the payload rather than parsing the stream.
    assert '"id": 7' in result.stdout


def test_read_command_has_no_confirmation_options():
    result = _run(["get", "--help"])
    assert "--yes" not in result.output
    assert "--dry-run" not in result.output


def test_get_full_flag_forwards_to_tool(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "devops_utils.cli.commands.azdo.tools.azdo_get_work_item",
        lambda wid, **k: seen.update(id=wid, **k) or {"id": wid},
    )
    result = _run(["get", "7", "--full"])
    assert result.exit_code == 0
    assert seen == {"id": 7, "relations": False, "full": True}
