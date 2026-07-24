"""Tests for the Claude Code plugin generator and the committed plugin tree."""

import json
from pathlib import Path

from click.testing import CliRunner

from devops_utils.agent import install
from devops_utils.cli.main import cli

REPO_ROOT = Path(__file__).resolve().parent.parent

SKILL_DIRS = (
    "azure-devops-work-items",
    "azure-devops-research",
    "sanitize-manifest",
)
AGENT_FILES = (
    "azdo-workitem-analyst.md",
    "azdo-build-analyst.md",
    "azdo-repo-analyst.md",
)


def test_plugin_manifest_names_the_plugin_devops_utils():
    manifest = install.plugin_manifest()
    assert manifest["name"] == "devops-utils"
    # Round-trips as JSON and carries no version (VCS-derived → intentionally absent).
    assert json.loads(json.dumps(manifest)) == manifest
    assert "version" not in manifest


def test_marketplace_manifest_points_at_the_plugin():
    manifest = install.marketplace_manifest()
    assert manifest["name"] == "carneirofc"
    (entry,) = manifest["plugins"]
    assert entry["name"] == "devops-utils"
    assert entry["source"] == "./plugins/devops-utils"


def test_install_plugin_lays_out_skills_agents_and_manifests(tmp_path):
    written, skipped = install.install_plugin(tmp_path)
    assert skipped == []
    plugin_root = tmp_path / "plugins" / "devops-utils"

    # Skills nest one dir deep (dir name == frontmatter name → namespaced component).
    for name in SKILL_DIRS:
        skill = plugin_root / "skills" / name / "SKILL.md"
        assert skill.exists()
        assert f"name: {name}" in skill.read_text(encoding="utf-8")

    # Agents stay flat .md files at the agents root (subdirs aren't valid for agents).
    for filename in AGENT_FILES:
        agent = plugin_root / "agents" / filename
        assert agent.exists()

    assert (plugin_root / ".claude-plugin" / "plugin.json").exists()
    assert (tmp_path / ".claude-plugin" / "marketplace.json").exists()
    # Every reported written path actually exists.
    assert all(p.exists() for p in written)


def test_setup_plugin_cli(tmp_path):
    result = CliRunner().invoke(cli, ["setup", "plugin", "--dest", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (
        tmp_path / "plugins" / "devops-utils" / ".claude-plugin" / "plugin.json"
    ).exists()
    assert (tmp_path / ".claude-plugin" / "marketplace.json").exists()


def test_committed_plugin_tree_matches_source(tmp_path):
    """The committed plugin tree must equal a fresh regeneration (drift guard).

    If a bundled skill/agent changes, `devops-utils setup plugin --force` must be
    re-run so the committed `plugins/devops-utils` + marketplace stay in sync.
    """
    install.install_plugin(tmp_path, force=True)

    committed = REPO_ROOT / "plugins" / "devops-utils"
    generated = tmp_path / "plugins" / "devops-utils"

    committed_files = {
        p.relative_to(committed) for p in committed.rglob("*") if p.is_file()
    }
    generated_files = {
        p.relative_to(generated) for p in generated.rglob("*") if p.is_file()
    }
    assert committed_files == generated_files, "plugin file set drifted from source"

    for rel in committed_files:
        assert (committed / rel).read_bytes() == (generated / rel).read_bytes(), (
            f"{rel} drifted; re-run `devops-utils setup plugin --force`"
        )

    assert (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_bytes() == (
        tmp_path / ".claude-plugin" / "marketplace.json"
    ).read_bytes()
