"""Deterministic, offline filesystem diagnostic for the file-only graph.

Typed Python implementation of the behavioral filesystem diagnostic. It creates a
realistic cold-resumption corpus and measures bounded local reads; it is not a
model-token benchmark. The tracked ``benchmark/behavioral-baseline.txt``
metrics and the ``filesystem_diagnostic{...}`` line are preserved.
"""

from __future__ import annotations

import re
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path

__all__ = ["main"]

ROOT = "IDX-900-execution-memory"
DEFAULT_SCALES = (100, 1000)
MAX_SCALE = 10_000

_FRONTMATTER = re.compile(r"^---\s*$", re.MULTILINE)
_CONTEXT_REV = re.compile(r"^context_rev: (\d+)$", re.MULTILINE)
_DEPENDENCY_PIN = re.compile(r"Depends on \[\[DEF-900-routing\]\] at context_rev (\d+)\.")
_PRIMARY_ROUTE = re.compile(r"^(?:Parent|Area) \[\[([^\]]+)\]\]\.", re.MULTILINE)
_USAGE = (
    "usage: behavioral-benchmark [--scales N,N] [--verify]\n"
    "Generate temporary fixtures and report secondary filesystem diagnostics."
)


class _UsageError(Exception):
    """A command-line error that maps to exit code 2."""


class _FixtureError(Exception):
    """A generated fixture or baseline violated its contract."""


def _repo_root() -> Path:
    """Return the checkout root that holds the tracked baseline."""
    return Path(__file__).resolve().parents[2]


def _baseline_path() -> Path:
    return _repo_root() / "benchmark" / "behavioral-baseline.txt"


def _usage() -> None:
    print(_USAGE)


def _parse_options(argv: Sequence[str]) -> tuple[list[int], bool]:
    scales = list(DEFAULT_SCALES)
    verify = False
    args = list(argv)
    while args:
        option = args.pop(0)
        if option == "--verify":
            verify = True
        elif option == "--scales":
            if not args:
                raise _UsageError("--scales requires N,N")
            value = args.pop(0)
            try:
                scales = [int(part, 10) for part in value.split(",")]
            except ValueError as error:
                raise _UsageError(f"invalid integer in --scales: {value}") from error
        elif option in {"-h", "--help"}:
            _usage()
            raise SystemExit(0)
        else:
            raise _UsageError("unknown option")
    if not all(13 <= scale <= MAX_SCALE for scale in scales):
        raise _UsageError(f"scales must be 13 through {MAX_SCALE}")
    return sorted(set(scales)), verify


def _node(
    *,
    rev: int,
    summary: str,
    body: str,
    priority: str | None = None,
    next_action: str | None = None,
    disposition: str | None = None,
) -> str:
    fields = ["---", f"context_rev: {rev}"]
    if priority is not None:
        fields.append(f"priority: {priority}")
    fields.append("updated: 2026-01-15T12:00:00Z")
    fields.append(f"summary: {summary}")
    if next_action is not None:
        fields.append(f"next: {next_action}")
    if disposition is not None:
        fields.append(f"disposition: {disposition}")
    fields.extend(["---", "", body, ""])
    return "\n".join(fields)


def _write_fixture(root: Path, scale: int) -> None:
    for status in ("proposed", "active", "blocked", "resolved"):
        (root / status).mkdir(parents=True, exist_ok=True)

    def write(status: str, name: str, text: str) -> None:
        (root / status / f"{name}.md").write_text(text, encoding="utf-8")

    (root / "index-map.md").write_text(
        f"# Root hubs\n\n- Indexes [[{ROOT}]]: benchmark execution-memory route.\n",
        encoding="utf-8",
    )
    write(
        "resolved",
        ROOT,
        _node(rev=1, summary="Durable root for benchmark work.", body="# Invariant\n\nRoot hub."),
    )
    write(
        "resolved",
        "DEF-900-routing",
        _node(
            rev=2,
            summary="Token routing invariant.",
            body=f"# Context\n\nArea [[{ROOT}]].\n\n# Invariant\n\nUse the current routing rule.",
        ),
    )
    write(
        "resolved",
        "DEC-900-routing-v1",
        _node(
            rev=1,
            summary="Old token routing decision.",
            disposition="superseded",
            body=f"# Context\n\nArea [[{ROOT}]].\n\nSuperseded by [[DEC-901-routing-v2]].",
        ),
    )
    write(
        "resolved",
        "DEC-901-routing-v2",
        _node(
            rev=1,
            summary="Current token routing decision.",
            body=(
                f"# Context\n\nArea [[{ROOT}]].\n\n"
                "# Decision\n\nUse the current routing rule."
            ),
        ),
    )
    statuses = ("active", "proposed", "blocked", "resolved")
    for index in range(scale - 5):
        node_id = f"TAS-{index + 1:05d}"
        # The cold-resume record must be executable, not merely historically P0.
        status = "active" if index == 7 else statuses[index % 4]
        priority = "P0" if index == 7 else "P2"
        pin = 2 if index % 2 == 0 else 1
        topic = (
            "Cold-resume token routing incident."
            if index == 7
            else f"Routine maintenance record {index}."
        )
        body = (
            f"# Context\n\nArea [[{ROOT}]].\n\n"
            f"Depends on [[DEF-900-routing]] at context_rev {pin}.\n\n"
            f"# Outcome\n\n{topic}\n"
        )
        next_action = None if status == "resolved" else "Inspect the current routing invariant."
        write(
            status,
            node_id,
            _node(rev=1, summary=topic, priority=priority, next_action=next_action, body=body),
        )
    # An unfinished disconnected record is an actionable integrity failure.
    write(
        "active",
        "TAS-99999-orphan",
        _node(
            rev=1,
            summary="Disconnected actionable record.",
            next_action="Restore its primary route.",
            body="# Context\n\nParent [[MISSING-900]].",
        ),
    )


def _metadata(text: str) -> dict[str, str]:
    parts = _FRONTMATTER.split(text, maxsplit=2)
    header = parts[1] if len(parts) > 1 else ""
    fields: dict[str, str] = {}
    for raw_line in header.splitlines():
        key, separator, value = raw_line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def _assert_result(label: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise _FixtureError(
            f"fixture workflow failure for {label}: expected {expected!r}, got {actual!r}"
        )


def _scan(paths: Sequence[Path]) -> tuple[int, int, list[tuple[Path, str]]]:
    reads = 0
    byte_count = 0
    contents: list[tuple[Path, str]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        reads += 1
        byte_count += len(text.encode("utf-8"))
        contents.append((path, text))
    return reads, byte_count, contents


def _measure[T](step: Callable[[], T]) -> tuple[T, float]:
    started = time.monotonic()
    result = step()
    return result, round((time.monotonic() - started) * 1000, 2)


def _run_scale(scale: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="bt-behavioral-") as temp:
        root = Path(temp)
        _write_fixture(root, scale)
        paths = sorted(root.glob("*/*.md"))

        def resume_step() -> tuple[list[str], int, int]:
            route = (root / "index-map.md").read_text(encoding="utf-8")
            if f"Indexes [[{ROOT}]]" not in route:
                raise _FixtureError("fixture lacks root route")
            reads, byte_count, contents = _scan(paths)
            hits: list[str] = []
            for path, text in contents:
                fields = _metadata(text)
                if (
                    path.parent.name == "active"
                    and fields.get("priority") == "P0"
                    and "Cold-resume token routing incident." in text
                ):
                    if fields.get("next") != "Inspect the current routing invariant.":
                        raise _FixtureError(
                            "cold resume selected a task without an executable next action"
                        )
                    hits.append(path.stem)
            _assert_result("cold resume", hits, ["TAS-00008"])
            return hits, reads + 1, byte_count + len(route.encode("utf-8"))

        def current_step() -> tuple[list[str], int, int]:
            reads, byte_count, contents = _scan(paths)
            hits: list[str] = []
            for path, text in contents:
                fields = _metadata(text)
                if (
                    path.name.startswith("DEC-")
                    and "disposition" not in fields
                    and "# Decision\n" in text
                ):
                    hits.append(path.stem)
            _assert_result("current decision", hits, ["DEC-901-routing-v2"])
            return hits, reads, byte_count

        def stale_step() -> tuple[list[str], int, int]:
            definition = (root / "resolved" / "DEF-900-routing.md").read_text(encoding="utf-8")
            match = _CONTEXT_REV.search(definition)
            current_rev = match.group(1) if match else ""
            reads, byte_count, contents = _scan(paths)
            hits: list[str] = []
            for path, text in contents:
                pin = _DEPENDENCY_PIN.search(text)
                if pin and pin.group(1) != current_rev:
                    hits.append(path.stem)
            _assert_result("stale dependencies", len(hits), (scale - 5) // 2)
            return hits, reads + 1, byte_count + len(definition.encode("utf-8"))

        def orphan_step() -> tuple[list[str], int, int]:
            known = {path.stem for path in paths}
            reads, byte_count, contents = _scan(paths)
            hits: list[str] = []
            for path, text in contents:
                target = _PRIMARY_ROUTE.search(text)
                if target and target.group(1) not in known and path.parent.name == "active":
                    hits.append(path.stem)
            _assert_result("unfinished orphan discovery", hits, ["TAS-99999-orphan"])
            return hits, reads, byte_count

        resume, resume_ms = _measure(resume_step)
        current, current_ms = _measure(current_step)
        stale, stale_ms = _measure(stale_step)
        orphans, orphan_ms = _measure(orphan_step)
        resume_hits, resume_reads, resume_bytes = resume
        current_hits, current_reads, current_bytes = current
        stale_hits, stale_reads, stale_bytes = stale
        orphan_hits, orphan_reads, orphan_bytes = orphans
        read_count = resume_reads + current_reads + stale_reads + orphan_reads
        byte_count = resume_bytes + current_bytes + stale_bytes + orphan_bytes
        return {
            "scale": scale,
            "nodes": len(paths),
            "reads": read_count,
            "bytes": byte_count,
            "resume": len(resume_hits),
            "current": len(current_hits),
            "stale": len(stale_hits),
            "orphan": len(orphan_hits),
            "work_units": read_count + byte_count,
            "ms": [resume_ms, current_ms, stale_ms, orphan_ms],
        }


def _baseline() -> dict[int, list[int]]:
    expected: dict[int, list[int]] = {}
    for line in _baseline_path().read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        scale, values = line.split(":", 2)
        expected[int(scale, 10)] = [int(value, 10) for value in values.split(",")]
    return expected


def main(argv: Sequence[str] | None = None) -> int:
    """Run the behavioral filesystem diagnostic and return the exit code."""
    try:
        scales, verify = _parse_options(sys.argv[1:] if argv is None else argv)
        expected = _baseline()
        missing = [scale for scale in scales if scale not in expected]
        if verify and missing:
            joined = ", ".join(str(scale) for scale in missing)
            raise _UsageError(f"no tracked baseline for scale(s): {joined}")
        for scale in scales:
            result = _run_scale(scale)
            metrics = [
                result["nodes"],
                result["reads"],
                result["bytes"],
                result["resume"],
                result["current"],
                result["stale"],
                result["orphan"],
                result["work_units"],
            ]
            if verify and expected[scale] != metrics:
                expected_line = ",".join(str(value) for value in expected[scale])
                actual_line = ",".join(str(value) for value in metrics)
                raise _FixtureError(
                    f"baseline mismatch at scale {scale}: "
                    f"expected {expected_line}, got {actual_line}"
                )
            timings = result["ms"]
            assert isinstance(timings, list)
            timing_line = "/".join(f"{value:.2f}" for value in timings)
            joined_metrics = ",".join(str(value) for value in metrics)
            print(
                "filesystem_diagnostic"
                "{scale,nodes,reads,bytes,resume,current,stale,orphan,work_units,ms}: "
                f"{scale},{joined_metrics},{timing_line}"
            )
        if verify:
            print("verification: passed")
        return 0
    except _UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        _usage()
        return 2
    except _FixtureError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
