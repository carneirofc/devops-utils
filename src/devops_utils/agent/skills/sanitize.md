---
name: sanitize-manifest
description: Mask secret values in Kubernetes YAML manifests before sharing or committing.
---

# Sanitize Kubernetes manifest

Use this skill when a Kubernetes YAML manifest (or a multi-document stream) must be
shared, logged, or committed without exposing secret material.

## What it does

For every document whose `kind` is `Secret`, all values under `data` and
`stringData` are replaced with the mask `***secret_hidden**`. Non-Secret documents
pass through unchanged, and document order is preserved.

## How to invoke

- **CLI:** `devops-utils sanitize <file> -o -` (write masked YAML to stdout) or
  `devops-utils sanitize <file> -o out.yml`.
- **MCP tool:** `sanitize_manifest(manifest: str) -> str` — served by
  `devops-utils-mcp` (requires the `mcp` extra).
- **Python / agent:** `from devops_utils.agent.tools import sanitize_manifest`.

## Input / output

- **Input:** a string containing one or more Kubernetes YAML documents.
- **Output:** the same documents serialized back to YAML, with Secret values masked.

## Notes

- Masking is one-way; the original secret values cannot be recovered from the output.
- The tool does not validate the manifest against the Kubernetes schema.
