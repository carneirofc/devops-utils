"""Tests for CLI stdio encoding hardening (:mod:`devops_utils.cli.encoding`).

Regression guard for ``UnicodeEncodeError: 'charmap' codec can't encode
character '\\u2190'`` — raised when a work-item title (or the CLI's own ``—``)
was echoed to a redirected Windows stdout, which defaults to ``cp1252``.
"""

import io
import subprocess
import sys

from devops_utils.cli import encoding


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


def test_cli_writes_non_ascii_to_a_cp1252_stdout(tmp_path):
    """End-to-end: the dry-run preview survives a legacy redirected stdout."""
    env = {
        **_clean_env(),
        "PYTHONIOENCODING": "cp1252",
        "PYTHONPATH": str(_src_dir()),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "devops_utils.cli.main",
            "azdo",
            "update",
            "1",
            "--title",
            "arrow ← dash —",
            "--dry-run",
        ],
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert b"UnicodeEncodeError" not in result.stderr
    assert "dry run" in result.stdout.decode("utf-8", "replace")


def _clean_env() -> dict[str, str]:
    import os

    return {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}


def _src_dir() -> str:
    from pathlib import Path

    return str(Path(__file__).resolve().parent.parent / "src")
