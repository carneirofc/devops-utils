"""Tests for the MCP work-item write confirmation gate (human-in-the-loop).

The gate wraps each work-item write tool so a human approves the mutation via MCP
elicitation before it reaches Azure DevOps. These tests exercise the wrapper with
a scripted stub ``ctx`` (no live client) and assert the registration split.
"""

import asyncio
import inspect

import pytest

from devops_utils.agent import tools as agent_tools
from devops_utils.mcp import server


class _Result:
    """Stand-in for an ElicitationResult (only ``action`` is inspected)."""

    def __init__(self, action: str) -> None:
        self.action = action
        self.data = None


class _Ctx:
    """Stub Context whose ``elicit`` is scripted per test."""

    def __init__(self, action: str | None = None, raises: bool = False) -> None:
        self._action = action
        self._raises = raises
        self.elicited: list[str] = []

    async def elicit(self, message, schema):
        self.elicited.append(message)
        assert schema is server._confirm_schema()
        if self._raises:
            raise RuntimeError("client does not support elicitation")
        return _Result(self._action)


def _spy():
    """A fake work-item write callable recording its calls."""
    calls: list[tuple] = []

    def fake_write(work_item_id: int, text: str):
        calls.append((work_item_id, text))
        return {"id": work_item_id, "text": text}

    return fake_write, calls


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# gate behaviour
# --------------------------------------------------------------------------- #
def test_accept_runs_underlying_tool_with_exact_args():
    fn, calls = _spy()
    gated = server._confirm_write(fn, object)
    result = _run(gated(work_item_id=7, text="hi", ctx=_Ctx("accept")))
    assert calls == [(7, "hi")]
    assert result == {"id": 7, "text": "hi"}


def test_accept_passes_positional_args_through():
    fn, calls = _spy()
    gated = server._confirm_write(fn, object)
    _run(gated(7, "hi", ctx=_Ctx("accept")))
    assert calls == [(7, "hi")]


@pytest.mark.parametrize("action", ["decline", "cancel"])
def test_decline_or_cancel_does_not_run_and_reports_cancelled(action):
    fn, calls = _spy()
    gated = server._confirm_write(fn, object)
    result = _run(gated(work_item_id=7, text="hi", ctx=_Ctx(action)))
    assert calls == []
    assert result["status"] == "cancelled"
    assert result["tool"] == "fake_write"


def test_elicitation_unavailable_with_skip_env_runs(monkeypatch):
    monkeypatch.setenv("DEVOPS_UTILS_SKIP_CONFIRMATION", "1")
    fn, calls = _spy()
    gated = server._confirm_write(fn, object)
    result = _run(gated(work_item_id=7, text="hi", ctx=_Ctx(raises=True)))
    assert calls == [(7, "hi")]
    assert result == {"id": 7, "text": "hi"}


def test_elicitation_unavailable_without_env_blocks(monkeypatch):
    monkeypatch.delenv("DEVOPS_UTILS_SKIP_CONFIRMATION", raising=False)
    fn, calls = _spy()
    gated = server._confirm_write(fn, object)
    result = _run(gated(work_item_id=7, text="hi", ctx=_Ctx(raises=True)))
    assert calls == []
    assert result["status"] == "blocked"
    assert "DEVOPS_UTILS_SKIP_CONFIRMATION" in result["message"]


# --------------------------------------------------------------------------- #
# signature / schema preservation
# --------------------------------------------------------------------------- #
def test_wrapper_preserves_name_and_doc():
    gated = server._confirm_write(agent_tools.azdo_comment_work_item, object)
    assert gated.__name__ == "azdo_comment_work_item"
    assert gated.__doc__ == agent_tools.azdo_comment_work_item.__doc__


def test_wrapper_injects_ctx_param_without_disturbing_others():
    sentinel = type("Ctx", (), {})
    gated = server._confirm_write(agent_tools.azdo_comment_work_item, sentinel)
    params = inspect.signature(gated).parameters
    assert "ctx" in params
    assert params["ctx"].annotation is sentinel
    # original params are still present and precede ctx
    assert "work_item_id" in params and "text" in params
    # ctx must not leak into the original tool's annotations
    assert "ctx" not in agent_tools.azdo_comment_work_item.__annotations__


# --------------------------------------------------------------------------- #
# env-var helper
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("On", True),
        ("0", False),
        ("no", False),
        ("", False),
    ],
)
def test_skip_confirmation_matrix(monkeypatch, value, expected):
    monkeypatch.setenv("DEVOPS_UTILS_SKIP_CONFIRMATION", value)
    assert server._skip_confirmation() is expected


def test_skip_confirmation_unset_is_false(monkeypatch):
    monkeypatch.delenv("DEVOPS_UTILS_SKIP_CONFIRMATION", raising=False)
    assert server._skip_confirmation() is False


# --------------------------------------------------------------------------- #
# registration split
# --------------------------------------------------------------------------- #
def test_gated_set_is_exactly_the_work_item_writers():
    assert set(server.WORK_ITEM_WRITE_TOOLS) == {
        agent_tools.azdo_create_work_item,
        agent_tools.azdo_comment_work_item,
        agent_tools.azdo_set_work_item_tags,
        agent_tools.azdo_update_work_item,
        agent_tools.azdo_add_work_item_link,
        agent_tools.azdo_remove_work_item_link,
        agent_tools.azdo_add_work_item_attachment,
    }
    # non-work-item writes are deliberately NOT gated
    assert agent_tools.azdo_tag_build not in server.WORK_ITEM_WRITE_TOOLS
    assert agent_tools.azdo_comment_pull_request not in server.WORK_ITEM_WRITE_TOOLS


def test_server_registers_gated_tools_async_with_context_and_clean_schema():
    pytest.importorskip("mcp")
    srv = server._build_server()
    tools = _run(srv.list_tools())
    by_name = {t.name: t for t in tools}

    # a gated write: async, gets a Context, and 'ctx' is hidden from the schema
    tool = srv._tool_manager.get_tool("azdo_comment_work_item")
    assert tool.is_async
    assert tool.context_kwarg == "ctx"
    assert "ctx" not in by_name["azdo_comment_work_item"].inputSchema["properties"]
    assert set(by_name["azdo_comment_work_item"].inputSchema["properties"]) == {
        "work_item_id",
        "text",
    }

    # a read tool stays a plain sync tool with no injected context
    read = srv._tool_manager.get_tool("azdo_get_work_item")
    assert read.context_kwarg is None
