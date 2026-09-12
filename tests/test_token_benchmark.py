"""Contract tests for the typed Codex token benchmark."""

from __future__ import annotations

from pathlib import Path

import pytest

from braintree import token_benchmark

_FIXTURES = Path(__file__).parent / "fixtures"
_FAKE_CODEX = _FIXTURES / "fake-codex-mutation.py"
_SESSION = _FIXTURES / "token-usage-session.jsonl"
_COMPLETED_STREAM = _FIXTURES / "codex-stream-complete.jsonl"
_MALFORMED_STREAM = _FIXTURES / "codex-stream-reading-prefix-malformed.jsonl"
_COLD_ANSWER = _FIXTURES / "cold-resume-answer.json"


def test_protocol_is_live_call_free(capsys: pytest.CaptureFixture[str]) -> None:
    assert token_benchmark.main(["--protocol"]) == 0
    out = capsys.readouterr().out
    assert "token_benchmark{status,live_calls,baseline}: ready,0,absent" in out
    assert "historical accounting" in out


def test_check_output_schema_uses_compact_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert token_benchmark.main(["--check-output-schema", "--case", "cold-resume"]) == 0
    out = capsys.readouterr().out
    assert '"required":["frontier","next"]' in out
    assert '"$schema"' not in out


def test_composite_output_schema_shape(capsys: pytest.CaptureFixture[str]) -> None:
    assert token_benchmark.main(["--check-output-schema", "--case", "composite"]) == 0
    out = capsys.readouterr().out
    assert '"required":["frontier","current_decision","stale_dependents","orphan"]' in out
    assert '"properties":{"frontier"' in out
    assert '"current_decision":{"type":"string"}' in out


def test_check_fixture_reports_variants(capsys: pytest.CaptureFixture[str]) -> None:
    assert token_benchmark.main(["--check-fixture", "--case", "cold-resume"]) == 0
    out = capsys.readouterr().out
    assert '"fixture_version":"cold-resume-frontier-v1"' in out
    assert '"representation":"graph"' in out
    assert '"skill_sha256"' in out


def test_composite_fixture_has_expected_file_count(capsys: pytest.CaptureFixture[str]) -> None:
    assert token_benchmark.main(["--check-fixture"]) == 0
    out = capsys.readouterr().out
    assert '"files":62' in out
    assert '"fixture_version":"graph-retrieval-v3"' in out


def test_inspect_session_exposes_only_shapes(capsys: pytest.CaptureFixture[str]) -> None:
    assert token_benchmark.main(["--inspect-session", str(_SESSION)]) == 0
    out = capsys.readouterr().out
    assert '"turn_id,turn_token_usage"' in out
    assert '"session_meta"' in out
    assert '"turn_context"' in out


def test_historical_accounting_sums_final_snapshots(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        token_benchmark.main(
            [
                "--session",
                str(_SESSION),
                "--task-path",
                "/root/token-benchmark-fixture",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "historical_token_accounting{sessions,input_tokens" in out
    assert ": 1,200,20,180,50,17,250" in out
    assert '"classification":"historical-implementation-cost"' in out


def test_check_recording_accepts_a_canned_stream(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        token_benchmark.main(
            [
                "--check-recording",
                str(_COMPLETED_STREAM),
                "--answer",
                str(_COLD_ANSWER),
                "--case",
                "cold-resume",
            ]
        )
        == 0
    )
    assert "recording_check{status,live_calls}: valid,0" in capsys.readouterr().out


def test_check_recording_rejects_malformed_stream(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        token_benchmark.main(
            [
                "--check-recording",
                str(_MALFORMED_STREAM),
                "--answer",
                str(_COLD_ANSWER),
                "--case",
                "cold-resume",
            ]
        )
        == 2
    )
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("fixture", "extra"),
    [
        ("token-usage-invalid.jsonl", ["--model", "fixture-model", "--reasoning-effort", "low"]),
        ("token-usage-session.jsonl", ["--model", "wrong-model"]),
        ("token-usage-session.jsonl", ["--task-path", "/root/wrong-task"]),
        ("token-usage-no-provenance.jsonl", []),
        ("token-usage-regression.jsonl", []),
        ("token-usage-no-turn-id.jsonl", []),
    ],
)
def test_session_validation_rejects_bad_telemetry(
    fixture: str, extra: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert token_benchmark.main(["--session", str(_FIXTURES / fixture), *extra]) == 2
    assert "error:" in capsys.readouterr().err


def test_record_with_fake_codex_mutates_only_the_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BT_TOKEN_BENCHMARK_CODEX", str(_FAKE_CODEX))
    monkeypatch.setenv("BT_TOKEN_BENCHMARK_SESSIONS_DIR", str(tmp_path / "sessions"))
    assert (
        token_benchmark.main(
            [
                "--record",
                "--case",
                "routine-mutation",
                "--model",
                "fake-model",
                "--reasoning-effort",
                "medium",
                "--repetitions",
                "1",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "1,11,3,8,5,2,16,true" in out
    assert '"correctness":true' in out


def test_record_rejects_unrelated_fixture_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BT_TOKEN_BENCHMARK_CODEX", str(_FAKE_CODEX))
    monkeypatch.setenv("BT_TOKEN_BENCHMARK_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("BT_FAKE_MUTATION_EXTRA_EDIT", "1")
    assert (
        token_benchmark.main(
            [
                "--record",
                "--case",
                "routine-mutation",
                "--model",
                "fake-model",
                "--reasoning-effort",
                "medium",
                "--repetitions",
                "1",
            ]
        )
        == 2
    )
    assert "unexpected fixture path" in capsys.readouterr().err
