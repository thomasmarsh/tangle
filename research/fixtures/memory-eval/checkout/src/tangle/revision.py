"""Resolve the Tangle revision recorded when the skill was installed.

The installer writes ``installed-revision`` next to this module: the semantic
version from ``pyproject.toml`` plus the source revision the skill was copied
from, for example ``0.4.0+g1b58d57``. When no source revision can be
determined, the record keeps the version and states the revision explicitly as
``unknown``, for example ``0.4.0+unknown``. A checkout with no record reports
the plain declared version, so the source repository never invents a revision.
"""

from __future__ import annotations

from pathlib import Path

from . import __version__

__all__ = [
    "RECORD_NAME",
    "feedback_revision",
    "recorded_revision",
    "reported_version",
]

# The generated install record sits beside this module so it travels with the
# package, including when ``uv`` builds and installs a wheel.
RECORD_NAME = "installed-revision"


def _record_path() -> Path:
    return Path(__file__).with_name(RECORD_NAME)


def recorded_revision() -> str | None:
    """Return the install-time revision stamp, or ``None`` without a record."""
    try:
        text = _record_path().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def reported_version() -> str:
    """Return the recorded revision when installed, else the declared version."""
    return recorded_revision() or __version__


def feedback_revision() -> str:
    """Return the revision to stamp into ``FBK`` feedback frontmatter.

    The install record is used verbatim when it is present. A checkout with no
    record degrades explicitly to the declared version with an ``unknown``
    revision, matching the installer's own ``<version>+unknown`` fallback and
    the ``tangle_revision`` convention ``graph-check`` accepts.
    """
    return recorded_revision() or f"{__version__}+unknown"
