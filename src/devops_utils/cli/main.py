"""Root Click group for the ``devops-utils`` command."""

import click

from devops_utils import __version__
from devops_utils.cli.commands.azdo import azdo
from devops_utils.cli.commands.sanitize import sanitize


@click.group()
@click.version_option(__version__, prog_name="devops-utils")
def cli() -> None:
    """A set of utility tools for DevOps."""


cli.add_command(sanitize)
cli.add_command(azdo)


if __name__ == "__main__":
    cli()
