"""MCP server exposing devops-utils core tools.

Requires the ``mcp`` optional dependency: ``pip install devops-utils[mcp]``.
The import of :mod:`mcp` is deferred so that importing the package never pulls
in the MCP SDK when the extra is not installed.
"""

import yaml

from devops_utils.core.sanitizer import sanitize as _sanitize


def _build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise SystemExit(
            "The MCP server requires the 'mcp' extra. "
            "Install it with: pip install devops-utils[mcp]"
        ) from exc

    from devops_utils.agent import tools as agent_tools

    server = FastMCP("devops-utils")

    @server.tool()
    def sanitize_manifest(manifest: str) -> str:
        """Mask Secret values in a Kubernetes YAML manifest.

        Args:
            manifest: One or more Kubernetes YAML documents as a string.

        Returns:
            The manifest with every Secret's ``data``/``stringData`` values masked.
        """
        sanitized = _sanitize(manifest)
        return yaml.dump_all(sanitized, default_flow_style=False)

    # Azure DevOps work-item tools. Registered from the framework-agnostic agent
    # wrappers so the logic (and docstrings the LLM reads) live in one place.
    # Config comes from AZURE_DEVOPS_ORG_URL / AZURE_DEVOPS_TOKEN env vars.
    for fn in (
        agent_tools.azdo_list_repositories,
        agent_tools.azdo_list_work_items,
        agent_tools.azdo_search_work_items,
        agent_tools.azdo_get_work_item,
        agent_tools.azdo_create_work_item,
        agent_tools.azdo_comment_work_item,
        agent_tools.azdo_set_work_item_tags,
        agent_tools.azdo_update_work_item,
        agent_tools.azdo_add_work_item_link,
        agent_tools.azdo_remove_work_item_link,
        agent_tools.azdo_add_work_item_attachment,
    ):
        server.tool()(fn)

    return server


def main() -> None:
    """Entry point for the ``devops-utils-mcp`` console script (stdio transport)."""
    _build_server().run()


if __name__ == "__main__":
    main()
