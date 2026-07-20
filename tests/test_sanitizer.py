"""Tests for the manifest sanitizer and the CLI wrapper."""

from click.testing import CliRunner

from devops_utils.cli.main import cli
from devops_utils.core.sanitizer import SECRET_MASK, sanitize

SECRET_MANIFEST = """
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
data:
  password: c2VjcmV0
stringData:
  token: super-secret-token
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  color: blue
"""


def test_sanitize_masks_secret_values():
    docs = sanitize(SECRET_MANIFEST)
    secret = docs[0]
    assert secret["data"]["password"] == SECRET_MASK
    assert secret["stringData"]["token"] == SECRET_MASK


def test_sanitize_leaves_non_secret_documents_untouched():
    docs = sanitize(SECRET_MANIFEST)
    config = docs[1]
    assert config["kind"] == "ConfigMap"
    assert config["data"]["color"] == "blue"


def test_sanitize_preserves_document_order_and_count():
    docs = sanitize(SECRET_MANIFEST)
    assert [d["kind"] for d in docs] == ["Secret", "ConfigMap"]


def test_cli_sanitize_to_stdout(tmp_path):
    manifest = tmp_path / "manifest.yml"
    manifest.write_text(SECRET_MANIFEST, encoding="utf-8")

    result = CliRunner().invoke(cli, ["sanitize", str(manifest), "-o", "-"])

    assert result.exit_code == 0, result.output
    assert SECRET_MASK in result.output
    assert "super-secret-token" not in result.output
    assert "blue" in result.output  # non-secret value survives
