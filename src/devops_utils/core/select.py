"""Project and render JSON-shaped results without a shell-side ``jq``.

The ``azdo`` CLI prints JSON; scripts used to pull values out with
``… | jq -r .id``, which is bash-flavoured and rarely installed on Windows.
These pure helpers let the CLI do that projection itself so one command line
works the same in bash, PowerShell, and ``cmd``:

- :func:`select` keeps only the requested paths. Paths are ``/``-separated so
  dotted Azure DevOps field names need no quoting:
  ``fields/Microsoft.VSTS.Scheduling.StartDate``.
- :func:`render` turns the (projected) result into text: pretty JSON, bare ids,
  or raw scalars.
"""

from __future__ import annotations

import json
from typing import Any

#: Output modes accepted by :func:`render`.
OUTPUT_MODES = ("json", "id", "raw")

_MISSING = object()


def _lookup(value: Any, path: str) -> Any:
    """Walk ``path`` (``/``-separated keys or list indexes) into ``value``."""
    current = value
    for part in path.split("/"):
        if isinstance(current, dict):
            current = current.get(part, _MISSING)
        elif isinstance(current, list) and part.lstrip("-").isdigit():
            index = int(part)
            current = (
                current[index] if -len(current) <= index < len(current) else _MISSING
            )
        else:
            current = _MISSING
        if current is _MISSING:
            return None
    return current


def _project(item: Any, paths: tuple[str, ...]) -> Any:
    if len(paths) == 1:
        return _lookup(item, paths[0])
    return {path.rsplit("/", 1)[-1]: _lookup(item, path) for path in paths}


def select(result: Any, paths: tuple[str, ...] | list[str]) -> Any:
    """Keep only ``paths`` from ``result``.

    One path yields the bare value; several yield an object keyed by each
    path's last segment. A list result is projected item by item. Missing paths
    come back as ``None`` rather than raising, so a sparse field doesn't abort a
    whole listing.
    """
    paths = tuple(paths)
    if not paths:
        return result
    if isinstance(result, list):
        return [_project(item, paths) for item in result]
    return _project(result, paths)


def _scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return json.dumps(value)
    return json.dumps(value, ensure_ascii=False)


def render(result: Any, mode: str = "json") -> str:
    """Render ``result`` as text for stdout.

    Args:
        result: JSON-shaped value (usually already passed through :func:`select`).
        mode: ``json`` — pretty JSON (the default, unchanged CLI behaviour);
            ``id`` — the ``id`` of each object, one per line, nothing else;
            ``raw`` — scalars unquoted, one list element per line, anything
            nested as compact JSON.
    """
    if mode == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)
    items = result if isinstance(result, list) else [result]
    if mode == "id":
        ids = [item.get("id") if isinstance(item, dict) else item for item in items]
        return "\n".join(_scalar_text(i) for i in ids)
    if mode == "raw":
        return "\n".join(_scalar_text(item) for item in items)
    raise ValueError(f"unknown output mode: {mode!r}")
