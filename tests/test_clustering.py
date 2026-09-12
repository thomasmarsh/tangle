"""Parameter, stability, and label tests for advisory density clustering.

:mod:`braintree.clustering` clusters the raw provider vectors and the reduced
UMAP coordinates, reports noise and outliers separately, and labels each cluster
from one of its members. These tests drive it with deterministic stand-in
clusterer and reducer functions, so the default ``make test`` environment (which
has no ``semantic`` extra) stays offline, fast, and unmoved by numba, while the
real HDBSCAN and UMAP runtime is exercised only when the extra is present.

What the stand-ins prove: both spaces are clustered, the more stable space is
chosen and a tie prefers the raw vectors, a cluster's representative is its
centroid-nearest member and its route is the one its members share, HDBSCAN's
``-1`` is noise and is never attached to a cluster, outliers are reported
separately, the density parameters scale with the vault, the sample count is
bounded, a refused reduction drops only the reduced space, and an empty
embedding set is an explicit unavailable result rather than an exception.
Importing the module and running the interactive entry point must load no heavy
module.
"""

from __future__ import annotations

import os
import random
import sqlite3
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from braintree import clustering, reduction
from braintree.clustering import (
    ClusterError,
    ClusterParams,
    NodeFacts,
    clusters,
    parameters,
)

_ROOT = Path(__file__).resolve().parents[1]

# The heavy modules only the opt-in ``semantic`` extra provides. Importing this
# module and running the interactive entry point must never pull one of them in.
_HEAVY_MODULES = ("numpy", "sklearn", "umap", "hdbscan")

# Driving a fresh interpreter is the only way to observe the real import graph:
# the help path answers with no provider, then the probe reports every heavy
# module it loaded, which must be none.
_IMPORT_PROBE = """\
import sys
from braintree import clustering, main

assert clustering.ClusterParams().seeds == (17, 29, 43)
assert main.main(["--help"]) == 0
print("heavy:" + ",".join(name for name in sys.argv[1:] if name in sys.modules))
"""


class RowsClusterer:
    """A deterministic, row-wise stand-in for HDBSCAN.

    A row whose first coordinate falls inside the noise band is ``-1``, a
    positive row is cluster ``0`` and a negative row is cluster ``1``; the score
    clears ``outlier_threshold`` only for the planted far row. Being row-wise,
    its labelings agree perfectly across subsamples, which is what the label and
    noise tests need.
    """

    def __init__(self, band: float = 0.5, far: float = 100.0) -> None:
        self.band = band
        self.far = far
        self.calls: list[int] = []

    def __call__(
        self, matrix: Sequence[Sequence[float]], params: ClusterParams
    ) -> tuple[list[int], list[float]]:
        self.calls.append(len(matrix))
        labels: list[int] = []
        scores: list[float] = []
        for row in matrix:
            first = float(row[0])
            if abs(first) < self.band:
                labels.append(-1)
                scores.append(0.0)
            else:
                labels.append(0 if first > 0 else 1)
                scores.append(1.0 if abs(first) >= self.far else 0.0)
        return labels, scores


class MeanSplitClusterer:
    """Split rows at the sample mean of their first coordinate.

    The mean moves with the sample, so subsample labelings disagree and a space
    scores below one; a fixture that snaps each row to one of two poles is
    perfectly stable, which is what the selection test compares.
    """

    def __init__(self, band: float = 0.05) -> None:
        self.band = band

    def __call__(
        self, matrix: Sequence[Sequence[float]], params: ClusterParams
    ) -> tuple[list[int], list[float]]:
        values = [float(row[0]) for row in matrix]
        if not values:
            return [], []
        mean = sum(values) / len(values)
        labels = [
            -1 if abs(value - mean) < self.band else (0 if value < mean else 1)
            for value in values
        ]
        return labels, [0.0] * len(values)


class IdentityReducer:
    """A stand-in reduction returning the input's first two coordinates."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(
        self,
        method: str,
        matrix: Sequence[Sequence[float]],
        params: reduction.ReductionParams,
    ) -> list[list[float]]:
        self.calls += 1
        return [[float(row[0]), float(row[1])] for row in matrix]


class PolarReducer:
    """A stand-in reduction snapping each row to one of two poles on the first axis."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(
        self,
        method: str,
        matrix: Sequence[Sequence[float]],
        params: reduction.ReductionParams,
    ) -> list[list[float]]:
        self.calls += 1
        return [[3.0 if float(row[0]) >= 0 else -3.0, 0.0] for row in matrix]


class RefusingReducer:
    """A reducer that reports the same refusal the real seam reports."""

    def __call__(
        self,
        method: str,
        matrix: Sequence[Sequence[float]],
        params: reduction.ReductionParams,
    ) -> list[list[float]]:
        raise reduction.ReductionError("refused in a test")


def _connection(tmp_path: Path, name: str = "sidecar") -> sqlite3.Connection:
    return sqlite3.connect(tmp_path / f"{name}.sqlite3")


def _continuum(count: int) -> dict[str, list[float]]:
    """Return ``count`` vectors spread along the first axis with no pole gap."""
    return {
        f"h{index:02d}": [float(index) - (count - 1) / 2, float(index)]
        for index in range(count)
    }


def _two_poles(count: int = 12) -> dict[str, list[float]]:
    """Return two well-separated sign groups of ``count`` vectors each."""
    vectors: dict[str, list[float]] = {}
    for index in range(count * 2):
        first = -3.0 if index < count else 3.0
        vectors[f"h{index:02d}"] = [first, float(index)]
    return vectors


def test_parameters_scale_with_the_vault_and_cap(tmp_path: Path) -> None:
    """The density parameters follow the documented vault-size rule."""
    assert parameters(2).min_cluster_size == clustering._MIN_CLUSTER_SIZE
    assert parameters(24).min_cluster_size == 5
    assert parameters(118).min_cluster_size == 6
    assert parameters(10_000).min_cluster_size == clustering._MAX_MIN_CLUSTER_SIZE
    assert parameters(24).min_samples == max(1, round(5 / 3))
    explicit = ClusterParams(min_cluster_size=9, min_samples=4)
    assert parameters(118, explicit) == explicit
    assert parameters(24, ClusterParams(min_cluster_size=9)).min_samples == 3


def test_params_are_validated() -> None:
    """An unusable parameter is refused at construction, never at fit time."""
    assert ClusterParams().seeds == (17, 29, 43)
    for invalid in (
        {"metric": "  "},
        {"min_cluster_size": -1},
        {"min_samples": -1},
        {"seeds": ()},
        {"seeds": (1, 2, 3, 4, 5, 6, 7, 8, 9)},
        {"subsamples": -1},
        {"subsamples": 9},
        {"subsample_fraction": 0},
        {"subsample_fraction": 1.5},
        {"outlier_threshold": 1.5},
        {"cluster_selection_method": "best"},
    ):
        with pytest.raises(ClusterError):
            ClusterParams(**invalid)


def _single_cluster_fixture() -> tuple[dict[str, list[float]], dict[str, NodeFacts]]:
    """One signed group whose central member is deterministic, plus one noise row."""
    vectors = {
        f"h{index}": [1.0, float(second)]
        for index, second in enumerate((0.0, 1.0, 2.0, 3.0, 100.0))
    }
    vectors["noise"] = [0.0, 0.0]
    nodes = {key: NodeFacts(node_id=key.upper(), route="IDX-ONE") for key in vectors}
    return vectors, nodes


def test_two_cluster_vault_is_labeled_from_members_and_shared_routes(tmp_path: Path) -> None:
    """A clean two-cluster vault yields two clusters and no noise."""
    vectors = _two_poles()
    nodes = {
        key: NodeFacts(node_id=key.upper(), route="IDX-NEG" if index < 12 else "IDX-POS")
        for index, key in enumerate(sorted(vectors))
    }

    result = clusters(
        vectors, "key", _connection(tmp_path), nodes, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    assert result.available and result.space == "raw"
    assert len(result.clusters) == 2
    assert result.noise == ()
    assert {cluster.route for cluster in result.clusters} == {"IDX-NEG", "IDX-POS"}
    assert all(cluster.members for cluster in result.clusters)
    assert sorted(member for cluster in result.clusters for member in cluster.members) == sorted(
        node.node_id for node in nodes.values()
    )
    for cluster in result.clusters:
        assert cluster.label == f"{cluster.representative}@{cluster.route}"

    # A tie between the identical spaces prefers the raw vectors.
    assert [evidence.space for evidence in result.stability] == ["raw", "reduced"]
    assert all(evidence.ari == 1.0 for evidence in result.stability)


def test_single_cluster_vault_uses_the_centroid_nearest_member(tmp_path: Path) -> None:
    """One group is one cluster, labeled from its centroid-nearest member and route."""
    vectors, nodes = _single_cluster_fixture()

    result = clusters(
        vectors, "key", _connection(tmp_path), nodes, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.route == "IDX-ONE"
    assert cluster.representative == "H3"
    assert cluster.label == "H3@IDX-ONE"
    assert set(cluster.members) == {"H0", "H1", "H2", "H3", "H4"}
    assert result.noise == ("NOISE",)


def test_noise_is_explicit_and_never_attached_to_a_cluster(tmp_path: Path) -> None:
    """A ``-1`` member is reported as noise and appears in no cluster."""
    vectors, nodes = _single_cluster_fixture()

    result = clusters(
        vectors, "key", _connection(tmp_path), nodes, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    attached = {member for cluster in result.clusters for member in cluster.members}
    assert "NOISE" not in attached
    assert {member.node_id for member in result.members if member.cluster == -1} == {"NOISE"}


def test_outliers_are_reported_separately_from_clusters(tmp_path: Path) -> None:
    """A clustered member can also be an outlier; it stays in its cluster."""
    vectors = {"a": [1.0, 0.0], "b": [1.0, 1.0], "far": [200.0, 0.0]}
    nodes = {key: NodeFacts(node_id=key.upper(), route="IDX-ONE") for key in vectors}

    result = clusters(
        vectors, "key", _connection(tmp_path), nodes, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    assert result.outliers == ("FAR",)
    assert "FAR" in result.clusters[0].members
    assert [member.outlier_score for member in result.members if member.node_id == "FAR"] == [1.0]


def test_tiny_vault_is_all_explicit_noise(tmp_path: Path) -> None:
    """A vault smaller than a cluster is reported as noise, never as a cluster."""
    vectors = {"a": [0.0, 0.0], "b": [0.1, 0.0]}

    result = clusters(
        vectors, "key", _connection(tmp_path), None, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    assert result.available
    assert result.clusters == ()
    assert result.noise == ("a", "b")
    assert all(member.cluster == -1 for member in result.members)


def test_no_embeddings_returns_an_explicit_unavailable_result(tmp_path: Path) -> None:
    """An empty embedding set is capability absent, not an exception."""
    result = clusters(
        {}, "key", _connection(tmp_path), None, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    assert not result.available and result.reason == "no embeddings"
    assert result.members == () and result.clusters == () and result.stability == ()


def test_missing_node_facts_fall_back_to_the_content_hash(tmp_path: Path) -> None:
    """Without caller facts the content hash is the member id and there is no route."""
    result = clusters(
        _two_poles(), "key", _connection(tmp_path), None, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    assert all(member.route == "" for member in result.members)
    assert all(cluster.route == "" for cluster in result.clusters)
    assert {member.node_id for member in result.members} == set(_two_poles())


def test_every_seed_and_subsample_runs_and_the_more_stable_space_wins(tmp_path: Path) -> None:
    """Both spaces cluster every run, and the higher stability selects the space."""
    params = ClusterParams(seeds=(17, 29), subsamples=2)
    result = clusters(
        _continuum(24), "key", _connection(tmp_path), None, params,
        reducer=PolarReducer(), clusterer=MeanSplitClusterer(),
    )

    assert result.space == "reduced"
    assert len(result.clusters) == 2
    stability = {evidence.space: evidence for evidence in result.stability}
    assert set(stability) == {"raw", "reduced"}
    assert stability["reduced"].ari == 1.0
    assert stability["raw"].ari < stability["reduced"].ari
    # One canonical full run plus one run per seed and subsample.
    assert stability["raw"].runs == 1 + len(params.seeds) * params.subsamples


def test_a_refused_reduction_drops_only_the_reduced_space(tmp_path: Path) -> None:
    """A reduction the seam refuses still yields the advisory raw clustering."""
    result = clusters(
        _two_poles(), "key", _connection(tmp_path), None, ClusterParams(),
        reducer=RefusingReducer(), clusterer=RowsClusterer(),
    )

    assert result.available and result.space == "raw"
    assert [evidence.space for evidence in result.stability] == ["raw"]
    assert len(result.clusters) == 2


def test_identical_input_is_deterministic(tmp_path: Path) -> None:
    """Two calls over the same input return the same labels and evidence."""
    params = ClusterParams(seeds=(17, 29), subsamples=2)
    vectors = _continuum(24)
    first = clusters(
        vectors, "key", _connection(tmp_path, "a"), None, params,
        reducer=PolarReducer(), clusterer=MeanSplitClusterer(),
    )
    second = clusters(
        vectors, "key", _connection(tmp_path, "b"), None, params,
        reducer=PolarReducer(), clusterer=MeanSplitClusterer(),
    )

    assert first.space == second.space
    assert first.clusters == second.clusters
    assert first.members == second.members
    assert first.stability == second.stability


def test_the_sample_count_is_bounded(tmp_path: Path) -> None:
    """More than :data:`MAX_SAMPLES` nodes are truncated in sorted hash order."""
    vectors = {f"h{index:04d}": [3.0 if index % 2 else -3.0, float(index)] for index in range(600)}

    result = clusters(
        vectors, "key", _connection(tmp_path), None, ClusterParams(),
        reducer=IdentityReducer(), clusterer=RowsClusterer(),
    )

    ids = {member.node_id for member in result.members}
    assert len(result.members) == clustering.MAX_SAMPLES
    assert ids == {f"h{index:04d}" for index in range(clustering.MAX_SAMPLES)}
    assert sum(len(cluster.members) for cluster in result.clusters) + len(result.noise) == (
        clustering.MAX_SAMPLES
    )


def test_ragged_or_empty_vectors_are_refused(tmp_path: Path) -> None:
    """A vector shape the provider seam cannot have produced is refused."""
    with pytest.raises(ClusterError):
        clusters(
            {"a": [1.0, 2.0], "b": [1.0]}, "key", _connection(tmp_path), None, ClusterParams(),
            reducer=IdentityReducer(), clusterer=RowsClusterer(),
        )
    with pytest.raises(ClusterError):
        clusters(
            {"a": []}, "key", _connection(tmp_path, "b"), None, ClusterParams(),
            reducer=IdentityReducer(), clusterer=RowsClusterer(),
        )


def test_importing_and_running_the_entry_point_loads_no_heavy_module() -> None:
    """A plain install must not import numpy, scikit-learn, umap, or hdbscan."""
    env = os.environ.copy()
    env.pop("BT_SEMANTIC_PROVIDER", None)
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_PROBE, *_HEAVY_MODULES],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = [line for line in result.stdout.splitlines() if line.startswith("heavy:")]
    assert report == ["heavy:"]


def _require_extra() -> None:
    """Skip a real-runtime test unless the optional semantic extra is installed."""
    for module in ("numpy", "sklearn", "umap", "hdbscan"):
        pytest.importorskip(module)


def _blobs(count: int = 12, width: int = 8) -> dict[str, list[float]]:
    """Return two well-separated deterministic Gaussian blobs of ``width`` dimensions."""
    generator = random.Random(11)
    vectors: dict[str, list[float]] = {}
    for index in range(count * 2):
        center = 3.0 if index < count else -3.0
        vectors[f"h{index:02d}"] = [center + generator.gauss(0.0, 0.3) for _ in range(width)]
    return vectors


def test_real_hdbscan_clusters_two_blobs_deterministically(tmp_path: Path) -> None:
    """The shipped runtime recovers the planted two-cluster structure twice."""
    _require_extra()
    vectors = _blobs()
    nodes = {
        key: NodeFacts(node_id=key.upper(), route="IDX-A" if index < 12 else "IDX-B")
        for index, key in enumerate(sorted(vectors))
    }

    first = clusters(vectors, "key", _connection(tmp_path, "a"), nodes, ClusterParams())
    second = clusters(vectors, "key", _connection(tmp_path, "b"), nodes, ClusterParams())

    assert first.available and first.clusters == second.clusters
    assert len(first.clusters) == 2
    assert first.noise == ()
    assert sorted(member for cluster in first.clusters for member in cluster.members) == sorted(
        node.node_id for node in nodes.values()
    )
    assert {cluster.route for cluster in first.clusters} == {"IDX-A", "IDX-B"}
    # The tiny and structureless vaults still answer explicitly.
    tiny = clusters(
        {"a": [1.0] * 8, "b": [1.0] * 8}, "key", _connection(tmp_path, "c"), None, ClusterParams()
    )
    assert tiny.clusters == () and tiny.noise == ("a", "b")
