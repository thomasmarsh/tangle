"""Read-only cross-vault scan for Braintree ``FBK`` feedback nodes.

The scan reads only the filename, status directory, and frontmatter of
``FBK-*.md`` files under each vault's ``.braintree/`` tree, or the legacy
``nodes/`` tree, without migrating either. It never opens the sidecar, never
touches the network, and never writes to the scanned vault, so a maintainer can
collect feedback from a read-only checkout into a compact list ready for
triage in this graph.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Sequence

from . import store, vault
from .toon import field, row

__all__ = ["main"]

_USAGE = (
    "usage: braintree feedback scan [--limit N] VAULT [VAULT ...]\n"
    "Scan external vaults for FBK feedback nodes without writing state."
)

_FEEDBACK_GLOB = "FBK-*.md"
_POSITIVE_INTEGER = re.compile(r"[0-9]+\Z")


def _frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if re.fullmatch(r"---\s*", lines[index]):
            return "\n".join(lines[1:index])
    return None


def _frontmatter_value(header: str | None, key: str) -> str | None:
    if header is None:
        return None
    match = re.search(rf"^{re.escape(key)}:\s*(.*)$", header, re.MULTILINE)
    if match is None:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value or None


def _nodes_directory(argument: str) -> str:
    """Return the vault directory under ``argument``, accepting the legacy name.

    A vault root is scanned at ``.braintree/`` when present and otherwise at
    ``nodes/``; a directory that is already a vault is returned unchanged. The
    scan never migrates the external vault, so a legacy vault is read in place.
    """
    for name in (vault.DIRECTORY_NAME, vault.LEGACY_DIRECTORY_NAME):
        candidate = os.path.join(argument, name)
        if os.path.isdir(candidate):
            return candidate
    return argument


def _scan_vault(vault: str, nodes_dir: str) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for entry in store.iter_node_paths(nodes_dir):
        path, status = entry.path, entry.status
        if not os.path.basename(path).startswith("FBK-"):
            continue
        name = os.path.basename(path)[:-3]
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        header = _frontmatter(text)
        rows.append(
            (
                vault,
                name,
                status or "",
                _frontmatter_value(header, "braintree_revision") or "",
                _frontmatter_value(header, "summary") or "",
            )
        )
    return rows


def _print_results(rows: Sequence[tuple[str, str, str, str, str]]) -> None:
    if not rows:
        print("feedback: 0 nodes")
        return
    header = "vault,id,status,revision,summary"
    print(f"feedback[{len(rows)}]{{{header}}}:")
    for cells in rows:
        print(row(cells))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``braintree feedback scan`` command and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    limit: int | None = None
    vaults: list[str] = []
    while args:
        argument = args.pop(0)
        if argument in {"-h", "--help"}:
            print(_USAGE)
            return 0
        if argument == "--limit":
            if not args:
                print(field("error", "--limit requires N"))
                return 2
            raw_limit = args.pop(0)
            if _POSITIVE_INTEGER.fullmatch(raw_limit) is None or int(raw_limit) <= 0:
                print(field("error", "--limit must be a positive integer"))
                return 2
            limit = int(raw_limit)
        elif argument.startswith("-"):
            print(field("error", f"unknown option: {argument}"))
            return 2
        else:
            vaults.append(argument)
    if not vaults:
        print(field("error", "braintree feedback scan requires at least one vault"))
        print(field("help", "Run `braintree feedback scan --help` for usage."))
        return 2
    rows: list[tuple[str, str, str, str, str]] = []
    for vault_root in vaults:
        nodes_dir = _nodes_directory(vault_root)
        if not os.path.isdir(nodes_dir):
            print(field("error", f"nodes directory does not exist: {nodes_dir}"))
            print(
                field(
                    "help",
                    "Pass a vault root containing .braintree/ (or legacy "
                    "nodes/) or a vault directory.",
                )
            )
            return 1
        rows.extend(_scan_vault(vault_root, nodes_dir))
    rows.sort(key=lambda cells: (cells[0], cells[1]))
    if limit is not None:
        rows = rows[:limit]
    _print_results(rows)
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
