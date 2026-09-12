"""The read-only ``graph-check`` vault validator.

This scaffold preserves the option surface (``--allow-stale``,
``--allow-orphan NODE``, ``-h``/``--help``), the positional
``nodes-directory`` argument, and the ``0``/``1``/``2`` exit codes. The full
checker is implemented by TAS-039.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

__all__ = ["main"]

_USAGE = (
    "usage: graph-check [--allow-stale] [--allow-orphan NODE] [nodes-directory]\n"
    "Validate a file-only Braintree vault without writing state."
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``graph-check`` command and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg in {"-h", "--help"} for arg in args):
        print(_USAGE)
        return 0
    print("error: validator is not implemented in the scaffold", file=sys.stderr)
    return 1
