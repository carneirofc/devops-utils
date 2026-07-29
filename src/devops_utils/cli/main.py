"""Root Click group for the ``devops-utils`` command."""

import click

from devops_utils import __version__
from devops_utils.cli.commands.azdo import azdo
from devops_utils.cli.commands.sanitize import sanitize
from devops_utils.cli.commands.setup import setup
from devops_utils.core.encoding import configure_stdio


@click.group()
@click.version_option(__version__, prog_name="devops-utils")
def cli() -> None:
    """A set of utility tools for DevOps."""
    # Work-item text and this CLI's own output are non-ASCII; a redirected
    # stdout on Windows is cp1252 and would raise UnicodeEncodeError mid-write.
    # `main` already did this for the console script; repeating it here (the
    # call is idempotent) covers `python -m` and embedding `cli` directly.
    configure_stdio()


cli.add_command(sanitize)
cli.add_command(azdo)
cli.add_command(setup)


def main() -> None:
    """Console-script entry point.

    Configures stdio *before* Click parses ``argv``. Eager options (``--help``,
    ``--version``) print to stdout during parsing, which is too early for the
    group callback — and unlike stderr, stdout gets no ``backslashreplace``
    default from CPython.
    """
    configure_stdio()
    cli()


if __name__ == "__main__":
    main()
