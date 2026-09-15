"""Zero-live staged A/B for the direct-answer surface.

``tangle benchmark staged`` compares one recorded pre-thrust sample against
one recorded landed sample of the same controlled token-benchmark task. A sample
is the artifact ``tangle benchmark token --record --output`` writes: a
``codex-session-token-v2`` record with the token totals, the round-trip counts,
the exact-value ``correctness`` flag, and the fixture/model/effort/CLI metadata.

The two records must match on the fixture generator (version, seed, case,
representation, scale), the requested model, the reasoning effort, and the Codex
CLI version, so the only deliberate difference is the state under test. The
generator plus the case name fixes both the generated node set and the prompt, so
matching those fields matches the fixture and the prompt. ``fixture_sha256`` is
deliberately not compared: the generated fixture embeds ``SKILL.md`` and
``src/tangle``, so its hash changes with the state under test even when the
fixture data and prompt are identical.

Every sample must pass its exact-value gate before any delta is reported: first
the record's own ``correctness`` flag, and, when the matching raw session and
answer are supplied, an independent re-run of the gate over the session stream.
The harness reuses the token benchmark's session parser for round trips, so a
record that predates the round-trip telemetry takes its counts from the matching
session JSONL. It makes no model calls, so ``make benchmark`` stays zero-live.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import token_benchmark

__all__ = ["main"]

Json = dict[str, Any]
PROTOCOL = "codex-session-token-v2"
STAGED_PROTOCOL = "staged-ab-v1"
FALLBACK_UNAVAILABLE = "no round-trip telemetry in record or session"
# The metadata that must match across the two samples: the fixture generator
# (which fixes the node set and the prompt), the model, the effort, and the CLI
# version.
_MATCHED_FIELDS = (
    "fixture_version",
    "fixture_seed",
    "benchmark_case",
    "representation",
    "scale",
    "requested_model",
    "requested_reasoning_effort",
    "requested_codex_version",
)
_TOKEN_FIELDS = (*token_benchmark.FIELDS, "uncached_input_tokens")
# Round trips are the goal the direct-answer surface serves; uncached input and
# total tokens are the cost that goal must not inflate. The decision reads only
# these, while the report still prints every token field.
_DECISION_METRICS = ("tool_calls", "uncached_input_tokens", "total_tokens")
_USAGE = (
    "usage: tangle benchmark staged --before RECORD.json --after RECORD.json\n"
    "       [--before-session S.jsonl --before-answer A.json]\n"
    "       [--after-session  S.jsonl --after-answer  A.json]\n"
    "       [--expected EXPECTED.json] [--output PATH]\n"
    "Compare a recorded pre-thrust and landed token-benchmark sample."
)


class _UsageError(Exception):
    """A command-line error that maps to exit code 2."""


class _StagedError(Exception):
    """A sample, match, or gate failure that maps to exit code 1."""


@dataclass(frozen=True)
class _Sample:
    """One gated side of the A/B with its token totals and round-trip counts."""

    label: str
    metadata: Json
    tokens: Json
    tool_calls: int | None
    shell_calls: int | None
    round_trip_source: str


def _usage() -> None:
    print(_USAGE)


def _load_json(path: str, kind: str) -> Json:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _StagedError(f"could not read {kind} {path}: {error}") from error
    if not isinstance(value, dict):
        raise _StagedError(f"{kind} {path} is not a JSON object")
    return value


def _metadata(record: Json, path: str) -> Json:
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        raise _StagedError(f"record {path} has no metadata object")
    return metadata


def _validate_record(record: Json, path: str) -> Json:
    if record.get("protocol") != PROTOCOL:
        raise _StagedError(f"record {path} is not a {PROTOCOL} record")
    if record.get("correctness") is not True:
        raise _StagedError(f"record {path} did not pass its exact-value gate")
    median = record.get("median")
    if not isinstance(median, dict):
        raise _StagedError(f"record {path} has no token median")
    for field in _TOKEN_FIELDS:
        value = median.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            raise _StagedError(f"record {path} median lacks integer {field}")
    return {field: int(median[field]) for field in _TOKEN_FIELDS}


def _record_round_trips(record: Json) -> tuple[int, int] | None:
    round_trips = record.get("round_trips")
    if not isinstance(round_trips, dict):
        return None
    median = round_trips.get("median")
    if not isinstance(median, dict):
        return None
    tool_calls = median.get("tool_calls")
    shell_calls = median.get("shell_calls")
    if isinstance(tool_calls, int) and isinstance(shell_calls, int):
        return tool_calls, shell_calls
    return None


def _round_trips(record: Json, session_path: str | None) -> tuple[int | None, int | None, str]:
    from_record = _record_round_trips(record)
    if from_record is not None:
        return from_record[0], from_record[1], "record"
    if session_path is not None:
        parsed = token_benchmark._session_round_trips(session_path)
        if parsed is not None:
            return int(parsed["tool_calls"]), int(parsed["shell_calls"]), "session"
    return None, None, "unavailable"


def _gate(session_path: str, answer_path: str, expected: Json) -> None:
    """Re-run the exact-value gate over a raw session stream and answer artifact."""
    stream = Path(session_path).read_text(encoding="utf-8")
    try:
        token_benchmark._completed_answer(stream, answer_path, expected)
    except token_benchmark._BenchError as error:
        raise _StagedError(f"exact-value gate failed for {answer_path}: {error}") from error


def _load_sample(
    label: str,
    record_path: str,
    session_path: str | None,
    answer_path: str | None,
    expected: Json | None,
) -> _Sample:
    if answer_path is not None and session_path is None:
        raise _UsageError(f"{label} needs a session to gate an answer")
    record = _load_json(record_path, "record")
    tokens = _validate_record(record, record_path)
    metadata = _metadata(record, record_path)
    if session_path is not None and answer_path is not None and expected is not None:
        _gate(session_path, answer_path, expected)
    tool_calls, shell_calls, source = _round_trips(record, session_path)
    if session_path is not None:
        _observed_match(label, session_path, metadata)
    return _Sample(
        label=label,
        metadata=metadata,
        tokens=tokens,
        tool_calls=tool_calls,
        shell_calls=shell_calls,
        round_trip_source=source,
    )


def _single_observation(observed: Json, field: str) -> str | None:
    values = observed.get(field)
    if isinstance(values, list) and len(values) == 1:
        return str(values[0])
    return None


def _observed_match(label: str, session_path: str, metadata: Json) -> None:
    """Compare a session's observed model/effort/CLI with its record metadata."""
    observed = token_benchmark._session_observations(  # noqa: SLF001
        session_path
    )
    pairs = (
        ("observed_model", "requested_model"),
        ("observed_reasoning_effort", "requested_reasoning_effort"),
        ("observed_cli_version", "requested_codex_version"),
    )
    for observed_field, requested_field in pairs:
        seen = _single_observation(observed, observed_field)
        requested = metadata.get(requested_field)
        if seen is None or not isinstance(requested, str):
            continue
        normalized = seen.removeprefix("codex-cli ")
        if normalized != requested.removeprefix("codex-cli "):
            raise _StagedError(
                f"{label} session {observed_field} {seen!r} does not match record "
                f"{requested_field} {requested!r}"
            )


def _match(before: _Sample, after: _Sample) -> Json:
    matched: Json = {}
    for field in _MATCHED_FIELDS:
        left = before.metadata.get(field)
        right = after.metadata.get(field)
        if left != right:
            raise _StagedError(
                f"unmatched {field}: before {left!r} != after {right!r}"
            )
        matched[field] = left
    return matched


def _delta(before: int, after: int) -> int:
    return after - before


def _decide(before: _Sample, after: _Sample) -> tuple[str, list[str], list[str], bool]:
    comparable = before.tool_calls is not None and after.tool_calls is not None
    metrics: list[tuple[str, int, int]] = [
        ("uncached_input_tokens", before.tokens["uncached_input_tokens"],
         after.tokens["uncached_input_tokens"]),
        ("total_tokens", before.tokens["total_tokens"], after.tokens["total_tokens"]),
    ]
    if comparable:
        assert before.tool_calls is not None and after.tool_calls is not None
        metrics.insert(0, ("tool_calls", before.tool_calls, after.tool_calls))
    improved = [name for name, left, right in metrics if right < left]
    regressed = [name for name, left, right in metrics if right > left]
    if not regressed:
        decision = "keep"
    elif not improved:
        decision = "revert"
    else:
        decision = "revise"
    return decision, improved, regressed, comparable


def _rationale(
    decision: str, improved: list[str], regressed: list[str], comparable: bool
) -> str:
    scope = (
        "round trips plus uncached and total tokens"
        if comparable
        else "uncached and total tokens (round trips unavailable)"
    )
    if decision == "keep":
        return f"{scope}: no regression; improved {', '.join(improved) or 'nothing'}"
    if decision == "revert":
        return f"{scope}: regression in {', '.join(regressed)} with no improvement"
    return (
        f"{scope}: mixed; improved {', '.join(improved)} but regressed "
        f"{', '.join(regressed)}"
    )


def _round_trip_cell(value: int | None) -> str:
    return "n/a" if value is None else str(value)


def _tool_calls_delta(before: _Sample, after: _Sample, comparable: bool) -> str:
    if not comparable:
        return "n/a"
    assert before.tool_calls is not None and after.tool_calls is not None
    return str(after.tool_calls - before.tool_calls)


def _emit(before: _Sample, after: _Sample, matched: Json, output_path: str | None) -> None:
    decision, improved, regressed, comparable = _decide(before, after)
    fields = {
        "case": matched["benchmark_case"],
        "representation": matched["representation"],
        "scale": matched["scale"],
        "model": matched["requested_model"],
        "effort": matched["requested_reasoning_effort"],
        "cli_version": matched["requested_codex_version"],
        "round_trips": "compared" if comparable else "unavailable",
        "decision": decision,
        "tool_calls_before": _round_trip_cell(before.tool_calls),
        "tool_calls_after": _round_trip_cell(after.tool_calls),
        "tool_calls_delta": _tool_calls_delta(before, after, comparable),
        "uncached_before": before.tokens["uncached_input_tokens"],
        "uncached_after": after.tokens["uncached_input_tokens"],
        "uncached_delta": _delta(
            before.tokens["uncached_input_tokens"], after.tokens["uncached_input_tokens"]
        ),
        "total_before": before.tokens["total_tokens"],
        "total_after": after.tokens["total_tokens"],
        "total_delta": _delta(before.tokens["total_tokens"], after.tokens["total_tokens"]),
    }
    header = ",".join(fields)
    values = ",".join(str(value) for value in fields.values())
    print(f"staged_ab{{{header}}}: {values}")
    record = {
        "protocol": STAGED_PROTOCOL,
        "decision": decision,
        "matched": matched,
        "round_trips": {
            "comparable": comparable,
            "before": {"tool_calls": before.tool_calls, "shell_calls": before.shell_calls},
            "after": {"tool_calls": after.tool_calls, "shell_calls": after.shell_calls},
            "sources": {"before": before.round_trip_source, "after": after.round_trip_source},
            "fallback": None if comparable else FALLBACK_UNAVAILABLE,
        },
        "tokens": {
            "before": before.tokens,
            "after": after.tokens,
            "delta": {
                field: _delta(before.tokens[field], after.tokens[field])
                for field in _TOKEN_FIELDS
            },
        },
        "improved": improved,
        "regressed": regressed,
        "rationale": _rationale(decision, improved, regressed, comparable),
    }
    print(json.dumps(record, separators=(",", ":"), ensure_ascii=False))
    if output_path:
        Path(output_path).write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


def _expected_answer(case: str, expected_path: str | None) -> Json | None:
    if expected_path is not None:
        return _load_json(expected_path, "expected answer")
    answer = token_benchmark.CASES.get(case)
    if answer is None or not answer.expected:
        return None
    return answer.expected


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tangle benchmark staged",
        description="Compare recorded pre-thrust and landed samples without live calls.",
        add_help=True,
    )
    parser.add_argument("--before", required=True, help="Pre-thrust token-benchmark record")
    parser.add_argument("--after", required=True, help="Landed token-benchmark record")
    parser.add_argument("--before-session", help="Pre-thrust raw Codex session JSONL")
    parser.add_argument("--after-session", help="Landed raw Codex session JSONL")
    parser.add_argument("--before-answer", help="Pre-thrust answer artifact")
    parser.add_argument("--after-answer", help="Landed answer artifact")
    parser.add_argument("--expected", help="Expected answer JSON; defaults to the case answer")
    parser.add_argument("--output", help="Write the reviewable A/B report as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the staged A/B and return the process exit code."""
    parser = _build_parser()
    try:
        options = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit as exit_signal:
        return int(exit_signal.code or 0)
    try:
        before_record = _load_json(options.before, "record")
        case = str(_metadata(before_record, options.before).get("benchmark_case"))
        expected = _expected_answer(case, options.expected)
        before = _load_sample(
            "before", options.before, options.before_session, options.before_answer, expected
        )
        after = _load_sample(
            "after", options.after, options.after_session, options.after_answer, expected
        )
        matched = _match(before, after)
        _emit(before, after, matched, options.output)
        return 0
    except _UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        _usage()
        return 2
    except _StagedError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
