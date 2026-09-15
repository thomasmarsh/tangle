"""Typed Python implementation of the Tangle Markdown graph tooling."""

from __future__ import annotations

from importlib.metadata import version as _distribution_version

__all__ = ["__version__"]

# The distribution version is declared once in ``pyproject.toml``; read it back
# from installed metadata so the package and the installer never diverge.
__version__ = _distribution_version("tangle")
