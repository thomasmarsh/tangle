"""Deterministic, advisory manifold reduction of cached embeddings.

The optional semantic layer embeds node text through the provider seam in
:mod:`tangle.semantic`, cached in the disposable sidecar by content hash.
This module is the next derived layer: it turns those vectors into
low-dimensional coordinates for density clustering and human inspection. UMAP is
the primary embedding, PCA the linear baseline, and t-SNE the comparison, and
nothing here is required by ``similar`` or any interactive verb: the caller
decides when to reduce, and the whole layer is advisory and derived under the
capability-boundary decision.

The three methods preserve different structure, which is why all three ship:

- **PCA** is linear, model-free, and deterministic. It keeps the directions of
  greatest variance, so it preserves global spread but flattens curved
  structure. It has no sample-count requirement, which makes it the fallback.
- **UMAP** preserves local neighborhood structure on a learned manifold. It is
  approximate and stochastic, so every parameter that changes the layout is
  explicit (``n_neighbors``, ``min_dist``, ``metric``) and ``random_state`` is
  fixed, and it needs strictly more samples than ``n_neighbors + 1`` to build
  its graph at all.
- **t-SNE** preserves local neighborhoods too, but optimizes a different
  divergence, is much slower, and needs ``perplexity`` below the sample count,
  so it is the comparison rather than the default.

The heavy stack (numpy, scikit-learn, umap-learn) is imported lazily inside the
fit functions, mirroring :mod:`tangle.provider`, so importing this module on
the interactive path loads nothing and a plain install keeps
``dependencies = []``. Reduced coordinates live in the disposable sidecar keyed
by provider identity, the explicit parameters, and the content-hash set they
were computed from, so a re-run over unchanged inputs recomputes nothing.

The output is bounded and advisory: at most :data:`_MAX_COMPONENTS` dimensions,
at most :data:`_MAX_SAMPLES` samples, and a small or degenerate input falls
back to PCA deterministically instead of raising.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256

__all__ = [
    "MAX_COMPONENTS",
    "MAX_SAMPLES",
    "METHODS",
    "Reduction",
    "ReductionError",
    "ReductionParams",
    "coordinates",
    "fit",
]

METHODS = ("umap", "pca", "tsne")
# Bounded output: a coordinate set wider than three dimensions is neither
# plottable nor useful to a downstream clusterer, and the cap keeps a caller
# from asking a stochastic fit for an unbounded layout.
MAX_COMPONENTS = 3
MAX_SAMPLES = 512

# The reduction cache is disposable derived state, like ``semantic_cache``: the
# primary key is the provider identity, the canonical parameter string, and the
# hash of the exact content-hash input set, so identical inputs hit one row and
# any changed input, parameter, or provider misses. The table is created
# additively alongside the vector cache and never constrains Markdown.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS reduction_cache (
  provider TEXT NOT NULL, params TEXT NOT NULL, inputs_hash TEXT NOT NULL,
  method TEXT NOT NULL, coordinates TEXT NOT NULL,
  PRIMARY KEY(provider, params, inputs_hash)
);
"""

# One reduced coordinate vector per input vector, in input order.
Reducer = Callable[[str, Sequence[Sequence[float]], "ReductionParams"], list[list[float]]]
Matrix = Sequence[Sequence[float]]


class ReductionError(Exception):
    """Invalid parameters or an unusable fit result, reported to the caller."""


@dataclass(frozen=True)
class ReductionParams:
    """The explicit, seed-fixed parameters of one reduction.

    ``n_neighbors`` and ``min_dist`` configure UMAP's local structure, ``metric``
    is the input-space distance, ``random_state`` seeds the stochastic layouts,
    and ``n_components`` is the requested output width. PCA ignores
    ``n_neighbors`` and ``min_dist``; t-SNE ignores ``n_neighbors`` and derives
    its own perplexity from the sample count.
    """

    method: str = "umap"
    n_neighbors: int = 15
    min_dist: float = 0.1
    metric: str = "cosine"
    random_state: int = 42
    n_components: int = 2

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise ReductionError(f"unknown method: {self.method}")
        if self.n_neighbors < 2:
            raise ReductionError("n_neighbors must be at least 2")
        if self.min_dist < 0:
            raise ReductionError("min_dist must not be negative")
        if not self.metric.strip():
            raise ReductionError("metric must be a non-empty distance name")
        if not 1 <= self.n_components <= MAX_COMPONENTS:
            raise ReductionError(
                f"n_components must be between 1 and {MAX_COMPONENTS}"
            )

    def key(self) -> str:
        """Return the canonical cache-key string for these parameters."""
        return json.dumps(
            [
                self.method,
                self.n_neighbors,
                self.min_dist,
                self.metric,
                self.random_state,
                self.n_components,
            ],
            separators=(",", ":"),
        )


@dataclass(frozen=True)
class Reduction:
    """Reduced coordinates in the same order as their content hashes.

    ``method`` is the method actually fitted, which differs from the requested
    one when ``fallback`` is true; ``cached`` is true when no fit ran because
    the sidecar already held this exact input set and parameter set.
    """

    method: str
    fallback: bool
    cached: bool
    content_hashes: tuple[str, ...]
    coordinates: tuple[tuple[float, ...], ...]


def fit(method: str, matrix: Matrix, params: ReductionParams) -> list[list[float]]:
    """Fit ``method`` over ``matrix`` and return one coordinate row per sample.

    The heavy runtime is imported here, inside the dispatch through
    ``importlib``, so importing this module never loads numpy, scikit-learn, or
    umap-learn. Every method is seeded by ``params.random_state``, so a repeated
    fit over the same matrix and parameters returns the same coordinates; the
    stochastic methods are seed-stable, not parameter-free.
    """
    if method == "pca":
        return _fit_pca(matrix, params)
    if method == "tsne":
        return _fit_tsne(matrix, params)
    if method == "umap":
        return _fit_umap(matrix, params)
    raise ReductionError(f"unknown method: {method}")


def _array(matrix: Matrix) -> object:
    """Return the input as a float numpy array, imported lazily."""
    numpy = importlib.import_module("numpy")
    return numpy.asarray(matrix, dtype=float)


def _fit_pca(matrix: Matrix, params: ReductionParams) -> list[list[float]]:
    """Project onto the principal components; deterministic and model-free."""
    decomposition = importlib.import_module("sklearn.decomposition")
    model = decomposition.PCA(
        n_components=params.n_components, random_state=params.random_state
    )
    return [[float(value) for value in row] for row in model.fit_transform(_array(matrix))]


def _fit_umap(matrix: Matrix, params: ReductionParams) -> list[list[float]]:
    """Embed with UMAP using the explicit neighborhood, distance, and metric.

    ``n_jobs`` is pinned to one job alongside the fixed ``random_state``, so the
    layout is byte-identical on a repeated call instead of varying with the
    machine's parallelism.
    """
    umap = importlib.import_module("umap")
    model = umap.UMAP(
        n_components=params.n_components,
        n_neighbors=params.n_neighbors,
        min_dist=params.min_dist,
        metric=params.metric,
        random_state=params.random_state,
        n_jobs=1,
    )
    return [[float(value) for value in row] for row in model.fit_transform(_array(matrix))]


def _fit_tsne(matrix: Matrix, params: ReductionParams) -> list[list[float]]:
    """Embed with t-SNE, deriving a perplexity that the sample count allows."""
    manifold = importlib.import_module("sklearn.manifold")
    perplexity = float(min(30.0, max(1.0, (len(matrix) - 1) / 3.0)))
    model = manifold.TSNE(
        n_components=params.n_components,
        perplexity=perplexity,
        metric=params.metric,
        random_state=params.random_state,
        init="pca",
        learning_rate="auto",
    )
    return [[float(value) for value in row] for row in model.fit_transform(_array(matrix))]


def _resolve(method: str, count: int, params: ReductionParams) -> tuple[str, bool]:
    """Return the method that can actually fit ``count`` samples, and whether it fell back.

    UMAP needs strictly more samples than ``n_neighbors + 1`` and at least three
    points in practice; t-SNE needs at least three for a valid perplexity. A
    smaller or degenerate vault falls back to the deterministic PCA baseline
    instead of failing, which is the documented small-vault path.
    """
    if method == "umap" and (count < 3 or count <= params.n_neighbors + 1):
        return "pca", True
    if method == "tsne" and count < 3:
        return "pca", True
    return method, False


def _matrix(vectors: Mapping[str, Sequence[float]]) -> tuple[list[str], list[list[float]]]:
    """Return the bounded content hashes and their validated vectors.

    The keys are sorted so the input set identity, the matrix order, and the
    stored payload are deterministic. More than :data:`MAX_SAMPLES` vectors are
    truncated to the first in that order, keeping the reduction bounded; an
    empty, ragged, or zero-width input is refused because the seam cannot have
    produced it.
    """
    content_hashes = sorted(vectors)[:MAX_SAMPLES]
    width = 0
    matrix: list[list[float]] = []
    for content_hash in content_hashes:
        vector = list(vectors[content_hash])
        if not vector:
            raise ReductionError("cannot reduce an empty vector")
        if not matrix:
            width = len(vector)
        elif len(vector) != width:
            raise ReductionError("cannot reduce vectors of different widths")
        matrix.append([float(value) for value in vector])
    return content_hashes, matrix


def _inputs_hash(content_hashes: Sequence[str]) -> str:
    """Return the digest naming one exact, sorted content-hash input set."""
    digest = sha256()
    for content_hash in content_hashes:
        digest.update(content_hash.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def _components(count: int, matrix: Matrix, params: ReductionParams) -> int:
    """Return the output width the sample count and width allow, capped by the request."""
    width = len(matrix[0]) if matrix else 1
    return max(1, min(params.n_components, count, width))


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_SCHEMA)


def _load_cached(
    connection: sqlite3.Connection, provider: str, params: ReductionParams, inputs: str
) -> tuple[str, tuple[tuple[float, ...], ...]] | None:
    """Return the cached method and coordinates, or ``None`` when absent or unreadable."""
    row = connection.execute(
        "SELECT method, coordinates FROM reduction_cache "
        "WHERE provider = ? AND params = ? AND inputs_hash = ?",
        (provider, params.key(), inputs),
    ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(str(row[1]))
        coordinates = tuple(tuple(float(value) for value in entry) for entry in payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return str(row[0]), coordinates


def _store_cached(
    connection: sqlite3.Connection,
    provider: str,
    params: ReductionParams,
    inputs: str,
    method: str,
    coordinates: Sequence[Sequence[float]],
) -> None:
    connection.execute(
        "INSERT INTO reduction_cache(provider, params, inputs_hash, method, coordinates) "
        "VALUES(?,?,?,?,?) ON CONFLICT(provider, params, inputs_hash) DO UPDATE SET "
        "method=excluded.method, coordinates=excluded.coordinates",
        (provider, params.key(), inputs, method, json.dumps([list(row) for row in coordinates])),
    )


def coordinates(
    vectors: Mapping[str, Sequence[float]],
    provider: str,
    connection: sqlite3.Connection,
    params: ReductionParams | None = None,
    reducer: Reducer | None = None,
) -> Reduction:
    """Reduce ``vectors`` to low-dimensional coordinates, cached in the sidecar.

    ``vectors`` maps each input's content hash to its embedding vector, such as
    the vectors :func:`tangle.semantic.vectors` returns for a provider keyed
    by ``provider``. Identical content hashes, parameters, and provider identity
    hit the disposable ``reduction_cache`` and run no fit at all.

    A miss fits the requested method, or the deterministic PCA baseline when
    :func:`_resolve` finds the input too small for it, and stores the result.
    ``reducer`` replaces the real fit in tests. The result stays advisory:
    nothing here is required by ``similar``, and Markdown remains authoritative.
    """
    selected = params or ReductionParams()
    fitted = fit if reducer is None else reducer
    content_hashes, matrix = _matrix(vectors)
    inputs = _inputs_hash(content_hashes)
    _ensure_schema(connection)
    cached = _load_cached(connection, provider, selected, inputs)
    if cached is not None and len(cached[1]) == len(content_hashes):
        method, rows = cached
        return Reduction(
            method=method,
            fallback=method != selected.method,
            cached=True,
            content_hashes=tuple(content_hashes),
            coordinates=rows,
        )
    method, fallback = _resolve(selected.method, len(content_hashes), selected)
    if content_hashes:
        effective = replace(
            selected,
            method=method,
            n_components=_components(len(content_hashes), matrix, selected),
        )
        produced = fitted(method, matrix, effective)
        if len(produced) != len(content_hashes):
            raise ReductionError(
                f"{method} returned {len(produced)} coordinates for {len(content_hashes)} vectors"
            )
        rows = tuple(tuple(float(value) for value in row) for row in produced)
    else:
        rows = ()
    _store_cached(connection, provider, selected, inputs, method, rows)
    return Reduction(
        method=method,
        fallback=fallback,
        cached=False,
        content_hashes=tuple(content_hashes),
        coordinates=rows,
    )
