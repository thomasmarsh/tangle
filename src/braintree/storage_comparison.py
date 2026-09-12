"""Offline comparison of four status representations.

Typed Python port of ``scripts/storage-comparison.rb``. It creates disposable
Git repositories only; no fixture, cache, or status view is retained. The
``storage{...}`` line and the tracked baseline in
``benchmark/storage-comparison-baseline.txt`` are preserved.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = ["main"]

NODES = 100
ACTIVE = 25
_UU = re.compile(r"^UU ", re.MULTILINE)
_CONFLICT = re.compile(r"^CONFLICT ", re.MULTILINE)
_ACTIVE_INDEX = re.compile(r"^active: (.*)$", re.MULTILINE)

Transition = Callable[[str], None]


class _CaseError(Exception):
    """A Git fixture command failed."""


@dataclass
class _CaseResult:
    shape: str
    transition_paths: int
    query_reads: int
    query_entries: int
    conflicts: int
    stale: int
    stable: int


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _baseline_path() -> Path:
    return _repo_root() / "benchmark" / "storage-comparison-baseline.txt"


def _capture(*command: str, chdir: str) -> tuple[str, bool]:
    result = subprocess.run(
        command,
        cwd=chdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout or "", result.returncode == 0


def _run(*command: str, chdir: str) -> str:
    output, success = _capture(*command, chdir=chdir)
    if not success:
        raise _CaseError(f"{' '.join(command)}: {output}")
    return output


def _node(node_id: str, status: str | None = None) -> str:
    metadata = [
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        f"summary: Fixture {node_id}.",
    ]
    if status is not None:
        metadata.append(f"status: {status}")
    metadata.extend(["---", "", "Area [[IDX-900-root]].", ""])
    return "\n".join(metadata)


def _git_setup(root: str) -> None:
    _run("git", "init", "-q", chdir=root)
    _run("git", "config", "user.email", "fixture@example.invalid", chdir=root)
    _run("git", "config", "user.name", "Fixture", chdir=root)


def _commit(root: str, message: str) -> None:
    _run("git", "add", ".", chdir=root)
    _run("git", "commit", "-qm", message, chdir=root)


def _merge_conflicts(root: str, transition: Transition) -> int:
    base = _run("git", "branch", "--show-current", chdir=root).strip()
    _run("git", "checkout", "-qb", "left", chdir=root)
    transition("TAS-00001")
    _commit(root, "left transition")
    _run("git", "checkout", "-q", base, chdir=root)
    _run("git", "checkout", "-qb", "right", chdir=root)
    transition("TAS-00002")
    _commit(root, "right transition")
    output, success = _capture("git", "merge", "left", chdir=root)
    if success:
        return 0
    return len(_UU.findall(output)) + len(_CONFLICT.findall(output))


def _diff_shape(root: str, transition: Transition) -> tuple[str, int]:
    transition("TAS-00003")
    _run("git", "add", "-A", chdir=root)
    output = _run("git", "diff", "--cached", "--name-status", "-M", chdir=root)
    codes = [line.split()[0] for line in output.splitlines() if line.split()]
    shape = "+".join(sorted(codes))
    weight = sum(2 if code.startswith(("R", "C")) else 1 for code in codes)
    return shape, weight


def _restore(root: str) -> None:
    _run("git", "reset", "--hard", "-q", "HEAD", chdir=root)
    _run("git", "clean", "-fdq", chdir=root)


def _status_count(paths: Sequence[str]) -> int:
    return sum(1 for path in paths if os.path.exists(path))


def _directory_case(root: str) -> _CaseResult:
    for status in ("active", "proposed", "blocked", "resolved"):
        os.makedirs(os.path.join(root, "nodes", status), exist_ok=True)
    for index in range(NODES):
        node_id = f"TAS-{index + 1:05d}"
        status = "active" if index < ACTIVE else "resolved"
        path = os.path.join(root, "nodes", status, f"{node_id}.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(_node(node_id))
    query_entries = _status_count(glob.glob(os.path.join(root, "nodes", "active", "*.md")))
    _commit(root, "baseline")

    def transition(node_id: str) -> None:
        os.replace(
            os.path.join(root, "nodes", "active", f"{node_id}.md"),
            os.path.join(root, "nodes", "resolved", f"{node_id}.md"),
        )

    shape, paths = _diff_shape(root, transition)
    _restore(root)
    conflicts = _merge_conflicts(root, transition)
    return _CaseResult(shape, paths, 0, query_entries, conflicts, 0, 0)


def _stationary_case(root: str) -> _CaseResult:
    canonical = os.path.join(root, "nodes", "canonical")
    for index in range(NODES):
        node_id = f"TAS-{index + 1:05d}"
        directory = os.path.join(canonical, node_id[-2:])
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"{node_id}.md"), "w", encoding="utf-8") as handle:
            handle.write(_node(node_id, "active" if index < ACTIVE else "resolved"))
    paths = glob.glob(os.path.join(canonical, "*", "*.md"))
    query_entries = 0
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            if "status: active" in handle.read():
                query_entries += 1
    _commit(root, "baseline")

    def transition(node_id: str) -> None:
        path = glob.glob(os.path.join(canonical, "*", f"{node_id}.md"))[0]
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace("status: active", "status: resolved"))

    shape, paths_changed = _diff_shape(root, transition)
    _restore(root)
    conflicts = _merge_conflicts(root, transition)
    return _CaseResult(shape, paths_changed, len(paths), query_entries, conflicts, 0, 1)


def _symlink_case(root: str) -> _CaseResult:
    canonical = os.path.join(root, "nodes", "canonical")
    for status in ("active", "resolved"):
        os.makedirs(os.path.join(root, "nodes", "status", status), exist_ok=True)
    for index in range(NODES):
        node_id = f"TAS-{index + 1:05d}"
        directory = os.path.join(canonical, node_id[-2:])
        os.makedirs(directory, exist_ok=True)
        source = os.path.join(directory, f"{node_id}.md")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(_node(node_id))
        status = "active" if index < ACTIVE else "resolved"
        link = os.path.join(root, "nodes", "status", status, f"{node_id}.md")
        os.symlink(os.path.join("..", "..", "canonical", node_id[-2:], f"{node_id}.md"), link)
    query_entries = _status_count(
        glob.glob(os.path.join(root, "nodes", "status", "active", "*.md"))
    )
    _commit(root, "baseline")

    def transition(node_id: str) -> None:
        old = os.path.join(root, "nodes", "status", "active", f"{node_id}.md")
        new = os.path.join(root, "nodes", "status", "resolved", f"{node_id}.md")
        os.replace(old, new)

    shape, paths = _diff_shape(root, transition)
    _restore(root)
    conflicts = _merge_conflicts(root, transition)
    # A deleted view entry is invisible to a directory query although its
    # canonical node still exists; this is the stale/broken-view failure mode.
    link = os.path.join(root, "nodes", "status", "active", "TAS-00004.md")
    os.remove(link)
    source = glob.glob(os.path.join(canonical, "*", "TAS-00004.md"))[0]
    stale = 1 if os.path.exists(source) and not os.path.exists(link) else 0
    return _CaseResult(shape, paths, 0, query_entries, conflicts, stale, 1)


def _index_case(root: str) -> _CaseResult:
    canonical = os.path.join(root, "nodes", "canonical")
    for index in range(NODES):
        node_id = f"TAS-{index + 1:05d}"
        directory = os.path.join(canonical, node_id[-2:])
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"{node_id}.md"), "w", encoding="utf-8") as handle:
            handle.write(_node(node_id))
    active = [f"TAS-{number:05d}" for number in range(1, ACTIVE + 1)]
    index_path = os.path.join(root, "nodes", "status-index.md")

    def write_index(ids: Sequence[str]) -> None:
        with open(index_path, "w", encoding="utf-8") as handle:
            handle.write(f"active: {','.join(ids)}\n")

    def read_index() -> list[str]:
        with open(index_path, encoding="utf-8") as handle:
            match = _ACTIVE_INDEX.search(handle.read())
        if match is None:
            raise _CaseError("missing active status index")
        return [value for value in match.group(1).split(",") if value]

    write_index(active)
    query_entries = len(active)
    _commit(root, "baseline")

    def transition(node_id: str) -> None:
        # Read the checked-out fixture state for each scenario. A closure over
        # a mutable list would let diff-shape mutations leak into the branches.
        write_index([value for value in read_index() if value != node_id])

    shape, paths = _diff_shape(root, transition)
    _restore(root)
    conflicts = _merge_conflicts(root, transition)
    # Removing a name from the cache leaves the canonical file untouched.
    write_index([value for value in read_index() if value != "TAS-00004"])
    source = glob.glob(os.path.join(canonical, "*", "TAS-00004.md"))[0]
    stale = 1 if os.path.exists(source) else 0
    return _CaseResult(shape, paths, 1, query_entries, conflicts, stale, 1)


_CASES: dict[str, Callable[[str], _CaseResult]] = {
    "directory": _directory_case,
    "stationary": _stationary_case,
    "symlink": _symlink_case,
    "index": _index_case,
}


def _result_for(name: str) -> _CaseResult:
    with tempfile.TemporaryDirectory(prefix="bt-storage-") as root:
        _git_setup(root)
        return _CASES[name](root)


def _baseline() -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in _baseline_path().read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, value = line.split(":", 2)
        expected[name] = value
    return expected


def main(argv: Sequence[str] | None = None) -> int:
    """Run the storage-representation comparison and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    expected = _baseline()
    for name in _CASES:
        try:
            result = _result_for(name)
        except _CaseError as error:
            print(str(error), file=sys.stderr)
            return 1
        line = ",".join(
            str(value)
            for value in (
                result.shape,
                result.transition_paths,
                result.query_reads,
                result.query_entries,
                result.conflicts,
                result.stale,
                result.stable,
            )
        )
        if args == ["--verify"] and expected[name] != line:
            print(
                f"baseline mismatch for {name}: expected {expected[name]}, got {line}",
                file=sys.stderr,
            )
            return 1
        print(
            "storage{name,diff,transition_paths,query_reads,query_entries,"
            f"merge_conflicts,stale_view,stable_canonical_path}}: {name},{line}"
        )
    if args == ["--verify"]:
        print("verification: passed")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
