"""Sanitize Kubernetes manifests by masking Secret values."""

import os.path

import yaml

from devops_utils.core.io import eprint, input_confirm

# Mask placeholder written into sanitized output, not a real credential.
SECRET_MASK = "***secret_hidden**"  # nosec B105


def load_file(filename: str, debug: bool = False) -> str:
    """Read a file and return its contents."""
    with open(filename) as f:
        return f.read()


def sanitize(data, debug: bool = False):
    """Mask ``data``/``stringData`` values of every Kubernetes ``Secret`` document."""

    def _hide(_obj, _key: str):
        if _key not in _obj:
            return
        for k, _ in _obj[_key].items():
            obj[_key][k] = SECRET_MASK
            if debug:
                name = (
                    obj["metadata"]["name"]
                    if "metadata" in obj and "name" in obj["metadata"]
                    else ""
                )
                eprint(f"Ocultando key '{k}' do secret '{name}'")

    out_objs = []
    for obj in yaml.safe_load_all(data):
        is_secret = "kind" in obj and obj["kind"] == "Secret"
        if is_secret:
            _hide(obj, "data")
            _hide(obj, "stringData")
        out_objs.append(obj)
    return out_objs


def dump_yaml(data, filename: str, force: bool, debug: bool) -> None:
    """Serialize ``data`` to ``filename`` (``-`` for stdout)."""
    if not filename or not filename.strip():
        raise ValueError(f"filename '{filename}' is invalid")

    if debug:
        eprint(f"Salvando yaml em '{filename}'")

    if filename == "-":
        print(yaml.dump_all(data, default_flow_style=False))
        return

    if os.path.exists(filename) and not force:
        confirm = input_confirm(f"File '{filename}' already exists, confirm overwrite?")
        if not confirm:
            raise RuntimeError(f"Operation aborted, file '{filename}' already exists")

    with open(filename, "w+") as stream:
        yaml.dump_all(data, stream=stream, default_flow_style=False)
