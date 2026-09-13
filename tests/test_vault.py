"""Contract tests for ``.braintree`` vault resolution and legacy migration.

The default vault directory is ``.braintree``. A project that still holds a
legacy ``nodes/index-map.md`` vault and no ``.braintree/`` is migrated in place
by the default resolver and by ``braintree migrate``; an explicit operand or
``BT_NODES_DIR`` names its own directory and is never migrated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from braintree import cli, graph_check, vault

_INDEX = (
    "---\n"
    "updated: 2026-01-01T00:00:00Z\n"
    "summary: Route graph work.\n"
    "---\n"
    "\n"
    "# Root hubs\n"
    "\n"
    "- Indexes [[IDX-001-root]].\n"
)
_HUB = (
    "---\n"
    "context_rev: 1\n"
    "updated: 2026-01-01T00:00:00Z\n"
    "summary: Root hub.\n"
    "---\n"
)


def _legacy_vault(root: Path) -> Path:
    """Seed a minimal valid legacy ``root/nodes`` vault and return its path."""
    legacy = root / "nodes"
    (legacy / "resolved").mkdir(parents=True)
    (legacy / "index-map.md").write_text(_INDEX, encoding="utf-8")
    (legacy / "resolved" / "IDX-001-root.md").write_text(_HUB, encoding="utf-8")
    return legacy


def test_legacy_directory_qualifies_only_without_the_new_vault(tmp_path: Path) -> None:
    legacy = _legacy_vault(tmp_path)
    assert vault.legacy_directory(str(tmp_path)) == str(legacy)
    (tmp_path / vault.DIRECTORY_NAME).mkdir()
    assert vault.legacy_directory(str(tmp_path)) is None


def test_migrate_renames_and_merges_nested_reservations(tmp_path: Path) -> None:
    legacy = _legacy_vault(tmp_path)
    nested = legacy / ".braintree" / "reservations"
    nested.mkdir(parents=True)
    (nested / "TAS-001").write_text("", encoding="utf-8")

    result = vault.migrate(str(tmp_path))

    assert result is not None
    assert not legacy.exists()
    destination = tmp_path / vault.DIRECTORY_NAME
    assert (destination / "index-map.md").is_file()
    assert (destination / "reservations" / "TAS-001").is_file()
    assert not (destination / ".braintree").exists()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    _legacy_vault(tmp_path)
    assert vault.migrate(str(tmp_path)) is not None
    assert vault.migrate(str(tmp_path)) is None


def test_resolve_leaves_an_explicit_or_configured_directory_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    legacy = _legacy_vault(tmp_path)

    assert vault.resolve(str(legacy)) == str(legacy)
    assert legacy.exists()

    monkeypatch.setenv("BT_NODES_DIR", str(legacy))
    assert vault.resolve() == str(legacy)
    assert legacy.exists()


def test_resolve_migrates_the_default_legacy_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _legacy_vault(tmp_path)
    monkeypatch.delenv("BT_NODES_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    assert vault.resolve() == str(tmp_path / vault.DIRECTORY_NAME)
    assert (tmp_path / vault.DIRECTORY_NAME / "index-map.md").is_file()
    assert not (tmp_path / "nodes").exists()


def test_migrate_command_reports_both_outcomes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _legacy_vault(tmp_path)

    assert cli.main(["migrate", str(tmp_path)]) == 0
    assert 'result: "migrated"' in capsys.readouterr().out
    assert cli.main(["migrate", str(tmp_path)]) == 0
    assert 'result: "no-op"' in capsys.readouterr().out


def test_check_migrates_the_default_legacy_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _legacy_vault(tmp_path)
    monkeypatch.delenv("BT_NODES_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    assert graph_check.main([]) == 0
    assert (tmp_path / vault.DIRECTORY_NAME / "index-map.md").is_file()
    assert not (tmp_path / "nodes").exists()
