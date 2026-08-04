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
    assert "azure-devops-research" in names
    assert "git-history-workitems" in names
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


def test_setup_mcp_registers_uvx_server_by_default(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "mcp", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    entry = data["mcpServers"]["devops-utils"]
    assert entry["command"] == "uvx"
    assert entry["args"] == ["--from", "devops-utils[mcp]", "devops-utils-mcp"]


def test_setup_mcp_no_uvx_registers_console_script(tmp_path):
    result = CliRunner().invoke(
        cli, ["setup", "mcp", "--dest", str(tmp_path), "--no-uvx"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    entry = data["mcpServers"]["devops-utils"]
    assert entry["command"] == "devops-utils-mcp"
    assert entry["args"] == []


def test_setup_mcp_preserves_existing_servers(tmp_path):
    cfg = tmp_path / ".mcp.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"other": {"command": "keep-me"}}}),
        encoding="utf-8",
    )
    install.merge_mcp_config(cfg)
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["other"]["command"] == "keep-me"
    assert data["mcpServers"]["devops-utils"]["command"] == "uvx"


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


def test_setup_prompt_yes_overwrites(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path)], input="y\n"
    )
    assert result.exit_code == 0, result.output
    assert "SENTINEL" not in target.read_text(encoding="utf-8")
    assert "overwrite" in result.stderr


def test_setup_prompt_no_keeps_existing(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path)], input="n\n"
    )
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == "SENTINEL"
    assert "skip" in result.output


def test_setup_prompt_diff_then_overwrite(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path)], input="d\ny\n"
    )
    assert result.exit_code == 0, result.output
    assert "--- " in result.stderr and "+++ " in result.stderr
    assert "-SENTINEL" in result.stderr
    assert "SENTINEL" not in target.read_text(encoding="utf-8")


def _seed_two_skills(tmp_path):
    targets = [tmp_path / "azure-devops.md", tmp_path / "sanitize.md"]
    for target in targets:
        target.write_text("SENTINEL", encoding="utf-8")
    return targets


def test_setup_prompt_all_answers_remaining_files(tmp_path):
    targets = _seed_two_skills(tmp_path)
    # A single "a" covers both files: a second prompt would hit EOF and skip.
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path)], input="a\n"
    )
    assert result.exit_code == 0, result.output
    for target in targets:
        assert "SENTINEL" not in target.read_text(encoding="utf-8")


def test_setup_prompt_quit_keeps_remaining_files(tmp_path):
    targets = _seed_two_skills(tmp_path)
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path)], input="q\n"
    )
    assert result.exit_code == 0, result.output
    for target in targets:
        assert target.read_text(encoding="utf-8") == "SENTINEL"


def test_setup_identical_content_is_not_prompted(tmp_path):
    CliRunner().invoke(cli, ["setup", "skills", "--dest", str(tmp_path)])
    # Nothing changed on disk, so the rerun has nothing to ask about.
    result = CliRunner().invoke(cli, ["setup", "skills", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "same" in result.stderr
    assert "overwrite" not in result.stderr


def test_setup_yes_flag_overwrites_without_prompting(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(cli, ["setup", "skills", "--dest", str(tmp_path), "-y"])
    assert result.exit_code == 0, result.output
    assert "SENTINEL" not in target.read_text(encoding="utf-8")
    assert "overwrite" not in result.stderr


def test_setup_skip_confirmation_env_keeps_existing(tmp_path, monkeypatch):
    """Unattended runs must keep files, not clobber them."""
    monkeypatch.setenv("DEVOPS_UTILS_SKIP_CONFIRMATION", "1")
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path)], input="y\n"
    )
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == "SENTINEL"


def test_setup_all_shares_one_answer_across_steps(tmp_path):
    CliRunner().invoke(cli, ["setup", "all", "--dest", str(tmp_path), "--force"])
    skill = tmp_path / "azure-devops.md"
    agent = tmp_path / "agents" / "azdo-build-analyst.md"
    env = tmp_path / ".env.devops-utils.example"
    for target in (skill, agent, env):
        target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "all", "--dest", str(tmp_path)], input="a\n"
    )
    assert result.exit_code == 0, result.output
    for target in (skill, agent, env):
        assert "SENTINEL" not in target.read_text(encoding="utf-8")


def test_setup_mcp_prompt_declined_keeps_entry(tmp_path):
    cfg = tmp_path / ".mcp.json"
    CliRunner().invoke(cli, ["setup", "mcp", "--dest", str(tmp_path), "--no-uvx"])
    result = CliRunner().invoke(
        cli, ["setup", "mcp", "--dest", str(tmp_path)], input="n\n"
    )
    assert result.exit_code == 0, result.output
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["devops-utils"]["command"] == "devops-utils-mcp"


def test_setup_mcp_prompt_accepted_replaces_entry_and_keeps_siblings(tmp_path):
    cfg = tmp_path / ".mcp.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"other": {"command": "keep-me"}}}),
        encoding="utf-8",
    )
    CliRunner().invoke(cli, ["setup", "mcp", "--dest", str(tmp_path), "--no-uvx"])
    result = CliRunner().invoke(
        cli, ["setup", "mcp", "--dest", str(tmp_path)], input="y\n"
    )
    assert result.exit_code == 0, result.output
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["devops-utils"]["command"] == "uvx"
    assert data["mcpServers"]["other"]["command"] == "keep-me"


def test_setup_force_overwrites(tmp_path):
    target = tmp_path / "azure-devops.md"
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["setup", "skills", "--dest", str(tmp_path), "--force"]
    )
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") != "SENTINEL"


AGENT_NAMES = ("azdo-workitem-analyst", "azdo-build-analyst", "azdo-repo-analyst")


def test_bundled_agents_are_discoverable():
    names = {name for name, _filename, _text in install.iter_bundled_agents()}
    assert set(AGENT_NAMES) <= names


def test_bundled_agents_are_read_only():
    write_markers = ("create_work_item", "update_work_item", "comment", "tag_build")
    for _name, _filename, text in install.iter_bundled_agents():
        tools_line = next(
            line for line in text.splitlines() if line.startswith("tools:")
        )
        for marker in write_markers:
            assert marker not in tools_line


def test_setup_agents_installs_md_files(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "agents", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    for name in AGENT_NAMES:
        target = tmp_path / "agents" / f"{name}.md"
        assert target.exists()
        assert f"name: {name}" in target.read_text(encoding="utf-8")


def test_setup_agents_skips_existing_without_force(tmp_path):
    target = tmp_path / "agents" / "azdo-build-analyst.md"
    target.parent.mkdir(parents=True)
    target.write_text("SENTINEL", encoding="utf-8")
    result = CliRunner().invoke(cli, ["setup", "agents", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == "SENTINEL"
    assert "skip" in result.output
    result = CliRunner().invoke(
        cli, ["setup", "agents", "--dest", str(tmp_path), "--force"]
    )
    assert result.exit_code == 0, result.output
    assert "SENTINEL" not in target.read_text(encoding="utf-8")


def test_install_tracker_renders_placeholders(tmp_path):
    written, skipped = install.install_tracker(tmp_path, "Contoso", done_state="Done")
    assert skipped == []
    tracker = tmp_path / "docs" / "agents" / "issue-tracker.md"
    labels = tmp_path / "docs" / "agents" / "triage-labels.md"
    assert {tracker, labels} == set(written)
    text = tracker.read_text(encoding="utf-8")
    assert "--project Contoso" in text
    assert '--state "Done"' in text
    assert "{project}" not in text
    assert "{done_state}" not in text
    # unset defaults render readable fallbacks, never raw placeholders
    assert "{org_url}" not in text
    assert "{parent_epic}" not in text
    assert "{area_path}" not in text
    assert "{default_tags}" not in text
    assert "{create_flags}" not in text
    assert "{query_flags}" not in text
    assert "AZURE_DEVOPS_ORG_URL" in text
    assert "(none)" in text
    assert "ready-for-agent" in labels.read_text(encoding="utf-8")


def test_install_tracker_renders_defaults(tmp_path):
    install.install_tracker(
        tmp_path,
        "Contoso",
        done_state="Done",
        org_url="https://dev.azure.com/contoso",
        parent_epic=1400,
        area_path="Contoso\\Payments",
        default_tags=["web-app", "backend"],
    )
    text = (tmp_path / "docs" / "agents" / "issue-tracker.md").read_text(
        encoding="utf-8"
    )
    assert "https://dev.azure.com/contoso" in text
    assert "#1400" in text
    assert "--parent 1400" in text
    assert "--area-path 'Contoso\\Payments'" in text
    assert "--tag 'web-app' --tag 'backend'" in text
    assert "web-app, backend" in text


def test_install_tracker_skips_existing_without_force(tmp_path):
    target = tmp_path / "docs" / "agents" / "issue-tracker.md"
    target.parent.mkdir(parents=True)
    target.write_text("SENTINEL", encoding="utf-8")
    written, skipped = install.install_tracker(tmp_path, "Contoso")
    assert target in skipped
    assert target.read_text(encoding="utf-8") == "SENTINEL"
    written, skipped = install.install_tracker(tmp_path, "Contoso", force=True)
    assert target in written
    assert "SENTINEL" not in target.read_text(encoding="utf-8")


def test_setup_tracker_cli(tmp_path):
    result = CliRunner().invoke(
        cli,
        [
            "setup",
            "tracker",
            "--project-name",
            "Contoso",
            "--done-state",
            "Resolved",
            "--org-url",
            "https://dev.azure.com/contoso",
            "--parent-epic",
            "1400",
            "--area-path",
            "Contoso\\Payments",
            "--default-tag",
            "web-app",
            "--dest",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    text = (tmp_path / "docs" / "agents" / "issue-tracker.md").read_text(
        encoding="utf-8"
    )
    assert "azdo create --project Contoso" in text
    assert 'update <id> --state "Resolved"' in text
    assert "https://dev.azure.com/contoso" in text
    assert "--parent 1400" in text
    assert "--area-path 'Contoso\\Payments'" in text
    assert "--tag 'web-app'" in text


def test_setup_all_skips_mcp_by_default(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "all", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "azure-devops.md").exists()
    assert (tmp_path / "azure-devops-research.md").exists()
    assert (tmp_path / "agents" / "azdo-build-analyst.md").exists()
    assert (tmp_path / ".env.devops-utils.example").exists()
    # MCP registration is opt-in — nothing is written without --with-mcp.
    assert not (tmp_path / ".mcp.json").exists()
    assert "--with-mcp" in result.output


def test_setup_all_with_mcp_registers_uvx_server(tmp_path):
    result = CliRunner().invoke(
        cli, ["setup", "all", "--dest", str(tmp_path), "--with-mcp"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    assert data["mcpServers"]["devops-utils"]["command"] == "uvx"
