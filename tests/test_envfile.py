"""Tests for env-file loading (Windows-friendly credentials, no setx needed)."""

import os

import pytest

from devops_utils.core import envfile

KEYS = (
    "AZURE_DEVOPS_ORG_URL",
    "AZURE_DEVOPS_TOKEN",
    "AZURE_DEVOPS_AUTH_SCHEME",
    "AZURE_DEVOPS_API_VERSION",
    "UNRELATED_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def test_parse_handles_comments_quotes_export_bom_and_crlf():
    text = (
        "﻿# comment\r\n"
        "\r\n"
        "export AZURE_DEVOPS_ORG_URL='https://dev.azure.com/contoso'\r\n"
        'AZURE_DEVOPS_TOKEN="abc=def"\r\n'
        "AZURE_DEVOPS_AUTH_SCHEME = pat \r\n"
        "not a pair\r\n"
        "1BAD=x\r\n"
    )
    assert envfile.parse_env_text(text) == {
        "AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/contoso",
        "AZURE_DEVOPS_TOKEN": "abc=def",
        "AZURE_DEVOPS_AUTH_SCHEME": "pat",
    }


def test_loads_azure_keys_only(tmp_path):
    env = tmp_path / ".devops-utils.env"
    env.write_text(
        "AZURE_DEVOPS_ORG_URL=https://x\nAZURE_DEVOPS_TOKEN=t\nUNRELATED_KEY=1\n",
        encoding="utf-8",
    )
    assert envfile.load_env_files([env]) == env
    assert os.environ["AZURE_DEVOPS_ORG_URL"] == "https://x"
    assert os.environ["AZURE_DEVOPS_TOKEN"] == "t"
    assert "UNRELATED_KEY" not in os.environ


def test_real_environment_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_AUTH_SCHEME", "bearer")
    env = tmp_path / "e.env"
    env.write_text("AZURE_DEVOPS_AUTH_SCHEME=pat\n", encoding="utf-8")
    envfile.load_env_files([env])
    assert os.environ["AZURE_DEVOPS_AUTH_SCHEME"] == "bearer"


def test_first_existing_file_wins_and_files_are_not_merged(tmp_path):
    project = tmp_path / "project.env"
    user = tmp_path / "user.env"
    project.write_text("AZURE_DEVOPS_API_VERSION=6.0\n", encoding="utf-8")
    user.write_text(
        "AZURE_DEVOPS_ORG_URL=https://mine\nAZURE_DEVOPS_TOKEN=secret\n",
        encoding="utf-8",
    )
    missing = tmp_path / "missing.env"
    assert envfile.load_env_files([missing, project, user]) == project
    assert os.environ["AZURE_DEVOPS_API_VERSION"] == "6.0"
    assert "AZURE_DEVOPS_TOKEN" not in os.environ


def test_org_url_without_token_in_same_file_is_ignored(tmp_path):
    env = tmp_path / "e.env"
    env.write_text("AZURE_DEVOPS_ORG_URL=https://attacker\n", encoding="utf-8")
    envfile.load_env_files([env])
    assert "AZURE_DEVOPS_ORG_URL" not in os.environ


def test_org_url_ignored_when_session_token_is_already_set(tmp_path, monkeypatch):
    # A repo's file must not redirect a token the user set in their session.
    monkeypatch.setenv("AZURE_DEVOPS_TOKEN", "session-secret")
    env = tmp_path / "e.env"
    env.write_text(
        "AZURE_DEVOPS_ORG_URL=https://attacker\nAZURE_DEVOPS_TOKEN=x\n",
        encoding="utf-8",
    )
    envfile.load_env_files([env])
    assert "AZURE_DEVOPS_ORG_URL" not in os.environ
    assert os.environ["AZURE_DEVOPS_TOKEN"] == "session-secret"


def test_no_files_returns_none(tmp_path):
    assert envfile.load_env_files([tmp_path / "nope.env"]) is None


def test_candidates_order(tmp_path, monkeypatch):
    monkeypatch.undo()  # drop the conftest stub for this one test
    monkeypatch.setenv("DEVOPS_UTILS_ENV_FILE", str(tmp_path / "explicit.env"))
    monkeypatch.chdir(tmp_path)
    names = [p.name for p in envfile.env_file_candidates()]
    assert names == ["explicit.env", ".env.devops-utils", ".devops-utils.env"]
