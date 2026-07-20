"""devops-utils: a set of utility tools for DevOps."""

from importlib.metadata import PackageNotFoundError, version

__author__ = "Cláudio Ferreira Carneiro"
__email__ = "claudiofcarneiro@gmail.com"

try:
    __version__ = version("devops-utils")
except PackageNotFoundError:  # package is not installed
    __version__ = "0.0.0"

__all__ = ["__author__", "__email__", "__version__"]
