"""``devops-utils sanitize`` — mask secrets in a Kubernetes manifest."""

import click

from devops_utils.core.sanitizer import dump_yaml, load_file
from devops_utils.core.sanitizer import sanitize as _sanitize


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-o",
    "--output",
    default=None,
    help="Output filename, use '-' for stdout. Defaults to '<file>__debug__'.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force the operation, overwriting files when necessary.",
)
@click.option("--debug", is_flag=True, help="Enable debug output.")
def sanitize(file: str, output: str | None, force: bool, debug: bool) -> None:
    """Mask Secret values in the Kubernetes manifest FILE."""
    outfilename = output.strip() if output else f"{file}__debug__"

    data = load_file(file, debug=debug)
    sanitized = _sanitize(data, debug=debug)
    dump_yaml(sanitized, filename=outfilename, force=force, debug=debug)
