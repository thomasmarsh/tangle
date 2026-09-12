"""Parameter, fallback, and disposable-cache tests for manifold reduction.

:mod:`braintree.reduction` turns cached provider embeddings into low-dimensional
coordinates for clustering and inspection. These tests drive it with a
deterministic injected reducer, so the default ``make test`` environment (which
has no ``semantic`` extra) stays offline, fast, and unmoved by numba, and the
real UMAP, t-SNE, and PCA runtime is exercised only when the extra is present.

What the fake reducer proves: the explicit parameters reach the fit unchanged,
the requested method is used when the input is large enough, a small or
degenerate input resolves to the deterministic PCA baseline instead of raising,
the sidecar cache is keyed by provider, parameters, and the exact content-hash
input set so a second identical call runs no fit at all, the sample count is
bounded, and a corrupt cache row is recomputed rather than trusted. Importing
the module and running the interactive entry point must load no heavy module.
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

from braintree import reduction
from braintree.reduction import Reduction, ReductionError, ReductionParams, coordinates

_ROOT = Path(__file__).resolve().parents[1]

# The heavy modules only the opt-in ``semantic`` extra provides. Importing this
# module and running the interactive entry point must never pull one of them in.
_HEAVY_MODULES = ("numpy", "sklearn", "umap")

# Driving a fresh interpreter is the only way to observe the real import graph:
# the help path answers without a provider, then the probe reports every heavy
# module it loaded, which must be none.
_IMPORT_PROBE = """\
import sys
from braintree import main, reduction

assert reduction.ReductionParams().method == "umap"
assert main.main(["--help"]) == 0
print("heavy:" + ",".join(name for name in sys.argv[1:] if name in sys.modules))
"""

# A deterministic stand-in for the real fit, recording every call so a test can
# prove a cache hit performs no reduction work.
RecordedFit = tuple[str, list[list[float]], ReductionParams]


class Reducer:
    """A counting reducer returning a fixed coordinate row per input vector."""

    def __init__(self) -> None:
        self.calls: list[RecordedFit] = []

    def __call__(
        self, method: str, matrix: Sequence[Sequence[float]], params: ReductionParams
    ) -> list[list[float]]:
        self.calls.append((method, [list(row) for row in matrix], params))
        return [[float(len(row) + position) for _ in range(params.n_components)]
                for position, row in enumerate(matrix)]


def _vectors(count: int, width: int = 4) -> dict[str, list[float]]:
    """Return ``count`` distinct deterministic vectors keyed by fake content hash."""
    return {
        f"hash{index:02d}": [float(index + 1) * (offset + 1) for offset in range(width)]
        for index in range(count)
    }


def _connection(tmp_path: Path, name: str = "sidecar") -> sqlite3.Connection:
    return sqlite3.connect(tmp_path / f"{name}.sqlite3")


def test_params_are_validated() -> None:
    """An unusable parameter is refused at construction, never at fit time."""
    assert ReductionParams().key() == '["umap",15,0.1,"cosine",42,2]'
    with pytest.raises(ReductionError):
        ReductionParams(method="mds")
    with pytest.raises(ReductionError):
        ReductionParams(n_neighbors=1)
    with pytest.raises(ReductionError):
        ReductionParams(min_dist=-0.1)
    with pytest.raises(ReductionError):
        ReductionParams(metric="  ")
    with pytest.raises(ReductionError):
        ReductionParams(n_components=0)
    with pytest.raises(ReductionError):
        ReductionParams(n_components=reduction.MAX_COMPONENTS + 1)


def test_fit_refuses_an_unknown_method_before_importing_anything() -> None:
    """``fit`` reports an unknown method instead of reaching a heavy import."""
    with pytest.raises(ReductionError):
        reduction.fit("mds", [[0.0, 1.0], [1.0, 0.0]], ReductionParams())


def test_coordinates_fit_the_requested_method_with_the_explicit_params(tmp_path: Path) -> None:
    """A large enough input fits the requested method with the explicit parameters."""
    reducer = Reducer()
    params = ReductionParams(method="umap", n_neighbors=5, min_dist=0.05,
                             metric="cosine", random_state=7, n_components=2)

    result = coordinates(_vectors(12), "provider-key", _connection(tmp_path), params, reducer)

    assert isinstance(result, Reduction)
    assert result.method == "umap" and not result.fallback and not result.cached
    assert len(result.coordinates) == 12
    assert all(len(row) == 2 for row in result.coordinates)
    assert result.content_hashes == tuple(sorted(_vectors(12)))
    method, matrix, used = reducer.calls[0]
    assert method == "umap" and len(matrix) == 12
    assert used == params


def test_identical_inputs_hit_the_cache_and_run_no_fit(tmp_path: Path) -> None:
    """A second identical call returns the stored coordinates without reducing."""
    connection = _connection(tmp_path)
    reducer = Reducer()
    vectors = _vectors(12)

    first = coordinates(vectors, "provider-key", connection,
                        ReductionParams(n_neighbors=5), reducer)
    second = coordinates(vectors, "provider-key", connection,
                         ReductionParams(n_neighbors=5), reducer)

    assert not first.cached and second.cached
    assert second.coordinates == first.coordinates
    assert second.method == first.method == "umap"
    assert len(reducer.calls) == 1


def test_cache_key_covers_provider_params_and_the_exact_input_set(tmp_path: Path) -> None:
    """A changed provider, parameter, or single input row misses the cache."""
    connection = _connection(tmp_path)
    reducer = Reducer()
    vectors = _vectors(12)
    params = ReductionParams(method="umap", n_neighbors=5)

    coordinates(vectors, "provider-key", connection, params, reducer)
    coordinates(vectors, "other-key", connection, params, reducer)
    coordinates(vectors, "provider-key", connection,
                ReductionParams(method="umap", n_neighbors=6), reducer)
    subset = {key: vectors[key] for key in sorted(vectors)[:-1]}
    coordinates(subset, "provider-key", connection, params, reducer)

    assert len(reducer.calls) == 4
    cached = coordinates(vectors, "provider-key", connection, params, reducer)
    assert cached.cached and len(reducer.calls) == 4


def test_small_or_degenerate_inputs_fall_back_to_pca(tmp_path: Path) -> None:
    """A vault too small for UMAP or t-SNE reduces with the linear baseline."""
    reducer = Reducer()
    params = ReductionParams(method="umap", n_neighbors=5)

    pair = coordinates(_vectors(2), "key", _connection(tmp_path, "a"), params, reducer)
    assert pair.method == "pca" and pair.fallback
    assert [len(row) for row in pair.coordinates] == [2, 2]

    boundary = coordinates(_vectors(params.n_neighbors + 1), "key",
                           _connection(tmp_path, "b"), params, reducer)
    assert boundary.method == "pca" and boundary.fallback

    tse = coordinates(_vectors(2), "key", _connection(tmp_path, "c"),
                      ReductionParams(method="tsne"), reducer)
    assert tse.method == "pca" and tse.fallback
    assert [call[0] for call in reducer.calls] == ["pca", "pca", "pca"]


def test_empty_input_returns_no_coordinates_without_fitting(tmp_path: Path) -> None:
    """An empty vault reduces to nothing rather than raising."""
    reducer = Reducer()
    connection = _connection(tmp_path)

    empty = coordinates({}, "key", connection, ReductionParams(), reducer)
    assert empty.content_hashes == () and empty.coordinates == ()
    assert reducer.calls == []
    assert coordinates({}, "key", connection, ReductionParams(), reducer).cached


def test_coordinates_are_bounded_and_capped(tmp_path: Path) -> None:
    """The sample count and output width are bounded before any fit runs."""
    reducer = Reducer()
    vectors = _vectors(reduction.MAX_SAMPLES + 7)
    params = ReductionParams(n_components=reduction.MAX_COMPONENTS, n_neighbors=5)

    result = coordinates(vectors, "key", _connection(tmp_path), params, reducer)

    assert len(result.coordinates) == reduction.MAX_SAMPLES
    assert len(result.content_hashes) == reduction.MAX_SAMPLES
    assert result.content_hashes[0] == "hash00"
    assert all(len(row) == reduction.MAX_COMPONENTS for row in result.coordinates)
    assert reducer.calls[0][2].n_components == reduction.MAX_COMPONENTS


def test_ragged_or_empty_vectors_are_refused(tmp_path: Path) -> None:
    """A vector shape the provider seam cannot have produced is refused."""
    reducer = Reducer()
    with pytest.raises(ReductionError):
        coordinates({"a": [1.0, 2.0], "b": [1.0]}, "key", _connection(tmp_path), reducer=reducer)
    with pytest.raises(ReductionError):
        coordinates({"a": []}, "key", _connection(tmp_path, "b"), reducer=reducer)


def test_a_corrupt_cache_row_is_recomputed(tmp_path: Path) -> None:
    """A disposable row that cannot hold coordinates is refitted, not trusted."""
    reducer = Reducer()
    connection = _connection(tmp_path)
    vectors = _vectors(12)
    params = ReductionParams(n_neighbors=5)

    coordinates(vectors, "key", connection, params, reducer)
    connection.execute("UPDATE reduction_cache SET coordinates = 'nonsense'")
    recomputed = coordinates(vectors, "key", connection, params, reducer)
    assert not recomputed.cached and len(reducer.calls) == 2

    connection.execute("UPDATE reduction_cache SET coordinates = '[]'")
    short = coordinates(vectors, "key", connection, params, reducer)
    assert not short.cached and len(reducer.calls) == 3

    connection.execute(
        "UPDATE reduction_cache SET method = 'umap', coordinates = ?",
        ('[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]',),
    )
    assert len(coordinates(vectors, "key", connection, params, reducer).coordinates) == 12


def test_importing_and_running_the_entry_point_loads_no_heavy_module() -> None:
    """A plain install must not import numpy, scikit-learn, or umap-learn."""
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
    for module in _HEAVY_MODULES:
        pytest.importorskip(module)


def _blobs(count: int = 12, width: int = 8) -> dict[str, list[float]]:
    """Return two well-separated deterministic Gaussian blobs of ``width`` dimensions."""
    generator = random.Random(11)
    vectors: dict[str, list[float]] = {}
    for index in range(count * 2):
        center = 3.0 if index < count else -3.0
        vectors[f"hash{index:02d}"] = [
            center + generator.gauss(0.0, 0.3) for _ in range(width)
        ]
    return vectors


def test_real_umap_is_seed_stable_and_small_inputs_use_pca(tmp_path: Path) -> None:
    """The shipped runtime returns seeded coordinates and never fails on a tiny vault."""
    _require_extra()
    vectors = _blobs()
    params = ReductionParams(method="umap", n_neighbors=8, min_dist=0.05,
                             metric="cosine", random_state=17, n_components=2)

    first = coordinates(vectors, "key", _connection(tmp_path, "a"), params)
    second = coordinates(vectors, "key", _connection(tmp_path, "b"), params)

    assert first.method == second.method == "umap"
    assert len(first.coordinates) == 24
    assert all(len(row) == 2 for row in first.coordinates)
    assert first.coordinates == second.coordinates

    pair = coordinates({key: vectors[key] for key in ("hash00", "hash12")}, "key",
                       _connection(tmp_path, "c"), params)
    assert pair.method == "pca" and pair.fallback
    assert [len(row) for row in pair.coordinates] == [2, 2]
