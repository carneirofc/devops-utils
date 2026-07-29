"""Make CLI output survive non-UTF-8 stdio (Windows ``cp1252`` in particular).

Work-item titles, previews, and this CLI's own messages contain non-ASCII
characters (``→``, ``—``). On Windows a *redirected* stdout defaults to the
ANSI code page (``cp1252``), where writing one of those raises
``UnicodeEncodeError`` and kills the command mid-write::

    UnicodeEncodeError: 'charmap' codec can't encode character '\\u2190'

:func:`configure_stdio` upgrades such streams to UTF-8 and, whatever the
encoding ends up being, switches the error handler to ``backslashreplace`` so
an unencodable character degrades to an escape sequence instead of an
exception.

It is called from every entry point — the ``devops-utils`` console script (from
its ``main`` wrapper, *before* Click parses argv, so eager options like
``--help`` are covered too), the root Click group (covering ``python -m`` and
embedded use), and the ``devops-utils-mcp`` server via :func:`configure_stderr`.
The point is that none of this depends on the caller exporting ``PYTHONUTF8`` /
``PYTHONIOENCODING`` first.

stdout is the stream that matters: CPython already defaults ``sys.stderr`` to
``backslashreplace``, so Click's own error output was never the crash path.

Note that ``chcp 65001`` was never part of the fix: since PEP 528 a process
attached to a *real* Windows console writes through ``WriteConsoleW`` whatever
the code page is. The crash only ever happened on a **redirected** stream,
which falls back to the ANSI code page.
"""

from __future__ import annotations

import sys
from typing import IO, Any

#: Error handler used for all CLI output: never raise, escape what can't be
#: encoded (``←``) so the text stays readable and diagnosable.
ERRORS = "backslashreplace"


def _is_utf8(encoding: str | None) -> bool:
    """Return True if ``encoding`` names UTF-8 (``utf-8``/``utf8``/``UTF_8``)."""
    if not encoding:
        return False
    return encoding.lower().replace("-", "").replace("_", "") == "utf8"


def _configure_stream(stream: IO[Any] | None) -> None:
    """Best-effort: give one text stream UTF-8 encoding and lenient errors.

    Streams without ``reconfigure`` (already-detached, or a non-text
    replacement installed by a host application) are left alone, as are streams
    that refuse the call — output robustness must never itself break the CLI.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    encoding = getattr(stream, "encoding", None)
    try:
        if _is_utf8(encoding):
            # Already UTF-8 (real Windows console, POSIX): only relax errors.
            reconfigure(errors=ERRORS)
        else:
            reconfigure(encoding="utf-8", errors=ERRORS)
    except (ValueError, OSError, AttributeError):
        # Detached/closed stream, or an exotic wrapper — keep the CLI running.
        pass


def configure_stdio() -> None:
    """Apply UTF-8 + ``backslashreplace`` to ``sys.stdout`` and ``sys.stderr``.

    Idempotent, so it is safe to call from more than one entry point.

    ``stdin`` is deliberately left alone: the only readers are ``click.confirm``
    and :func:`devops_utils.core.io.input_confirm`, both of which take ``y``/``n``.
    A future "read the description from stdin" feature should reconfigure at its
    own call site rather than globally.
    """
    _configure_stream(sys.stdout)
    _configure_stream(sys.stderr)


def configure_stderr() -> None:
    """Harden ``sys.stderr`` only — for hosts that own stdout.

    The MCP stdio transport frames JSON-RPC over stdout and stdin; those must
    stay byte-exact UTF-8, and ``backslashreplace`` at the *stream* layer would
    silently mangle a frame rather than let the serializer escape it. Its log
    channel is stderr, though, which is exposed to the same cp1252 crash as the
    CLI's.
    """
    _configure_stream(sys.stderr)
