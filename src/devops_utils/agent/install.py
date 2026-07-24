"""Install bundled skills and wire the MCP server into an agent's config.

Framework-agnostic helpers used by the ``devops-utils setup`` CLI. Kept out of
the Click layer so the copy/merge logic stays importable and testable on its own
(mirrors how :mod:`devops_utils.agent.tools` stays free of any framework import).

The bundled skill markdown lives at ``devops_utils/agent/skills/*.md`` and is
read through :mod:`importlib.resources`, so it resolves the same way from a
source checkout and from an installed wheel.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

#: Name under which the MCP server is registered in an agent's config.
MCP_SERVER_NAME = "devops-utils"

#: Console script that launches the stdio MCP server (see ``[project.scripts]``).
MCP_COMMAND = "devops-utils-mcp"

#: Claude Code plugin name. The harness namespaces a plugin's skills/agents as
#: ``<plugin-name>:<component>``, so with this name the bundled skills/agents list
#: as ``devops-utils:azure-devops-research``, ``devops-utils:azdo-workitem-analyst``,
#: etc. — distinguishable at a glance from unrelated skills/agents.
PLUGIN_NAME = "devops-utils"

#: Marketplace name users add before installing the plugin
#: (``/plugin install devops-utils@<MARKETPLACE_NAME>``).
MARKETPLACE_NAME = "carneirofc"


def _skills_resource():
    """Return the ``importlib.resources`` traversable for the skills package."""
    return files("devops_utils.agent.skills")


def _skill_name(text: str, fallback: str) -> str:
    """Extract the ``name:`` field from a skill's YAML frontmatter.

    Args:
        text: Full markdown text of the skill (may start with a ``---`` block).
        fallback: Name to use when no frontmatter ``name:`` is present.

    Returns:
        The frontmatter ``name`` value, or ``fallback``.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fallback
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            value = stripped[len("name:") :].strip().strip("\"'")
            if value:
                return value
    return fallback


def iter_bundled_skills() -> list[tuple[str, str, str]]:
    """List the skills bundled with the package.

    Returns:
        A list of ``(skill_name, filename, text)`` tuples, sorted by filename.
        ``skill_name`` comes from the frontmatter ``name:`` (falling back to the
        file stem); ``filename`` is the original ``*.md`` file name.
    """
    skills: list[tuple[str, str, str]] = []
    for entry in _skills_resource().iterdir():
        if not entry.name.endswith(".md"):
            continue
        text = entry.read_text(encoding="utf-8")
        stem = entry.name[: -len(".md")]
        skills.append((_skill_name(text, stem), entry.name, text))
    return sorted(skills, key=lambda s: s[1])


def _write(path: Path, text: str, force: bool) -> Path | None:
    """Write ``text`` to ``path``, returning the path or ``None`` if skipped."""
    if path.exists() and not force:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def install_skills(
    dest: Path, layout: str = "claude", force: bool = False
) -> tuple[list[Path], list[Path]]:
    """Copy the bundled skills into ``dest``.

    Args:
        dest: Base directory to install into.
        layout: ``"claude"`` writes ``dest/skills/<name>/SKILL.md`` (Claude Code
            discovery layout); ``"flat"`` writes ``dest/<filename>``.
        force: Overwrite existing files instead of skipping them.

    Returns:
        A ``(written, skipped)`` tuple of destination paths.
    """
    if layout not in ("claude", "flat"):
        raise ValueError(f"unknown layout: {layout!r}")

    written: list[Path] = []
    skipped: list[Path] = []
    for name, filename, text in iter_bundled_skills():
        if layout == "claude":
            target = dest / "skills" / name / "SKILL.md"
        else:
            target = dest / filename
        result = _write(target, text, force)
        (written if result is not None else skipped).append(target)
    return written, skipped


def _agents_resource():
    """Return the ``importlib.resources`` traversable for the agents package."""
    return files("devops_utils.agent.agents")


def iter_bundled_agents() -> list[tuple[str, str, str]]:
    """List the Claude Code agent files bundled with the package.

    Returns:
        A list of ``(agent_name, filename, text)`` tuples, sorted by filename.
        ``agent_name`` comes from the frontmatter ``name:`` (falling back to
        the file stem).
    """
    agents: list[tuple[str, str, str]] = []
    for entry in _agents_resource().iterdir():
        if not entry.name.endswith(".md"):
            continue
        text = entry.read_text(encoding="utf-8")
        stem = entry.name[: -len(".md")]
        agents.append((_skill_name(text, stem), entry.name, text))
    return sorted(agents, key=lambda a: a[1])


def install_agents(dest: Path, force: bool = False) -> tuple[list[Path], list[Path]]:
    """Copy the bundled Claude Code agents into ``dest/agents/<name>.md``.

    Claude Code discovers subagents as single ``.md`` files in an ``agents/``
    directory (user scope ``~/.claude/agents``, project scope ``.claude/agents``).

    Args:
        dest: Base directory to install into (e.g. ``~/.claude``).
        force: Overwrite existing files instead of skipping them.

    Returns:
        A ``(written, skipped)`` tuple of destination paths.
    """
    written: list[Path] = []
    skipped: list[Path] = []
    for name, _filename, text in iter_bundled_agents():
        target = dest / "agents" / f"{name}.md"
        result = _write(target, text, force)
        (written if result is not None else skipped).append(target)
    return written, skipped


def _trackers_resource():
    """Return the ``importlib.resources`` traversable for the tracker templates."""
    return files("devops_utils.agent.trackers")


def install_tracker(
    dest: Path,
    project_name: str,
    done_state: str = "Closed",
    force: bool = False,
) -> tuple[list[Path], list[Path]]:
    """Write the Azure DevOps tracker config for mattpocock-style skills.

    Renders the bundled templates (``agent/trackers/*.md``) into
    ``dest/docs/agents/``, substituting the ``{project}`` and ``{done_state}``
    placeholders. The resulting ``issue-tracker.md`` / ``triage-labels.md`` are
    the config files skills like mattpocock/skills read to learn how to talk to
    the issue tracker.

    Args:
        dest: Repository root to install into (files go to ``docs/agents/``).
        project_name: Azure DevOps team project name.
        done_state: ``System.State`` value that means "closed" in the project's
            process template (e.g. ``Closed``, ``Done``, ``Resolved``).
        force: Overwrite existing files instead of skipping them.

    Returns:
        A ``(written, skipped)`` tuple of destination paths.
    """
    written: list[Path] = []
    skipped: list[Path] = []
    for entry in sorted(_trackers_resource().iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(".md"):
            continue
        text = (
            entry.read_text(encoding="utf-8")
            .replace("{project}", project_name)
            .replace("{done_state}", done_state)
        )
        target = dest / "docs" / "agents" / entry.name
        result = _write(target, text, force)
        (written if result is not None else skipped).append(target)
    return written, skipped


def mcp_server_entry() -> dict[str, object]:
    """Return the MCP ``mcpServers`` entry for the stdio server."""
    return {"command": MCP_COMMAND, "args": [], "env": {}}


def merge_mcp_config(
    path: Path, name: str = MCP_SERVER_NAME, force: bool = False
) -> tuple[Path, bool]:
    """Register the MCP server in a JSON config, preserving other servers.

    Loads ``path`` if it exists, sets ``mcpServers[name]`` to
    :func:`mcp_server_entry` without touching sibling servers, and writes it back
    pretty-printed. Works for both ``~/.claude.json`` (user) and ``.mcp.json``
    (project).

    Args:
        path: Path to the JSON config file (created if missing).
        name: Server key to register under.
        force: Overwrite an existing entry for ``name``. When ``False`` and the
            entry already exists, the file is left unchanged.

    Returns:
        A ``(path, changed)`` tuple. ``changed`` is ``False`` when an entry for
        ``name`` already existed and ``force`` was not set.
    """
    data: dict[str, object] = {}
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8") or "{}")
        if isinstance(loaded, dict):
            data = loaded

    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    if name in servers and not force:
        return path, False

    servers[name] = mcp_server_entry()
    data["mcpServers"] = servers
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path, True


def env_template() -> str:
    """Return an ``.env`` scaffold for the Azure DevOps credentials."""
    return (
        "# Azure DevOps configuration for devops-utils (azdo tools / MCP).\n"
        "# No machine credentials are read; only these env vars are used.\n"
        "\n"
        "# Cloud: https://dev.azure.com/{org} | on-prem: https://server/tfs/{collection}\n"
        "AZURE_DEVOPS_ORG_URL=\n"
        "# Bearer token or PAT.\n"
        "AZURE_DEVOPS_TOKEN=\n"
        "# 'bearer' (default) or 'pat'.\n"
        "AZURE_DEVOPS_AUTH_SCHEME=bearer\n"
        "# Default 7.1; lower it for older on-prem servers.\n"
        "AZURE_DEVOPS_API_VERSION=7.1\n"
    )


def write_env_scaffold(path: Path, force: bool = False) -> Path | None:
    """Write the env scaffold to ``path`` (skipped if it exists and not ``force``)."""
    return _write(path, env_template(), force)


def plugin_manifest() -> dict[str, object]:
    """Return the ``.claude-plugin/plugin.json`` contents for the bundled plugin.

    The plugin name drives Claude Code's namespacing: skills and agents shipped
    under it list as ``devops-utils:<component>`` (see :data:`PLUGIN_NAME`). The
    MCP server is intentionally *not* declared here — a plugin-bundled MCP server
    is re-scoped to ``mcp__plugin_<plugin>_<server>__<tool>``, which would break
    the agents' ``tools:`` frontmatter that targets ``mcp__devops-utils__azdo_*``.
    MCP stays wired via :func:`merge_mcp_config` / ``setup mcp`` instead.

    ``version`` is deliberately omitted (it is optional): the package uses VCS-derived
    versioning, so a value here would change on every commit and make the committed
    manifest churn and drift from a regeneration.
    """
    return {
        "name": PLUGIN_NAME,
        "description": (
            "Read-only Azure DevOps skills and subagents for work-item, build, "
            "and repository research (cloud + on-prem)."
        ),
        "author": {
            "name": "Cláudio Ferreira Carneiro",
            "email": "claudiofcarneiro@gmail.com",
        },
        "homepage": "https://carneirofc.github.io/devops-utils/",
        "repository": "https://github.com/carneirofc/devops-utils",
        "license": "MIT",
        "keywords": ["azure-devops", "devops", "work-items", "mcp"],
    }


def marketplace_manifest() -> dict[str, object]:
    """Return the ``.claude-plugin/marketplace.json`` contents for the repo.

    Declares a single-plugin marketplace whose ``source`` is the relative path
    ``./plugins/devops-utils`` (Claude Code resolves it from the marketplace root,
    i.e. the repo root). Users install with::

        /plugin marketplace add carneirofc/devops-utils
        /plugin install devops-utils@carneirofc
    """
    return {
        "name": MARKETPLACE_NAME,
        "owner": {
            "name": "Cláudio Ferreira Carneiro",
            "email": "claudiofcarneiro@gmail.com",
        },
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": f"./plugins/{PLUGIN_NAME}",
                "description": (
                    "Read-only Azure DevOps skills and subagents "
                    "(work items, builds, repositories)."
                ),
            }
        ],
    }


def _write_json(path: Path, data: dict[str, object], force: bool) -> Path | None:
    """Write ``data`` as pretty UTF-8 JSON (skipped if it exists sans ``force``)."""
    return _write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", force)


def install_plugin(
    repo_root: Path, force: bool = False
) -> tuple[list[Path], list[Path]]:
    """Generate the Claude Code plugin + marketplace tree under ``repo_root``.

    Lays the bundled skills/agents out where Claude Code discovers them for a
    plugin named :data:`PLUGIN_NAME`, and writes the two manifests:

    - ``repo_root/plugins/devops-utils/skills/<name>/SKILL.md`` (via
      :func:`install_skills` with the ``"claude"`` layout)
    - ``repo_root/plugins/devops-utils/agents/<name>.md`` (via
      :func:`install_agents`)
    - ``repo_root/plugins/devops-utils/.claude-plugin/plugin.json``
    - ``repo_root/.claude-plugin/marketplace.json``

    The skill/agent markdown is copied byte-for-byte from the bundled sources;
    the ``<plugin>:<name>`` namespace is derived by Claude Code from this layout,
    so no frontmatter rewriting is needed.

    Args:
        repo_root: Repository root to generate the plugin tree into.
        force: Overwrite existing files instead of skipping them.

    Returns:
        A ``(written, skipped)`` tuple of destination paths.
    """
    plugin_root = repo_root / "plugins" / PLUGIN_NAME

    written: list[Path] = []
    skipped: list[Path] = []
    for install in (install_skills, install_agents):
        w, s = install(plugin_root, force=force)
        written.extend(w)
        skipped.extend(s)

    for path, data in (
        (plugin_root / ".claude-plugin" / "plugin.json", plugin_manifest()),
        (repo_root / ".claude-plugin" / "marketplace.json", marketplace_manifest()),
    ):
        result = _write_json(path, data, force)
        (written if result is not None else skipped).append(path)

    return written, skipped
