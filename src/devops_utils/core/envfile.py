"""Load Azure DevOps settings from an env file into ``os.environ``.

``AzureDevOpsClient.from_env`` reads only process environment variables. On
Windows that means ``setx``/``$env:`` juggling, and an MCP server launched by
Claude Desktop or Claude Code never sees variables set in a PowerShell session.
An env file next to the user's profile works the same on every OS and every
launcher.

Only the **first existing** file of these is used:

1. ``$DEVOPS_UTILS_ENV_FILE`` — an explicit path.
2. ``./.env.devops-utils`` — project scope (keep it out of git).
3. ``~/.devops-utils.env`` — user scope (``%USERPROFILE%`` on Windows).

Files are never merged, and a variable already in the process environment
always wins. Both rules exist so a cloned repo's project file cannot pair its
own ``AZURE_DEVOPS_ORG_URL`` with the token from your user file or session and
ship that token to a server of its choosing. For the same reason an org URL
from a file is ignored unless the token in effect comes from that same file,
and only ``AZURE_DEVOPS_*`` keys are ever loaded.

The format is the usual ``KEY=VALUE`` subset: ``#`` comments, blank lines, an
optional leading ``export``, and optional matching single/double quotes. A UTF-8
BOM and CRLF line endings — what Notepad writes — are tolerated. Nothing is
expanded or executed.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Env var naming an explicit env file to load first.
ENV_FILE_VAR = "DEVOPS_UTILS_ENV_FILE"

#: Project-scope env file name (resolved against the current directory).
PROJECT_ENV_FILE = ".env.devops-utils"

#: User-scope env file name (resolved against the home directory).
USER_ENV_FILE = ".devops-utils.env"

#: Only keys with this prefix are loaded from a file.
KEY_PREFIX = "AZURE_DEVOPS_"

_ORG_URL = "AZURE_DEVOPS_ORG_URL"
_TOKEN = "AZURE_DEVOPS_TOKEN"  # nosec B105 - env var name, not a secret


def env_file_candidates() -> list[Path]:
    """Return the env files to try, highest precedence first."""
    candidates: list[Path] = []
    explicit = os.environ.get(ENV_FILE_VAR, "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(Path.cwd() / PROJECT_ENV_FILE)
    candidates.append(Path.home() / USER_ENV_FILE)
    return candidates


def parse_env_text(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines; malformed lines are skipped, not fatal."""
    values: dict[str, str] = {}
    for raw in text.lstrip("﻿").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key.isidentifier():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env_files(candidates: list[Path] | None = None) -> Path | None:
    """Fill unset ``AZURE_DEVOPS_*`` variables from the first existing env file.

    Never overrides a variable that is already set (even to an empty string —
    an explicit empty value is the user's choice). Unreadable files are skipped
    so a stray permission problem can't stop the CLI from starting.

    Returns:
        The file that was used, or ``None``.
    """
    for path in env_file_candidates() if candidates is None else candidates:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        values = {
            key: value
            for key, value in parse_env_text(text).items()
            if key.startswith(KEY_PREFIX)
        }
        # The org URL only travels with the token that will actually be used.
        if _TOKEN not in values or _TOKEN in os.environ:
            values.pop(_ORG_URL, None)
        for key, value in values.items():
            os.environ.setdefault(key, value)
        return path
    return None
