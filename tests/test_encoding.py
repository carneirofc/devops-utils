"""Tests for stdio encoding hardening (:mod:`devops_utils.core.encoding`).

Regression guard for ``UnicodeEncodeError: 'charmap' codec can't encode
character '\\u2190'`` — raised when a work-item title (or the CLI's own ``—``)
was echoed to a redirected Windows stdout, which defaults to ``cp1252``.

The point of these tests is that *no* caller-side preamble
(``chcp 65001`` / ``PYTHONUTF8`` / ``PYTHONIOENCODING``) is needed: the
subprocess cases deliberately run under a hostile ``PYTHONIOENCODING=cp1252``.
"""

import io
import json
import subprocess
import sys

import yaml

from devops_utils.core import encoding


def _wrapper(enc: str) -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding=enc, errors="strict")


def test_legacy_stream_is_upgraded_to_utf8():
    stream = _wrapper("cp1252")
    encoding._configure_stream(stream)
    assert stream.encoding.lower().replace("-", "") == "utf8"
    assert stream.errors == encoding.ERRORS
    stream.write("→ ← —")  # would raise UnicodeEncodeError before configuring


def test_utf8_stream_keeps_encoding_but_relaxes_errors():
    stream = _wrapper("utf-8")
    encoding._configure_stream(stream)
    assert stream.encoding.lower().replace("-", "") == "utf8"
    assert stream.errors == encoding.ERRORS


def test_unencodable_character_is_escaped_not_raised():
    """A stream that cannot be re-encoded still degrades instead of raising."""
    stream = _wrapper("ascii")
    # Simulate a stream that refuses an encoding change (console handles do).
    stream.reconfigure(errors=encoding.ERRORS)
    stream.write("←")
    stream.flush()
    assert stream.buffer.getvalue() == b"\\u2190"


def test_non_reconfigurable_stream_is_left_alone():
    encoding._configure_stream(io.StringIO())  # no reconfigure attr → no raise
    encoding._configure_stream(None)


def test_configure_stdio_leaves_stdin_alone(monkeypatch):
    seen = []
    monkeypatch.setattr(encoding, "_configure_stream", seen.append)
    encoding.configure_stdio()
    assert seen == [sys.stdout, sys.stderr]


def test_configure_stderr_touches_only_stderr(monkeypatch):
    seen = []
    monkeypatch.setattr(encoding, "_configure_stream", seen.append)
    encoding.configure_stderr()
    assert seen == [sys.stderr]


def test_configure_stdio_is_idempotent():
    """Called from both `main` and the group callback — must not raise twice."""
    encoding.configure_stdio()
    encoding.configure_stdio()


def test_cli_entry_point_configures_stdio_before_click_parses(monkeypatch):
    """`main` must configure stdio ahead of argv parsing, not in the callback."""
    from devops_utils.cli import main as cli_main

    order = []
    monkeypatch.setattr(cli_main, "configure_stdio", lambda: order.append("stdio"))
    monkeypatch.setattr(cli_main, "cli", lambda: order.append("cli"))
    cli_main.main()
    assert order == ["stdio", "cli"]


def test_mcp_server_hardens_stderr_only(monkeypatch):
    """stdout/stdin carry framed JSON-RPC the SDK owns — never reconfigure them.

    Pins the decision so nobody "helpfully" swaps in ``configure_stdio`` later:
    ``backslashreplace`` on a transport stream corrupts frames instead of
    letting the serializer escape them.
    """
    from devops_utils.mcp import server

    order = []
    monkeypatch.setattr(server, "configure_stderr", lambda: order.append("stderr"))

    class _Server:
        def run(self):
            order.append("run")

    monkeypatch.setattr(server, "_build_server", _Server)
    server.main()
    assert order == ["stderr", "run"]
    assert not hasattr(server, "configure_stdio")


def test_sanitizer_reads_utf8_regardless_of_the_platform_default(tmp_path):
    """The read at ``load_file`` was the silent one: cp1252 mojibakes a UTF-8
    manifest, and ``dump_yaml`` then writes the corruption straight back out.
    """
    from devops_utils.core import sanitizer

    manifest = tmp_path / "m.yaml"
    manifest.write_bytes(
        "apiVersion: v1\nkind: ConfigMap\ndata:\n  nota: ação — ←\n".encode()
    )
    docs = list(yaml.safe_load_all(sanitizer.load_file(str(manifest))))
    assert docs[0]["data"]["nota"] == "ação — ←"

    out = tmp_path / "out.yaml"
    sanitizer.dump_yaml(docs, str(out), force=True, debug=False)
    assert yaml.safe_load(out.read_text(encoding="utf-8"))["data"]["nota"] == "ação — ←"


def test_cli_writes_non_ascii_to_a_cp1252_stdout(tmp_path):
    """End-to-end: the dry-run preview survives a legacy redirected stdout."""
    result = _run_cli(["azdo", "update", "1", "--title", "arrow ← dash —", "--dry-run"])
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert b"UnicodeEncodeError" not in result.stderr
    # The preview lives on stderr now; stdout stays free for the JSON payload.
    assert "dry run" in result.stderr.decode("utf-8", "replace")
    assert result.stdout == b""


def test_eager_option_output_survives_cp1252():
    """``--help`` is written during parsing, before the group callback runs.

    Click routes *errors* to stderr, which CPython already gives
    ``backslashreplace``; eager options print to **stdout**, which it does not.
    Only the pre-parse ``configure_stdio()`` in ``cli.main.main`` covers those.
    """
    result = _run_cli(["azdo", "get", "--help"])
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert b"UnicodeEncodeError" not in result.stderr
    assert "--full" in result.stdout.decode("utf-8", "replace")


def test_json_payload_on_stdout_survives_cp1252():
    """`azdo get … | jq` with no shell preamble: stdout must decode and parse.

    Driven through ``_echo``'s exact serialization rather than a live command,
    so the test needs no network but still crosses a real redirected stdout.
    """
    payload = {"id": 7, "title": "ação ← traço —"}
    result = _run_python(
        "from devops_utils.core.encoding import configure_stdio; configure_stdio();"
        "import json, click;"
        f"click.echo(json.dumps({payload!r}, indent=2, ensure_ascii=False))"
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert json.loads(result.stdout.decode("utf-8")) == payload


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run the CLI in a subprocess whose stdio defaults to a legacy code page."""
    return _spawn(["-m", "devops_utils.cli.main", *args])


def _run_python(source: str) -> subprocess.CompletedProcess:
    return _spawn(["-c", source])


def _spawn(argv: list[str]) -> subprocess.CompletedProcess:
    import os
    from pathlib import Path

    env = {
        **{k: v for k, v in os.environ.items() if k not in _ENCODING_ENV},
        "PYTHONIOENCODING": "cp1252",
        "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src"),
    }
    return subprocess.run([sys.executable, *argv], capture_output=True, env=env)


#: Cleared so the subprocess cannot be rescued by an inherited preamble.
_ENCODING_ENV = ("PYTHONIOENCODING", "PYTHONUTF8")
