import argparse
import yaml
import os.path

from devops_utils.utils import input_confirm, eprint


def load_file(filename: str, debug: bool = False):
    data = ""
    with open(filename, "r") as f:
        data = f.read()
    return data


def sanitize(data, debug: bool = False):
    def _hide(_obj, _key: str):
        if _key not in _obj:
            return
        for k, _ in _obj[_key].items():
            obj[_key][k] = "***secret_hidden**"
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


def dump_yaml(data, filename: str, force: bool):
    if not filename:
        raise ValueError(f"filename '{filename}' is invalid")

    if os.path.exists(filename) and not force:
        confirm = input_confirm(f"File '{filename}' already exists, confirm overwrite?")
        if not confirm:
            raise RuntimeError(f"Operation aborted, file '{filename}' already exists")

    with open(filename, "w+") as stream:
        yaml.dump_all(data, stream, default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="Nome do arquivo yaml")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Força a operação, sobrescrevendo arquivos quando necessário",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Habilita saída de debug",
    )
    args = parser.parse_args()

    filename: str = args.file
    force: bool = args.force
    debug: bool = args.debug

    data = load_file(filename)
    sanitized = sanitize(data, debug=debug)
    dump_yaml(sanitized, force=force, filename=f"{filename}__debug__")
