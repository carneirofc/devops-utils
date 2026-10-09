#!/usr/bin/env python
"""Fixtures for the tests."""

import pytest

__author__ = "Cláudio Ferreira Carneiro"
__docformat__ = "restructuredtext"


@pytest.fixture(autouse=True)
def _no_env_files(monkeypatch):
    """Keep the developer's own ~/.devops-utils.env out of every test.

    The CLI and MCP entry points load env files on start-up; tests that need
    that behaviour pass explicit candidates to ``load_env_files``.
    """
    monkeypatch.setattr("devops_utils.core.envfile.env_file_candidates", lambda: [])
