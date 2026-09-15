"""The ``tangle project register`` verb: record an external project locally.

The durable project registry maps a lowercase alias to an immutable project UID
and a local vault location. It is local state, never canonical Markdown: the
generated ``views/projects.md`` page reads it through ``views._registered_projects``,
so it must not become a node. This module is the write side, letting a client
bind an alias to a cross-project UID without hand-editing JSON.

``src/tangle/cli.py`` and ``src/tangle/sidecar.py`` are two of the seven
``src/tangle/*.py`` paths embedded as observable prompt content in
``benchmark/memory-authority-cases.json``, so the verb lives in its own module
instead, the same route ``tangle.allocate`` and ``tangle.census`` take.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence

from . import identity, vault, views
from .toon import field

__all__ = ["main"]

_PATH_FLAG = "--path"


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `tangle project register --help` for operands and exit meanings.",
        )
    )
    return 2


def _registry_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Repair or remove the malformed registry; it is never overwritten.",
        )
    )
    return 1


def _conflict_error(alias: str, recorded: object, supplied: str) -> int:
    print(
        field(
            "error",
            f"alias {alias!r} is already bound to {recorded!r}, not {supplied!r}",
        )
    )
    print(
        field(
            "help",
            "A project UID is immutable; register a different alias or correct the UID.",
        )
    )
    return 1


def _runtime_error(message: str) -> int:
    print(field("error", message))
    print(field("help", "Check the vault location and retry."))
    return 1


def _read_projects(registry: str) -> tuple[dict[str, object] | None, int]:
    """Return the normalized registry entries or an exit code on malformed input.

    A missing file is an empty registry. A file that is not a JSON object, or a
    ``projects`` value that is not an object, is malformed and never repaired
    implicitly; the caller must not clobber it.
    """
    document: object = None
    try:
        with open(registry, encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        return {}, 0
    except (OSError, ValueError) as exc:
        return None, _registry_error(f"unable to read project registry {registry}: {exc}")
    if not isinstance(document, dict):
        return None, _registry_error(f"malformed project registry {registry}: not an object")
    raw = document.get("projects", document)
    if not isinstance(raw, dict):
        return None, _registry_error(
            f"malformed project registry {registry}: 'projects' must be an object"
        )
    return dict(raw), 0


def _write_projects(registry: str, projects: dict[str, object]) -> int:
    """Atomically write the normalized ``{"projects": ...}`` document.

    The page is staged in a same-directory process-unique temporary file and
    renamed into place, so a reader never observes a half-written registry and a
    concurrent writer still publishes one complete document.
    """
    text = json.dumps({"projects": projects}, indent=2, sort_keys=True) + "\n"
    try:
        directory = os.path.dirname(registry)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary = f"{registry}.{os.getpid()}.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(temporary, registry)
        except BaseException:
            try:
                os.remove(temporary)
            except OSError:
                pass
            raise
    except OSError as exc:
        return _runtime_error(f"unable to write project registry {registry}: {exc}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``tangle project register ALIAS UID [--path PATH]``.

    ``argv`` is the full ``tangle ...`` argument list, the same shape
    :func:`tangle.main.main` accepts, so the operands start after the two-word
    command at index 2.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    operands = args[2:]
    if len(operands) < 2:
        return _usage_error("project register requires ALIAS and UID")
    alias = operands[0]
    uid = operands[1]
    path = ""
    rest = operands[2:]
    position = 0
    while position < len(rest):
        token = rest[position]
        if token == _PATH_FLAG:
            if position + 1 >= len(rest):
                return _usage_error("--path requires a value")
            path = rest[position + 1]
            position += 2
        elif token.startswith(_PATH_FLAG + "="):
            path = token[len(_PATH_FLAG) + 1 :]
            position += 1
        else:
            return _usage_error(f"unexpected argument: {token}")
    if not identity.is_project_alias(alias):
        return _usage_error(
            "ALIAS must start with a lowercase letter and contain only lowercase "
            "letters, digits, or hyphens (at most 63 characters)"
        )
    if not identity.is_project_uid(uid):
        return _usage_error("UID must be a canonical prj- project UID")

    registry = os.path.join(vault.resolve(migrate_legacy=False), views.PROJECT_REGISTRY_FILE)
    projects, code = _read_projects(registry)
    if projects is None:
        return code
    entry: dict[str, object] = {}
    existing = projects.get(alias)
    if existing is not None:
        if not isinstance(existing, dict):
            return _registry_error(
                f"alias {alias!r} has a malformed entry in project registry {registry}"
            )
        recorded = existing.get("uid", "")
        if recorded != uid:
            return _conflict_error(alias, recorded, uid)
        entry = dict(existing)
    entry["uid"] = uid
    entry["path"] = path
    projects[alias] = entry
    code = _write_projects(registry, projects)
    if code != 0:
        return code
    print(field("alias", alias))
    print(field("project", uid))
    print(field("path", path))
    print(field("registry", os.path.abspath(registry)))
    return 0
