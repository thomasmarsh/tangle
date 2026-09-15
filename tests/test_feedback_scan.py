"""Behavioral tests for the read-only ``feedback-scan`` collector.

The scan is exercised against fixture vaults so it is proven to return only
``FBK`` feedback, to bound its output, and to state a zero result explicitly
without writing to the scanned vault.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tangle import feedback_scan


def _write(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _vault(root: Path, *, feedback: bool, feedback_id: str = "FBK-001-allocation-friction") -> Path:
    nodes = root / "nodes"
    (nodes / "proposed").mkdir(parents=True, exist_ok=True)
    (nodes / "active").mkdir(exist_ok=True)
    if feedback:
        _write(
            nodes / "proposed" / f"{feedback_id}.md",
            "---",
            "context_rev: 1",
            "updated: 2026-09-12T00:00:00Z",
            "summary: Allocation collided with nodes on disk.",
            "tangle_revision: 0.4.0+g1b58d57",
            "---",
            "",
            "Area [[IDX-001-root]].",
            "",
            "# Feedback",
            "",
            "Attempted: Ran tangle allocate after a reindex.",
            "Friction: The allocated id already existed on disk.",
            "Improvement: Seed allocation from the Markdown maximum.",
        )
    _write(
        nodes / "active" / "TAS-001-unrelated.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-12T00:00:00Z",
        "summary: Unrelated task.",
        "next: Do work.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    return root


def test_scan_reports_feedback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _vault(tmp_path / "consumer", feedback=True)
    assert feedback_scan.main([str(vault)]) == 0
    out = capsys.readouterr().out
    assert "feedback[1]{vault,id,status,revision,summary}:" in out
    assert "FBK-001-allocation-friction" in out
    assert "proposed" in out
    assert "0.4.0+g1b58d57" in out
    assert "Allocation collided with nodes on disk." in out
    assert "TAS-001-unrelated" not in out


def test_scan_reports_zero_explicitly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _vault(tmp_path / "quiet", feedback=False)
    assert feedback_scan.main([str(vault)]) == 0
    assert capsys.readouterr().out.strip() == "feedback: 0 nodes"


def test_scan_accepts_a_nodes_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _vault(tmp_path / "consumer", feedback=True)
    assert feedback_scan.main([str(vault / "nodes")]) == 0
    assert "feedback[1]{" in capsys.readouterr().out


_CANONICAL_FBK = "fbk-01k5v6m3x8f2q7c9d4hn8w2pza-allocation-friction"


def _stationary_vault(root: Path) -> Path:
    """Seed a stationary canonical vault with one lowercase fbk node."""
    nodes = root / ".tangle"
    directory = nodes / "canonical" / _CANONICAL_FBK[-2:]
    directory.mkdir(parents=True, exist_ok=True)
    _write(
        directory / f"{_CANONICAL_FBK}.md",
        "---",
        "status: proposed",
        "context_rev: 1",
        "updated: 2026-09-12T00:00:00Z",
        "summary: Canonical feedback node.",
        "tangle_revision: 0.4.0+g1b58d57",
        "---",
        "",
        "Area [[IDX-001-root]].",
        "",
        "# Feedback",
        "",
        "Attempted: A canonical capture.",
        "Friction: Discovery missed lowercase ids.",
        "Improvement: Match both spellings.",
    )
    return root


def test_scan_reads_canonical_lowercase_feedback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _stationary_vault(tmp_path / "canonical")
    assert feedback_scan.main([str(vault)]) == 0
    out = capsys.readouterr().out
    assert "feedback[1]{vault,id,status,revision,summary}:" in out
    assert _CANONICAL_FBK in out
    assert "proposed" in out
    assert "Canonical feedback node." in out


def test_scan_reads_mixed_legacy_and_canonical_feedback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _stationary_vault(tmp_path / "mixed")
    legacy = vault / ".tangle" / "proposed"
    legacy.mkdir(parents=True, exist_ok=True)
    _write(
        legacy / "FBK-001-one.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-12T00:00:00Z",
        "summary: Legacy feedback node.",
        "tangle_revision: 0.4.0+g1b58d57",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    assert feedback_scan.main([str(vault)]) == 0
    out = capsys.readouterr().out
    assert "feedback[2]{" in out
    assert "FBK-001-one" in out
    assert _CANONICAL_FBK in out


def test_scan_collects_multiple_vaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = _vault(tmp_path / "first", feedback=True, feedback_id="FBK-001-one")
    second = _vault(tmp_path / "second", feedback=True, feedback_id="FBK-002-two")
    assert feedback_scan.main([str(first), str(second)]) == 0
    out = capsys.readouterr().out
    assert "feedback[2]{" in out
    assert "FBK-001-one" in out
    assert "FBK-002-two" in out


def test_scan_limit_bounds_results(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = _vault(tmp_path / "first", feedback=True, feedback_id="FBK-001-one")
    second = _vault(tmp_path / "second", feedback=True, feedback_id="FBK-002-two")
    assert feedback_scan.main(["--limit", "1", str(first), str(second)]) == 0
    out = capsys.readouterr().out
    assert "feedback[1]{" in out
    assert "FBK-001-one" in out
    assert "FBK-002-two" not in out


def test_scan_does_not_write_to_the_vault(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _vault(tmp_path / "consumer", feedback=True)
    node = vault / "nodes" / "proposed" / "FBK-001-allocation-friction.md"
    before = node.read_text(encoding="utf-8")
    assert feedback_scan.main([str(vault)]) == 0
    capsys.readouterr()
    assert node.read_text(encoding="utf-8") == before


def test_scan_missing_vault_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert feedback_scan.main([str(tmp_path / "absent")]) == 1
    assert "nodes directory does not exist" in capsys.readouterr().out


def test_scan_requires_a_vault(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_scan.main([]) == 2
    assert "tangle feedback scan requires at least one vault" in capsys.readouterr().out


def test_scan_rejects_bad_limit(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_scan.main(["--limit", "0", "vault"]) == 2
    assert "--limit must be a positive integer" in capsys.readouterr().out


def test_scan_unknown_option_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_scan.main(["--bogus"]) == 2
    assert "unknown option: --bogus" in capsys.readouterr().out


def test_scan_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_scan.main(["--help"]) == 0
    assert feedback_scan.main(["-h"]) == 0
    assert "usage: tangle feedback scan" in capsys.readouterr().out
