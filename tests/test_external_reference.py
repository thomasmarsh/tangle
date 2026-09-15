"""Behavioral tests for durable cross-project external references.

A canonical node may cite another project's node with a bare
``tangle://<prj-uid>/node/<node-id>`` URI. These tests drive the real command
process: an unregistered or unavailable target stays visible and unresolved, a
registered local vault carrying the matching project UID resolves it, no target
is ever materialized as a local node, and the generated ``projects.md`` page
projects the same state deterministically.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
import vault_helpers

from tangle import identity

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_PROJECT = "external-reference-test"
_PROJECT_UID = "prj-04r8b1t7n2c6m9x3q5f0hkwdza"
_OTHER_UID = "prj-14r8b1t7n2c6m9x3q5f0hkwdza"
_HUB = vault_helpers.deterministic_id("idx", 0)
_CONSUMER = vault_helpers.deterministic_id("tas", 1)
_TARGET = vault_helpers.deterministic_id("tas", 7)
_HUB_NAME = f"{_HUB}-root"
_LEGACY_TARGET = "TAS-777"


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": _PROJECT,
        "TANGLE_NODES_DIR": str(vault),
    }


def _uri(project_uid: str, node_id: str) -> str:
    return identity.format_external_reference(project_uid, node_id)


def _consumer_text(extra: str) -> str:
    return (
        "---\n"
        "status: active\n"
        "context_rev: 1\n"
        "updated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the root.\n"
        "next: Reconcile the root.\n"
        "---\n"
        f"\nParent [[{_HUB_NAME}]].\n"
        f"\n{extra}\n"
    )


def _seed(vault: Path, extra: str) -> None:
    """Write a resolved hub and one routed active consumer that cites ``extra``."""
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "index-map.md").write_text(
        f"# Root hubs\n\n- Indexes [[{_HUB_NAME}]]\n", encoding="utf-8"
    )
    vault_helpers.write_node(
        vault,
        _HUB,
        "root",
        "---\n"
        "status: resolved\n"
        "context_rev: 1\n"
        "updated: 2026-09-11T00:00:00Z\n"
        "summary: Root graph entry.\n"
        "---\n",
    )
    vault_helpers.write_node(vault, _CONSUMER, "consumer", _consumer_text(extra))


def _external_vault(tmp_path: Path, project_uid: str) -> Path:
    """Create a local external vault that commits ``project_uid``."""
    external = tmp_path / "external"
    external.mkdir()
    (external / identity.PROJECT_UID_FILE).write_text(project_uid + "\n", encoding="utf-8")
    return external


def test_identity_round_trips_and_rejects_non_references() -> None:
    """The grammar formats, parses, and refuses anything that is not a URI."""
    reference = identity.parse_external_reference(_uri(_OTHER_UID, _TARGET))
    assert reference == identity.Reference(_OTHER_UID, _TARGET, True)
    legacy = identity.parse_external_reference(_uri(_OTHER_UID, _LEGACY_TARGET))
    assert legacy == identity.Reference(_OTHER_UID, _LEGACY_TARGET, True)
    assert identity.parse_external_reference(_TARGET) is None
    assert identity.parse_external_reference("hekate:" + _TARGET) is None
    assert identity.parse_external_reference("tangle://prj-short/node/" + _TARGET) is None
    with pytest.raises(identity.IdentityError):
        identity.format_external_reference("not-a-uid", _TARGET)


def test_an_unregistered_reference_stays_visible_and_makes_no_node(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """An unregistered target is reported unresolved without a fake canonical node."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_OTHER_UID, _TARGET)}.")
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0

    reported = run_tangle_inproc("external", env=env)
    assert reported.returncode == 0, reported.stdout + reported.stderr
    assert 'unresolved: "1"' in reported.stdout
    assert f'"{_OTHER_UID}"' in reported.stdout
    assert f'"{_TARGET}"' in reported.stdout
    assert '"unregistered"' in reported.stdout

    checked = run_tangle_inproc("check", env=env)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    names = {path.name for path in vault_helpers.iter_nodes(vault)}
    assert not any(name.startswith(f"{_TARGET}-") for name in names)


def test_a_registered_available_project_resolves_the_reference(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A registered vault committing the matching UID resolves the reference."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_OTHER_UID, _TARGET)}.")
    env = _env(tmp_path, vault)
    external = _external_vault(tmp_path, _OTHER_UID)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert (
        run_tangle_inproc(
            "project", "register", "hekate", _OTHER_UID, "--path", str(external), env=env
        ).returncode
        == 0
    )

    reported = run_tangle_inproc("external", env=env)
    assert reported.returncode == 0, reported.stdout + reported.stderr
    assert 'unresolved: "0"' in reported.stdout
    assert '"resolved"' in reported.stdout
    assert '"hekate"' in reported.stdout


def test_a_registered_missing_projects_is_unavailable(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A registered location that is not a directory leaves the reference unresolved."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_OTHER_UID, _TARGET)}.")
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert (
        run_tangle_inproc(
            "project",
            "register",
            "gone",
            _OTHER_UID,
            "--path",
            str(tmp_path / "missing"),
            env=env,
        ).returncode
        == 0
    )

    reported = run_tangle_inproc("external", env=env)
    assert reported.returncode == 0
    assert 'unresolved: "1"' in reported.stdout
    assert '"unavailable"' in reported.stdout


def test_a_mismatched_project_identity_is_unavailable(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A local path that commits a different UID never resolves another project."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_OTHER_UID, _TARGET)}.")
    env = _env(tmp_path, vault)
    external = _external_vault(tmp_path, _PROJECT_UID)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert (
        run_tangle_inproc(
            "project", "register", "hekate", _OTHER_UID, "--path", str(external), env=env
        ).returncode
        == 0
    )

    reported = run_tangle_inproc("external", env=env)
    assert reported.returncode == 0
    assert 'unresolved: "1"' in reported.stdout
    assert '"unavailable"' in reported.stdout


def test_a_reference_to_this_project_is_local(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A URI naming this vault's own UID is reported as a local reference."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_PROJECT_UID, _TARGET)}.")
    (vault / identity.PROJECT_UID_FILE).write_text(_PROJECT_UID + "\n", encoding="utf-8")
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0

    reported = run_tangle_inproc("external", env=env)
    assert reported.returncode == 0, reported.stdout + reported.stderr
    assert '"local"' in reported.stdout
    assert 'unresolved: "1"' in reported.stdout


def test_unresolved_filter_hides_resolved_references(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """``--unresolved`` lists only the references that cannot be resolved."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_OTHER_UID, _TARGET)}.")
    env = _env(tmp_path, vault)
    external = _external_vault(tmp_path, _OTHER_UID)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert (
        run_tangle_inproc(
            "project", "register", "hekate", _OTHER_UID, "--path", str(external), env=env
        ).returncode
        == 0
    )

    filtered = run_tangle_inproc("external", "--unresolved", env=env)
    assert filtered.returncode == 0, filtered.stdout + filtered.stderr
    assert "references: 0 references" in filtered.stdout


def test_the_view_projects_reference_state_deterministically(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """The projects page lists the reference and a no-op run rewrites nothing."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to {_uri(_OTHER_UID, _TARGET)}.")
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("frontier", env=env).returncode == 0

    page = (vault / "views" / "projects.md").read_text(encoding="utf-8")
    assert "## External references" in page
    assert _uri(_OTHER_UID, _TARGET) in page
    assert "unregistered" in page
    before = (vault / "views" / "projects.md").read_bytes()

    assert run_tangle_inproc("frontier", env=env).returncode == 0
    assert (vault / "views" / "projects.md").read_bytes() == before


def test_a_quoted_reference_is_not_scanned(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A URI documented inside an inline code span is not an authored reference."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Grammar: `{_uri(_OTHER_UID, _TARGET)}`.")
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0

    reported = run_tangle_inproc("external", env=env)
    assert reported.returncode == 0
    assert 'unresolved: "0"' in reported.stdout
    assert "references: 0 references" in reported.stdout


def test_a_wikilink_external_reference_fails_check(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """The checker rejects a cross-project URI spelled as a local wikilink."""
    vault = tmp_path / "nodes"
    _seed(vault, f"Related to [[{_uri(_OTHER_UID, _TARGET)}]].")
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0

    checked = run_tangle_inproc("check", "--format", "toon", env=env)
    assert checked.returncode == 1, checked.stdout + checked.stderr
    assert "node-external-wikilink" in checked.stdout


def test_external_rejects_an_unknown_operand(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """Only ``--unresolved`` is accepted, and ``--help`` answers without a vault."""
    vault = tmp_path / "nodes"
    _seed(vault, "No reference here.")
    env = _env(tmp_path, vault)

    bogus = run_tangle_inproc("external", "--bogus", env=env)
    assert bogus.returncode == 2, bogus.stdout + bogus.stderr

    helped = run_tangle_inproc("external", "--help", env=env)
    assert helped.returncode == 0
    assert "usage: \"tangle external" in helped.stdout
