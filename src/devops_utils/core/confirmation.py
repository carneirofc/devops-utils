"""Shared human-in-the-loop confirmation bypass, used by the MCP server and CLI.

Both surfaces gate Azure DevOps writes behind a human confirmation step; this
module holds the one env var/check they share so the name and truthy-parsing
rules can't drift between them.
"""

import os

SKIP_CONFIRMATION_ENV = "DEVOPS_UTILS_SKIP_CONFIRMATION"


def skip_confirmation() -> bool:
    """Whether write confirmation is bypassed via env var (unattended automation)."""
    return os.environ.get(SKIP_CONFIRMATION_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
