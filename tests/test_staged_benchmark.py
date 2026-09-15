"""Contract tests for the zero-live staged A/B harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tangle import main as bt_main
from tangle import staged_benchmark, token_benchmark

# Benchmark verification replays recorded samples, so it is opt-in.
pytestmark = pytest.mark.benchmark

Json = dict[str, Any]

_ZERO_MEDIAN = {
    "input_tokens": 100_000,
    "cached_input_tokens": 90_000,
    "uncached_input_tokens": 10_000,
    "output_tokens": 1_000,
    "reasoning_output_tokens": 500,
    "total_tokens": 101_000,
}
_MATCHED_METADATA: Json = {
    "fixture_version": "graph-retrieval-v3",
    "fixture_seed": "tas-020-2026-09-10",
    "benchmark_case": "composite",
    "representation": "graph",
    "scale": "small",
    "requested_model": "gpt-x",
    "requested_reasoning_effort": "low",
    "requested_codex_version": "codex-cli 0.154.0",
}


def _record(
    path: Path,
    *,
    median: Json | None = None,
    round_trips: Json | None = None,
    correctness: bool = True,
    metadata: Json | None = None,
) -> Path:
    document = {
        "protocol": "codex-session-token-v2",
        "correctness": correctness,
        "samples": [median or _ZERO_MEDIAN],
        "median": median or _ZERO_MEDIAN,
        "metadata": metadata or dict(_MATCHED_METADATA),
    }
    if round_trips is not None:
        document["round_trips"] = {
            "samples": [round_trips],
            "median": round_trips,
            "fallback": None,
        }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _session(
    path: Path,
    *,
    tool_calls: int = 0,
    shell_calls: int = 0,
    model: str = "gpt-x",
    effort: str = "low",
    cli: str = "0.154.0",
) -> Path:
    lines: list[Json] = [
        {"type": "session_meta", "payload": {"cli_version": cli, "cwd": "/fixture"}},
        {"type": "turn_context", "payload": {"cwd": "/fixture", "model": model, "effort": effort}},
    ]
    for index in range(tool_calls):
        name = "exec" if index < shell_calls else "apply_patch"
        lines.append(
            {
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": name,
                    "call_id": f"call-{index}",
                    "input": "tangle frontier",
                },
            }
        )
    if tool_calls == 0:
        lines.append({"type": "response_item", "payload": {"type": "other"}})
    lines.append(
        {
            "type": "token_usage_record",
            "payload": {
                "turn_id": "turn-a",
                "turn_token_usage": {
                    "input_tokens": 100,
                    "cached_input_tokens": 40,
                    "output_tokens": 10,
                    "reasoning_output_tokens": 2,
                    "total_tokens": 110,
                },
            },
        }
    )
    lines.append({"type": "turn.completed", "payload": {}})
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return path


def _median(**overrides: int) -> Json:
    return {**_ZERO_MEDIAN, **overrides}


def _round_trips(tool_calls: int, shell_calls: int) -> Json:
    return {"tool_calls": tool_calls, "shell_calls": shell_calls}


def test_staged_keep_when_landed_cuts_round_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(
        tmp_path / "before.json",
        median=_median(uncached_input_tokens=18_000, total_tokens=170_000),
        round_trips=_round_trips(5, 3),
    )
    after = _record(
        tmp_path / "after.json",
        median=_median(uncached_input_tokens=9_000, total_tokens=90_000),
        round_trips=_round_trips(1, 1),
    )
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 0
    out = capsys.readouterr().out
    assert "staged_ab{" in out
    assert '"decision":"keep"' in out
    assert "composite,graph,small,gpt-x,low,codex-cli 0.154.0,compared,keep" in out
    assert ",5,1,-4," in out  # tool call delta
    assert '"improved":["tool_calls","uncached_input_tokens","total_tokens"]' in out


def test_staged_revert_when_landed_regresses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(
        tmp_path / "before.json",
        median=_median(uncached_input_tokens=9_000, total_tokens=90_000),
        round_trips=_round_trips(1, 1),
    )
    after = _record(
        tmp_path / "after.json",
        median=_median(uncached_input_tokens=18_000, total_tokens=170_000),
        round_trips=_round_trips(5, 3),
    )
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 0
    out = capsys.readouterr().out
    assert '"decision":"revert"' in out
    assert '"regressed":["tool_calls","uncached_input_tokens","total_tokens"]' in out


def test_staged_revise_on_mixed_change(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(
        tmp_path / "before.json",
        median=_median(uncached_input_tokens=9_000, total_tokens=90_000),
        round_trips=_round_trips(5, 3),
    )
    after = _record(
        tmp_path / "after.json",
        median=_median(uncached_input_tokens=18_000, total_tokens=170_000),
        round_trips=_round_trips(1, 1),
    )
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 0
    out = capsys.readouterr().out
    assert '"decision":"revise"' in out
    assert '"improved":["tool_calls"]' in out


def test_staged_rejects_unmatched_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json", round_trips=_round_trips(2, 1))
    after = _record(
        tmp_path / "after.json",
        round_trips=_round_trips(1, 1),
        metadata={**_MATCHED_METADATA, "requested_model": "gpt-y"},
    )
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 1
    assert "unmatched requested_model" in capsys.readouterr().err


def test_staged_rejects_unmatched_fixture_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json", round_trips=_round_trips(2, 1))
    after = _record(
        tmp_path / "after.json",
        round_trips=_round_trips(1, 1),
        metadata={**_MATCHED_METADATA, "fixture_version": "graph-retrieval-v4"},
    )
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 1
    assert "unmatched fixture_version" in capsys.readouterr().err


def test_staged_falls_back_to_session_round_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A record that predates round-trip telemetry carries no round_trips map.
    before = _record(tmp_path / "before.json")
    after = _record(tmp_path / "after.json", round_trips=_round_trips(1, 1))
    before_session = _session(tmp_path / "before.jsonl", tool_calls=5, shell_calls=3)
    assert (
        staged_benchmark.main(
            [
                "--before",
                str(before),
                "--after",
                str(after),
                "--before-session",
                str(before_session),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert '"sources":{"before":"session","after":"record"}' in out
    assert '"comparable":true' in out


def test_staged_falls_back_to_tokens_when_no_round_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(
        tmp_path / "before.json", median=_median(uncached_input_tokens=18_000, total_tokens=170_000)
    )
    after = _record(
        tmp_path / "after.json", median=_median(uncached_input_tokens=9_000, total_tokens=90_000)
    )
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 0
    out = capsys.readouterr().out
    assert '"comparable":false' in out
    assert f'"fallback":"{staged_benchmark.FALLBACK_UNAVAILABLE}"' in out
    assert '"decision":"keep"' in out


def test_staged_regates_the_exact_answer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json", round_trips=_round_trips(2, 1))
    after = _record(tmp_path / "after.json", round_trips=_round_trips(1, 1))
    for label in ("before", "after"):
        _session(tmp_path / f"{label}.jsonl", tool_calls=2, shell_calls=1)
    expected = token_benchmark.CASES["composite"].expected
    answer = tmp_path / "answer.json"
    answer.write_text(json.dumps(expected), encoding="utf-8")
    arguments = [
        "--before",
        str(before),
        "--after",
        str(after),
        "--before-session",
        str(tmp_path / "before.jsonl"),
        "--after-session",
        str(tmp_path / "after.jsonl"),
        "--before-answer",
        str(answer),
        "--after-answer",
        str(answer),
    ]
    assert staged_benchmark.main(arguments) == 0

    answer.write_text(json.dumps({**expected, "frontier": "WRONG"}), encoding="utf-8")
    assert staged_benchmark.main(arguments) == 1
    assert "exact-value gate failed" in capsys.readouterr().err


def test_staged_rejects_unobserved_session_telemetry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json")
    after = _record(tmp_path / "after.json")
    wrong = _session(tmp_path / "before.jsonl", tool_calls=1, model="different-model")
    assert (
        staged_benchmark.main(
            ["--before", str(before), "--after", str(after), "--before-session", str(wrong)]
        )
        == 1
    )
    assert "does not match record requested_model" in capsys.readouterr().err


def test_staged_requires_a_session_to_gate_an_answer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json")
    after = _record(tmp_path / "after.json")
    answer = tmp_path / "answer.json"
    answer.write_text("{}", encoding="utf-8")
    assert (
        staged_benchmark.main(
            ["--before", str(before), "--after", str(after), "--before-answer", str(answer)]
        )
        == 2
    )
    assert "error:" in capsys.readouterr().err


def test_staged_rejects_a_record_that_failed_its_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json", correctness=False)
    after = _record(tmp_path / "after.json", round_trips=_round_trips(1, 1))
    assert staged_benchmark.main(["--before", str(before), "--after", str(after)]) == 1
    assert "did not pass its exact-value gate" in capsys.readouterr().err


def test_staged_writes_a_reviewable_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _record(tmp_path / "before.json", round_trips=_round_trips(3, 2))
    after = _record(tmp_path / "after.json", round_trips=_round_trips(1, 1))
    output = tmp_path / "staged-ab.json"
    assert (
        staged_benchmark.main(
            ["--before", str(before), "--after", str(after), "--output", str(output)]
        )
        == 0
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["protocol"] == "staged-ab-v1"
    assert report["decision"] == "keep"
    assert report["round_trips"]["before"] == {"tool_calls": 3, "shell_calls": 2}
    assert report["tokens"]["delta"]["uncached_input_tokens"] == 0
    capsys.readouterr()


def test_benchmark_staged_is_dispatched(capsys: pytest.CaptureFixture[str]) -> None:
    assert bt_main.main(["--help"]) == 0
    assert "benchmark token|behavioral|storage|verbs|staged|embedding" in (
        capsys.readouterr().out
    )
