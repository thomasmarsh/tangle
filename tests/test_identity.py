"""Tests for immutable project and lowercase node identity primitives."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from braintree import identity

RunBt = Callable[..., subprocess.CompletedProcess[str]]


def test_generated_ids_have_the_exact_canonical_128_bit_shape() -> None:
    project = identity.generate_project_uid()
    node = identity.generate_node_id("TAS")
    assert re.fullmatch(r"prj-[0-7][0-9a-hjkmnp-tv-z]{25}", project)
    assert re.fullmatch(r"tas-[0-7][0-9a-hjkmnp-tv-z]{25}", node)
    assert identity.normalize_node_id(node.upper()) == node
    assert identity.normalize_node_id("TAS-203") == "TAS-203"


@pytest.mark.parametrize("value", ["tas-01i", "tas-8" + "0" * 25, "tas-01" + "o" * 24])
def test_noncanonical_node_payloads_are_rejected(value: str) -> None:
    with pytest.raises(identity.IdentityError):
        identity.normalize_node_id(value)


def test_project_uid_is_committed_once_and_shared_by_a_clone(tmp_path: Path) -> None:
    vault = tmp_path / ".braintree"
    vault.mkdir()
    first = identity.ensure_project_uid(vault)
    assert identity.ensure_project_uid(vault) == first
    assert (vault / "project-id").read_text(encoding="utf-8") == first + "\n"


def test_location_reports_committed_project_uid(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / ".braintree"
    vault.mkdir()
    project = identity.ensure_project_uid(vault)
    result = run_bt(
        "location",
        env={
            "BT_NODES_DIR": str(vault),
            "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
            "BT_PROJECT_ID": "sidecar-test",
        },
    )
    assert result.returncode == 0
    assert f'project_uid: "{project}"' in result.stdout


def test_qualified_references_expand_aliases_to_immutable_authority() -> None:
    local = "prj-0123456789abcdefghjkmnpqrs"
    remote = "prj-1123456789abcdefghjkmnpqrs"
    node = "tas-0123456789abcdefghjkmnpqrs"
    reference = identity.parse_reference(f"hekate:{node.upper()}", local, {"hekate": remote})
    assert reference == identity.Reference(remote, node, True)
    with pytest.raises(identity.IdentityError, match="unknown project alias"):
        identity.parse_reference(f"other:{node}", local, {"hekate": remote})


def test_abbreviations_lengthen_only_for_same_type_collisions() -> None:
    first = "tas-0123456789abcdefghjkmnpqrs"
    second = "tas-01234567z9abcdefghjkmnpqrs"
    other_type = "def-0123456789abcdefghjkmnpqrs"
    abbreviated = identity.abbreviate([first, second, other_type])
    assert abbreviated[first] == "tas-012345678..."
    assert abbreviated[second] == "tas-01234567z..."
    assert abbreviated[other_type] == "def-01234567..."
