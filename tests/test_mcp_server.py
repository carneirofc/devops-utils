import asyncio

import pytest

pytest.importorskip("mcp")

from devops_utils.mcp.server import _build_server  # noqa: E402


def test_mcp_server_registers_all_tools():
    server = _build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "sanitize_manifest" in names
    assert "azdo_create_work_item" in names
    assert "azdo_comment_pull_request" in names
    assert len(names) == 16
