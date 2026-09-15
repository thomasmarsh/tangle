"""Behavioral tests for the external-project registry writer.

``tangle project register`` is the write side of the durable local registry
that the generated ``views/projects.md`` page reads. These tests drive the real
command process: a registration normalizes the file and publishes the page, a
malformed registry is never clobbered, an alias is bound immutably to its UID,
and unrelated aliases and entry keys survive an update.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_PROJECT = "project-registry-test"
_PROJECT_UID = "prj-04r8b1t7n2c6m9x3q5f0hkwdza"
_OTHER_UID = "prj-14r8b1t7n2c6m9x3q5f0hkwdza"


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": _PROJECT,
        "TANGLE_NODES_DIR": str(vault),
    }


def _registry(vault: Path) -> dict[str, object]:
    document: object = json.loads((vault / "projects.json").read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return {str(key): value for key, value in document.items()}


def _write_registry(vault: Path, document: object) -> None:
    (vault / "projects.json").write_text(json.dumps(document), encoding="utf-8")


def test_register_writes_registry_and_publishes_the_view(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A registration normalizes the file and the views page reflects it."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    result = run_tangle("project", "register", "hekate", _PROJECT_UID, "--path", ".", env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'alias: "hekate"' in result.stdout
    assert f'project: "{_PROJECT_UID}"' in result.stdout
    assert 'path: "."' in result.stdout
    assert f'registry: "{vault / "projects.json"}"' in result.stdout

    assert _registry(vault) == {"projects": {"hekate": {"uid": _PROJECT_UID, "path": "."}}}
    page = (vault / "views" / "projects.md").read_text(encoding="utf-8")
    assert "## hekate" in page
    assert _PROJECT_UID in page
    assert "- local: present" in page


@pytest.mark.parametrize(
    "alias",
    ["Hekate", "", "-leading", "1leading", "with_underscore", "a" * 64],
    ids=["uppercase", "empty", "leading-hyphen", "leading-digit", "underscore", "over-63"],
)
def test_invalid_alias_is_a_usage_error_and_writes_nothing(
    tmp_path: Path, run_tangle: RunTangle, alias: str
) -> None:
    vault = tmp_path / "nodes"
    vault.mkdir()
    result = run_tangle("project", "register", alias, _PROJECT_UID, env=_env(tmp_path, vault))
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (vault / "projects.json").exists()


@pytest.mark.parametrize("uid", ["not-a-uid", "", "prj-short", "TAS-001"], ids=str)
def test_invalid_uid_is_a_usage_error_and_writes_nothing(
    tmp_path: Path, run_tangle: RunTangle, uid: str
) -> None:
    vault = tmp_path / "nodes"
    vault.mkdir()
    result = run_tangle("project", "register", "hekate", uid, env=_env(tmp_path, vault))
    assert result.returncode == 2, result.stdout + result.stderr
    assert not (vault / "projects.json").exists()


def test_missing_registry_is_created(tmp_path: Path, run_tangle: RunTangle) -> None:
    """A vault with no registry gains one on the first registration."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    assert not (vault / "projects.json").exists()

    result = run_tangle(
        "project", "register", "hekate", _PROJECT_UID, env=_env(tmp_path, vault)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _registry(vault) == {"projects": {"hekate": {"uid": _PROJECT_UID, "path": ""}}}


def test_same_alias_and_uid_updates_the_path(tmp_path: Path, run_tangle: RunTangle) -> None:
    """Re-registering a bound alias with the same UID rewrites only its path."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    env = _env(tmp_path, vault)
    assert (
        run_tangle("project", "register", "hekate", _PROJECT_UID, "--path", "old", env=env)
        .returncode
        == 0
    )

    updated = run_tangle(
        "project", "register", "hekate", _PROJECT_UID, "--path", "new", env=env
    )
    assert updated.returncode == 0, updated.stdout + updated.stderr
    assert _registry(vault) == {"projects": {"hekate": {"uid": _PROJECT_UID, "path": "new"}}}


def test_same_alias_different_uid_conflicts_and_leaves_the_file(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A bound alias is immutable, and a conflict never rewrites the registry."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    env = _env(tmp_path, vault)
    assert (
        run_tangle("project", "register", "hekate", _PROJECT_UID, env=env).returncode == 0
    )
    before = (vault / "projects.json").read_bytes()

    conflict = run_tangle("project", "register", "hekate", _OTHER_UID, env=env)
    assert conflict.returncode == 1, conflict.stdout + conflict.stderr
    assert "hekate" in conflict.stdout
    assert (vault / "projects.json").read_bytes() == before


@pytest.mark.parametrize(
    "content",
    ["{not json", "[]", '"text"', '{"projects": []}', '{"projects": 4}'],
    ids=["invalid-json", "array", "string", "projects-array", "projects-number"],
)
def test_malformed_registry_exits_one_and_is_never_clobbered(
    tmp_path: Path, run_tangle: RunTangle, content: str
) -> None:
    vault = tmp_path / "nodes"
    vault.mkdir()
    target = vault / "projects.json"
    target.write_text(content, encoding="utf-8")
    before = target.read_bytes()

    result = run_tangle(
        "project", "register", "hekate", _PROJECT_UID, env=_env(tmp_path, vault)
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert target.read_bytes() == before


def test_path_presence_is_projected(tmp_path: Path, run_tangle: RunTangle) -> None:
    """A registered local path resolves present; an unknown one renders unavailable."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    assert (
        run_tangle("project", "register", "here", _PROJECT_UID, "--path", ".", env=env)
        .returncode
        == 0
    )
    assert (
        run_tangle(
            "project", "register", "gone", _OTHER_UID, "--path", "missing-dir", env=env
        ).returncode
        == 0
    )

    page = (vault / "views" / "projects.md").read_text(encoding="utf-8")
    assert "## here" in page
    assert "## gone" in page
    assert "- local: present" in page
    assert "- local: unavailable" in page


def test_other_aliases_and_unknown_entry_keys_are_preserved(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A new registration leaves every other alias and entry key untouched."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    _write_registry(
        vault,
        {"projects": {"other": {"uid": _OTHER_UID, "path": "elsewhere", "note": "keep"}}},
    )

    result = run_tangle(
        "project", "register", "hekate", _PROJECT_UID, env=_env(tmp_path, vault)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    projects = _registry(vault)["projects"]
    assert isinstance(projects, dict)
    assert projects["other"] == {"uid": _OTHER_UID, "path": "elsewhere", "note": "keep"}
    assert projects["hekate"] == {"uid": _PROJECT_UID, "path": ""}


def test_same_uid_update_preserves_unknown_entry_keys(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """Updating a bound alias's path keeps the entry's other keys."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    _write_registry(
        vault,
        {"projects": {"hekate": {"uid": _PROJECT_UID, "path": "old", "note": "keep"}}},
    )

    result = run_tangle(
        "project", "register", "hekate", _PROJECT_UID, "--path", "new", env=_env(tmp_path, vault)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    projects = _registry(vault)["projects"]
    assert isinstance(projects, dict)
    assert projects["hekate"] == {"uid": _PROJECT_UID, "path": "new", "note": "keep"}


def test_a_top_level_alias_map_is_read_and_normalized(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """The reader accepts a top-level alias map; the writer normalizes the shape."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    _write_registry(vault, {"hekate": {"uid": _PROJECT_UID, "path": "."}})

    result = run_tangle(
        "project", "register", "newco", _OTHER_UID, env=_env(tmp_path, vault)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    document = _registry(vault)
    assert set(document) == {"projects"}
    projects = document["projects"]
    assert isinstance(projects, dict)
    assert projects["hekate"] == {"uid": _PROJECT_UID, "path": "."}
    assert projects["newco"] == {"uid": _OTHER_UID, "path": ""}


def test_path_equals_form_is_accepted(tmp_path: Path, run_tangle: RunTangle) -> None:
    """``--path=PATH`` records the same value as the spaced form."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    result = run_tangle(
        "project", "register", "hekate", _PROJECT_UID, "--path=some/dir", env=_env(tmp_path, vault)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _registry(vault) == {"projects": {"hekate": {"uid": _PROJECT_UID, "path": "some/dir"}}}


def test_extra_operands_and_missing_path_value_are_usage_errors(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A stray operand or a valueless ``--path`` is a usage error, not a write."""
    vault = tmp_path / "nodes"
    vault.mkdir()
    env = _env(tmp_path, vault)

    extra = run_tangle("project", "register", "hekate", _PROJECT_UID, "surprise", env=env)
    assert extra.returncode == 2, extra.stdout + extra.stderr
    valueless = run_tangle("project", "register", "hekate", _PROJECT_UID, "--path", env=env)
    assert valueless.returncode == 2, valueless.stdout + valueless.stderr
    missing = run_tangle("project", "register", "hekate", env=env)
    assert missing.returncode == 2, missing.stdout + missing.stderr
    assert not (vault / "projects.json").exists()
