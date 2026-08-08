# Sanitize Kubernetes manifests

`devops-utils sanitize` reads a Kubernetes YAML file and replaces the values of
every `Secret`'s `data` / `stringData` keys with `***secret_hidden**`. Key names,
document order, and every other resource in the file are left untouched, so the
result still reads like the manifest you started from — it just can't leak a
credential.

No extra is required: `pip install devops-utils` is enough.

## What it does

Given `manifest.yml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-credentials
type: Opaque
data:
  DB_PASSWORD: c3VwZXItc2VjcmV0
  API_TOKEN: aGFtbWVydGltZQ==
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  LOG_LEVEL: debug
```

```bash
devops-utils sanitize manifest.yml -o -
```

```yaml
apiVersion: v1
data:
  API_TOKEN: '***secret_hidden**'
  DB_PASSWORD: '***secret_hidden**'
kind: Secret
metadata:
  name: api-credentials
type: Opaque
---
apiVersion: v1
data:
  LOG_LEVEL: debug
kind: ConfigMap
metadata:
  name: api-config
```

The `ConfigMap` passes through untouched — only `kind: Secret` documents are
masked.

## Use cases

### Paste a manifest into a ticket, chat, or an LLM prompt

The most common one. Dump the live object, mask it, and paste the result
anywhere:

```bash
kubectl get secret api-credentials -o yaml > /tmp/secret.yml
devops-utils sanitize /tmp/secret.yml -o - | pbcopy   # or xclip / clip.exe
```

### Attach a redacted manifest to a work item

```bash
devops-utils sanitize deploy.yml -o deploy.sanitized.yml
devops-utils azdo attach 42 ./deploy.sanitized.yml --comment "Redacted manifest"
```

### Snapshot a whole namespace for a review

```bash
kubectl get all,secret,configmap -n staging -o yaml > staging.yml
devops-utils sanitize staging.yml -o staging.review.yml
```

### Pre-commit guard for an example manifest

Keep a checked-in `examples/deploy.yml` honest by regenerating it from the real
one:

```bash
devops-utils sanitize deploy.yml -o examples/deploy.yml --force
```

## Options

| Flag | Effect |
| --- | --- |
| `-o`, `--output` | Destination file, or `-` for stdout. Defaults to `<file>__debug__` |
| `--force` | Overwrite the output file without asking |
| `--debug` | Report each masked key on stderr |

With no `-o`, the output lands next to the input as `manifest.yml__debug__` —
handy for a quick look, easy to forget about, so prefer an explicit `-o`.

Writing to an existing file prompts for confirmation unless `--force` is given;
`-o -` never prompts, which is what makes it safe to put in a pipe.

## From an agent or the MCP server

The same masking is available as `sanitize_manifest(manifest: str) -> str` —
both as an MCP tool and as a plain Python callable — taking the manifest as a
string rather than a path:

```python
from devops_utils.agent.tools import sanitize_manifest

redacted = sanitize_manifest(open("manifest.yml", encoding="utf-8").read())
```

Unlike the Azure DevOps write tools, it needs no confirmation gate: it touches
nothing outside its own input.
