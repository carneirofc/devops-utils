"""Tests for the ``devops-utils setup`` command group and install helpers."""

import json

from click.testing import CliRunner

from devops_utils.agent import install
from devops_utils.cli.main import cli

AZDO_ENV_KEYS = (
    "AZURE_DEVOPS_ORG_URL",
    "AZURE_DEVOPS_TOKEN",
    "AZURE_DEVOPS_AUTH_SCHEME",
    "AZURE_DEVOPS_API_VERSION",
)


def test_bundled_skills_are_discoverable():
    names = {name for name, _filename, _text in install.iter_bundled_skills()}
    assert "azure-devops-work-items" in names
    assert "sanitize-manifest" in names


def test_setup_skills_flat_layout(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "skills", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "azure-devops.md").exists()
    assert (tmp_path / "sanitize.md").exists()


def test_setup_skills_claude_layout(tmp_path):
    result = CliRunner().invoke(
        cli,
        ["setup", "skills", "--dest", str(tmp_path), "--claude-layout"],
    )
    assert result.exit_code == 0, result.output
    skill = tmp_path / "skills" / "azure-devops-work-items" / "SKILL.md"
    assert skill.exists()
    assert "name: azure-devops-work-items" in skill.read_text(encoding="utf-8")


def test_setup_mcp_registers_server(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "mcp", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert data["mcpServers"]["devops-utils"]["command"] == "devops-utils-mcp"


def test_setup_mcp_preserves_existing_servers(tmp_path):
    cfg = tmp_path / ".mcp.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"other": {"command": "keep-me"}}}),
        encoding="utf-8",
    )
    install.merge_mcp_config(cfg)
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["other"]["command"] == "keep-me"
    assert data["mcpServers"]["devops-utils"]["command"] == "devops-utils-mcp"


def test_setup_mcp_skips_when_present_without_force(tmp_path):
    cfg = tmp_path / ".mcp.json"
    _path, changed = install.merge_mcp_config(cfg)
    assert changed is True
    _path, changed = install.merge_mcp_config(cfg)
    assert changed is False


def test_setup_env_writes_all_keys(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "env", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    text = (tmp_path / ".env.devops-utils.example").read_text(encoding="utf-8")
    for key in AZDO_ENV_KEYS:
        assert key in text


def test_setup_skips_existing_without_force(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(cli, ["setup", "skills", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == "SENTINEL"
    assert "skip" in result.output


def test_setup_force_overwrites(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path), "--force"]
    )
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") != "SENTINEL"


def test_setup_all_writes_everything(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "all", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "azure-devops.md").exists()
    assert (tmp_path / ".mcp.json").exists()
    assert (tmp_path / ".env.devops-utils.example").exists()
