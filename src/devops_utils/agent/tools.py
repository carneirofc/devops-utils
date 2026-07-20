"""Thin, framework-agnostic agent-tool wrappers over the core logic.

These are plain callables with clear signatures and docstrings so they can be
registered with any agent framework (or the MCP server) without importing it.
"""

import yaml

from devops_utils.core.sanitizer import sanitize as _sanitize


def sanitize_manifest(manifest: str) -> str:
    """Mask Secret values in a Kubernetes YAML manifest.

    Args:
        manifest: One or more Kubernetes YAML documents as a string.

    Returns:
        The manifest with every Secret's ``data``/``stringData`` values masked.
    """
    sanitized = _sanitize(manifest)
    return yaml.dump_all(sanitized, default_flow_style=False)
