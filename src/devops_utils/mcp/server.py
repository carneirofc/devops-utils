"""MCP server exposing devops-utils core tools.

Requires the ``mcp`` optional dependency: ``pip install devops-utils[mcp]``.
The import of :mod:`mcp` is deferred so that importing the package never pulls
in the MCP SDK when the extra is not installed.
"""

import functools
import inspect
import os
from typing import Any, Callable

import yaml

from devops_utils.agent import tools as agent_tools
from devops_utils.core.sanitizer import sanitize as _sanitize

# Environment variable that, when truthy, lets work-item writes proceed without
# a human confirmation prompt (for deliberate, unattended automation).
_SKIP_CONFIRMATION_ENV = "DEVOPS_UTILS_SKIP_CONFIRMATION"

# Work-item write tools gated behind a human confirmation (elicitation) prompt.
# Kept as an explicit, auditable set separate from read/non-work-item tools.
WORK_ITEM_WRITE_TOOLS = (
    agent_tools.azdo_create_work_item,
    agent_tools.azdo_comment_work_item,
    agent_tools.azdo_set_work_item_tags,
    agent_tools.azdo_update_work_item,
    agent_tools.azdo_add_work_item_link,
    agent_tools.azdo_remove_work_item_link,
    agent_tools.azdo_add_work_item_attachment,
)


_confirm_schema_cache: type | None = None


def _confirm_schema() -> type:
    """Return (and cache) the Pydantic model used as the elicitation schema.

    Confirmation is driven by the elicitation ``action`` (accept/decline/cancel);
    the optional ``note`` lets a human record why they approved or rejected. Built
    lazily so importing this module never requires pydantic (an mcp-extra dep).
    """
    global _confirm_schema_cache
    if _confirm_schema_cache is None:
        from pydantic import BaseModel

        class _Confirm(BaseModel):
            note: str | None = None

        _confirm_schema_cache = _Confirm
    return _confirm_schema_cache


def _skip_confirmation() -> bool:
    """Whether work-item write confirmation is bypassed via env var."""
    return os.environ.get(_SKIP_CONFIRMATION_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _preview(fn: Callable[..., Any], kwargs: dict[str, Any]) -> str:
    """Build a compact, human-readable description of a pending write call."""
    args = ", ".join(f"{key}={value!r}" for key, value in kwargs.items())
    return f"{fn.__name__}({args})"


def _confirm_write(fn: Callable[..., Any], ctx_type: type) -> Callable[..., Any]:
    """Wrap a work-item write callable so a human approves it before it runs.

    The returned async tool preserves ``fn``'s name, docstring, and parameters
    (so the MCP input schema is unchanged) and injects a keyword-only ``ctx``
    parameter annotated with ``ctx_type`` (FastMCP's ``Context``). FastMCP detects
    the context by its annotation and hides it from the tool's input schema.

    Before executing, the wrapper elicits a confirmation from the client:

    - ``accept`` → run ``fn`` and return its result.
    - ``decline`` / ``cancel`` → return a ``cancelled`` status without running.
    - elicitation unavailable (client can't prompt / non-interactive) → fail
      **closed** and return a ``blocked`` status, unless
      ``DEVOPS_UTILS_SKIP_CONFIRMATION`` is truthy, in which case run ``fn``.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = kwargs.pop("ctx")
        call_kwargs = dict(zip(inspect.signature(fn).parameters, args))
        call_kwargs.update(kwargs)

        message = (
            f"About to write to Azure DevOps: {_preview(fn, call_kwargs)}\n"
            "Apply this change?"
        )
        try:
            result = await ctx.elicit(message=message, schema=_confirm_schema())
        except Exception:
            if _skip_confirmation():
                return fn(**call_kwargs)
            return {
                "status": "blocked",
                "tool": fn.__name__,
                "message": (
                    "Human confirmation required but unavailable; set "
                    f"{_SKIP_CONFIRMATION_ENV}=1 to allow unattended writes."
                ),
            }

        if result.action == "accept":
            return fn(**call_kwargs)
        return {
            "status": "cancelled",
            "tool": fn.__name__,
            "message": "Change not applied — declined by human.",
        }

    # Rebuild the public signature as fn's params plus an injected, keyword-only
    # ``ctx`` so FastMCP builds the same input schema and supplies the Context.
    # FastMCP finds the context param via ``get_type_hints`` (i.e. __annotations__),
    # so ``ctx`` must be added there too — as a fresh dict, since ``functools.wraps``
    # aliases ``fn``'s annotations and mutating it would corrupt the original tool.
    fn_sig = inspect.signature(fn)
    ctx_param = inspect.Parameter(
        "ctx", inspect.Parameter.KEYWORD_ONLY, annotation=ctx_type
    )
    wrapper.__signature__ = fn_sig.replace(  # type: ignore[attr-defined]
        parameters=[*fn_sig.parameters.values(), ctx_param]
    )
    wrapper.__annotations__ = {**fn.__annotations__, "ctx": ctx_type}
    return wrapper


def _build_server():
    try:
        from mcp.server.fastmcp import Context, FastMCP
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise SystemExit(
            "The MCP server requires the 'mcp' extra. "
            "Install it with: pip install devops-utils[mcp]"
        ) from exc

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

    # Azure DevOps tools. Registered from the framework-agnostic agent wrappers so
    # the logic (and docstrings the LLM reads) live in one place. Config comes
    # from AZURE_DEVOPS_ORG_URL / AZURE_DEVOPS_TOKEN env vars.
    #
    # Read tools and non-work-item writes (build tags, PR comments) register
    # directly. Work-item write tools are wrapped with an elicitation gate so a
    # human confirms each mutation before it reaches Azure DevOps.
    for fn in (
        agent_tools.azdo_list_repositories,
        agent_tools.azdo_list_work_items,
        agent_tools.azdo_search_work_items,
        agent_tools.azdo_get_work_item,
        agent_tools.azdo_list_builds,
        agent_tools.azdo_get_build,
        agent_tools.azdo_tag_build,
        agent_tools.azdo_comment_pull_request,
    ):
        server.tool()(fn)

    for fn in WORK_ITEM_WRITE_TOOLS:
        server.tool()(_confirm_write(fn, Context))

    return server


def main() -> None:
    """Entry point for the ``devops-utils-mcp`` console script (stdio transport)."""
    _build_server().run()


if __name__ == "__main__":
    main()
