"""Advisory density clustering over cached embeddings and their reduction.

The optional semantic layer embeds node text (:mod:`braintree.semantic`) and the
derived reduction turns those vectors into low-dimensional coordinates
(:mod:`braintree.reduction`). This module is the next derived layer: it runs
HDBSCAN over both spaces, keeps noise and outliers explicit, and labels each
cluster from one of its own members. Nothing here is authoritative, required by
``similar``, or reachable from an interactive verb: the caller decides when to
cluster, and the whole layer is derived and advisory under the
capability-boundary decision.

Two spaces are clustered, because they fail differently. The **raw** provider
vectors preserve everything the model encoded and need no extra fit, but a
dense 384-dimensional space can hide structure in distance concentration. The
**reduced** UMAP coordinates expose the manifold the reduction found, but they
are stochastic, so a layout artifact could become a cluster. Rather than pick
one from belief, the winner is the space whose labelings agree most across
seeds and subsamples, measured by the mean pairwise Adjusted Rand Index. That
stability is reported as evidence; it never gates or hides a result.

The parameters scale with the vault, not with a constant. ``min_cluster_size``
defaults to ``max(5, round(0.05 * n))`` capped at 20 and ``min_samples`` to a
third of it, so a small or uniform vault cannot shatter into spurious
micro-clusters and a large one cannot hide sub-structure behind one giant
cluster; both are exposed on the result. Subsampling is seeded, so a repeated
call over the same input returns the same labels.

HDBSCAN's ``-1`` is noise, not a cluster: an unclustered node is named in
``noise`` and never attached to a nearby cluster. A separate outlier view
reports the members whose GLOSH density score reaches ``outlier_threshold``,
again as their own tuple rather than a merge into a cluster. Each cluster is
labeled from the member nearest its centroid plus the primary ``Parent``/``Area``
route its members share, so the label is reproducible and no generative summary
is involved. An empty embedding set is the capability-absent path and returns
an explicit unavailable result instead of raising.
"""

from __future__ import annotations

import importlib
import math
import random
import sqlite3
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from . import reduction

__all__ = [
    "CLUSTER_SPACES",
    "MAX_SAMPLES",
    "NOISE",
    "Cluster",
    "ClusterError",
    "ClusterMember",
    "ClusterParams",
    "Clusterer",
    "Clustering",
    "NodeFacts",
    "Stability",
    "clusters",
    "hdbscan",
    "parameters",
]

# HDBSCAN's label for a point no cluster claims. It is reported explicitly and
# never attached to a neighbouring cluster.
NOISE = -1
# Both spaces are clustered and compared: the raw provider vectors and the
# reduced coordinates. The order also breaks a stability tie, raw first.
CLUSTER_SPACES = ("raw", "reduced")
# The density parameters scale with the node count. A cluster is a related group
# of nodes, so its floor is a small absolute number, its target is a fraction of
# the vault, and its ceiling keeps a large vault from hiding sub-structure behind
# one giant cluster. The floor is what keeps a small or uniform vault from
# shattering into spurious micro-clusters.
_MIN_CLUSTER_SIZE = 5
_MAX_MIN_CLUSTER_SIZE = 20
_CLUSTER_SIZE_FRACTION = 0.05
# The derived layer is bounded exactly as the reduction is: at most this many
# nodes are clustered, taken in sorted content-hash order.
MAX_SAMPLES = 512
_MAX_SEEDS = 8
_MAX_SUBSAMPLES = 8

Matrix = Sequence[Sequence[float]]
# One HDBSCAN fit: a label and a density-based outlier score per row.
Clusterer = Callable[[Matrix, "ClusterParams"], tuple[list[int], list[float]]]


class ClusterError(Exception):
    """Invalid input or an unusable fit result, reported to the caller."""


@dataclass(frozen=True)
class NodeFacts:
    """The Markdown-derived identity of one embedded text.

    ``node_id`` names the node the embedding came from and ``route`` is its
    primary ``Parent``/``Area`` reference, which becomes the cluster's shared
    route hint. Both are caller-supplied, so this layer never reads Markdown and
    never decides a node's status.
    """

    node_id: str
    route: str = ""


@dataclass(frozen=True)
class ClusterParams:
    """The explicit HDBSCAN parameters and the deterministic selection knobs.

    ``min_cluster_size`` and ``min_samples`` of zero mean "derive from the node
    count" through :func:`parameters`. ``seeds`` drive both the reduction seed
    and the seeded subsample draws, ``subsamples`` is how many seeded subsets
    each seed contributes beside the full set, ``subsample_fraction`` is their
    size, and ``outlier_threshold`` is the density score at or above which a
    member is reported as an outlier. ``reduction`` configures the reduced
    space. ``metric`` applies to both spaces.
    """

    metric: str = "euclidean"
    min_cluster_size: int = 0
    min_samples: int = 0
    seeds: tuple[int, ...] = (17, 29, 43)
    subsamples: int = 3
    subsample_fraction: float = 0.8
    outlier_threshold: float = 0.9
    cluster_selection_method: str = "eom"
    reduction: reduction.ReductionParams = field(
        default_factory=reduction.ReductionParams
    )

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise ClusterError("metric must be a non-empty distance name")
        if self.min_cluster_size < 0 or self.min_samples < 0:
            raise ClusterError("min_cluster_size and min_samples must not be negative")
        if not self.seeds:
            raise ClusterError("at least one seed is required")
        if len(self.seeds) > _MAX_SEEDS:
            raise ClusterError(f"at most {_MAX_SEEDS} seeds are allowed")
        if not 0 <= self.subsamples <= _MAX_SUBSAMPLES:
            raise ClusterError(f"subsamples must be between 0 and {_MAX_SUBSAMPLES}")
        if not 0 < self.subsample_fraction <= 1:
            raise ClusterError("subsample_fraction must be in (0, 1]")
        if not 0 <= self.outlier_threshold <= 1:
            raise ClusterError("outlier_threshold must be between 0 and 1")
        if self.cluster_selection_method not in ("eom", "leaf"):
            raise ClusterError("cluster_selection_method must be 'eom' or 'leaf'")


@dataclass(frozen=True)
class Stability:
    """How stable one space's clustering is across seeds and subsamples.

    ``ari`` is the mean pairwise Adjusted Rand Index over every run of the
    space, each pair compared on the members the two runs share, and ``runs`` is
    how many labelings entered that average. It is evidence for the space
    choice, never a threshold that discards a result.
    """

    space: str
    runs: int
    ari: float


@dataclass(frozen=True)
class ClusterMember:
    """One node's advisory label in the chosen space."""

    node_id: str
    route: str
    cluster: int
    outlier_score: float
    outlier: bool


@dataclass(frozen=True)
class Cluster:
    """One advisory cluster, labeled from a member rather than a summary.

    ``representative`` is the member nearest the cluster centroid, ties broken
    by node id. ``route`` is the one primary ``Parent``/``Area`` route every
    member shares or ``""`` when they disagree, ``routes`` is every distinct
    non-empty route its members carry, and ``label`` joins the representative
    with the shared route for display. The members are node ids and the cluster
    is advisory only.
    """

    id: int
    representative: str
    route: str
    routes: tuple[str, ...]
    members: tuple[str, ...]

    @property
    def label(self) -> str:
        """Return the deterministic ``representative``/``route`` label."""
        return f"{self.representative}@{self.route}" if self.route else self.representative


@dataclass(frozen=True)
class Clustering:
    """The advisory clustering of one embedding set.

    ``available`` is false when no embedding was supplied, which is the
    capability-absent path: every tuple is empty and ``reason`` says why. When
    it is true, ``space`` names the chosen space, ``method`` names the reduction
    method behind a reduced choice, ``members`` carries one label per embedded
    node, ``clusters`` holds only real clusters, and ``noise`` and ``outliers``
    are reported separately and never merged into a cluster. ``params`` carries
    the resolved size-dependent density parameters.
    """

    available: bool
    space: str
    method: str
    reason: str
    params: ClusterParams
    members: tuple[ClusterMember, ...]
    clusters: tuple[Cluster, ...]
    noise: tuple[str, ...]
    outliers: tuple[str, ...]
    stability: tuple[Stability, ...]


def parameters(count: int, params: ClusterParams | None = None) -> ClusterParams:
    """Return ``params`` with the size-dependent density parameters resolved.

    ``min_cluster_size`` defaults to ``max(5, round(0.05 * n))`` capped at 20: a
    cluster is a related group, so its floor is a small absolute number, its
    target is five percent of the vault, and the ceiling keeps one giant cluster
    from hiding sub-structure. ``min_samples`` defaults to a third of
    ``min_cluster_size``. Explicit non-zero values are used unchanged.
    """
    selected = params or ClusterParams()
    if selected.min_cluster_size:
        minimum = selected.min_cluster_size
    else:
        minimum = min(
            _MAX_MIN_CLUSTER_SIZE,
            max(_MIN_CLUSTER_SIZE, round(count * _CLUSTER_SIZE_FRACTION)),
        )
    samples = selected.min_samples or max(1, round(minimum / 3))
    return replace(selected, min_cluster_size=minimum, min_samples=samples)


def hdbscan(matrix: Matrix, params: ClusterParams) -> tuple[list[int], list[float]]:
    """Fit HDBSCAN over ``matrix`` and return its labels and outlier scores.

    The heavy import happens here, so importing :mod:`braintree.clustering`
    loads nothing and no interactive verb reaches this path. ``min_samples``
    falls back to ``min_cluster_size`` while it is still zero, and a fit that
    exposes no GLOSH scores reports zero outliers rather than failing.
    """
    module = importlib.import_module("hdbscan")
    numpy = importlib.import_module("numpy")
    model = module.HDBSCAN(
        min_cluster_size=params.min_cluster_size,
        min_samples=params.min_samples or params.min_cluster_size,
        metric=params.metric,
        cluster_selection_method=params.cluster_selection_method,
    )
    labels = model.fit_predict(numpy.asarray(matrix, dtype=float))
    scores = getattr(model, "outlier_scores_", None)
    if scores is None:
        scores = [0.0] * len(matrix)
    if len(labels) != len(matrix) or len(scores) != len(matrix):
        raise ClusterError("HDBSCAN returned a result for the wrong number of samples")
    return [int(value) for value in labels], [float(value) for value in scores]


def _bounded(
    vectors: Mapping[str, Sequence[float]],
) -> tuple[list[str], list[list[float]]]:
    """Return the bounded content hashes and their validated raw vectors.

    Keys are sorted so the matrix order and every later label stay
    deterministic, and more than :data:`MAX_SAMPLES` are truncated in that
    order. A non-empty ragged or zero-width input is refused because the
    provider seam cannot have produced it.
    """
    content_hashes = sorted(vectors)[:MAX_SAMPLES]
    rows: list[list[float]] = []
    width = 0
    for content_hash in content_hashes:
        row = [float(value) for value in vectors[content_hash]]
        if not row:
            raise ClusterError("cannot cluster an empty vector")
        if not rows:
            width = len(row)
        elif len(row) != width:
            raise ClusterError("cannot cluster vectors of different widths")
        rows.append(row)
    return content_hashes, rows


def _reduced_matrices(
    content_hashes: Sequence[str],
    vectors: Mapping[str, Sequence[float]],
    provider: str,
    connection: sqlite3.Connection,
    params: ClusterParams,
    reducer: reduction.Reducer | None,
) -> tuple[dict[int, list[list[float]]], str] | None:
    """Return one reduced matrix per seed and the method actually fitted.

    Each seed is one deterministic reduction, and the whole set is what the
    stability comparison needs. A reduction the seam refuses drops the reduced
    space instead of failing the advisory answer, and a result missing one of
    the requested content hashes is equally unusable.
    """
    per_seed: dict[int, list[list[float]]] = {}
    method = ""
    for seed in params.seeds:
        seed_params = replace(params.reduction, random_state=seed)
        try:
            result = reduction.coordinates(
                vectors, provider, connection, seed_params, reducer
            )
        except reduction.ReductionError:
            return None
        by_hash = dict(zip(result.content_hashes, result.coordinates, strict=True))
        if any(content_hash not in by_hash for content_hash in content_hashes):
            return None
        method = method or result.method
        per_seed[seed] = [list(by_hash[content_hash]) for content_hash in content_hashes]
    return per_seed, method


def _subsets(count: int, params: ClusterParams, seed: int) -> list[tuple[int, ...]]:
    """Return the deterministic index subsets one seed contributes.

    The full index list is always first. Each further subset is drawn from a
    sampler seeded by the reduction seed and its position, so subsampling is
    reproducible, and is never smaller than ``min_cluster_size`` because a
    smaller draw could not contain a cluster and would measure only noise.
    """
    size = min(count, max(params.min_cluster_size, round(count * params.subsample_fraction)))
    subsets = [tuple(range(count))]
    for run in range(params.subsamples):
        sampler = random.Random(f"{seed}:{run}")
        subsets.append(tuple(sorted(sampler.sample(range(count), size))))
    return subsets


def _fit(
    clusterer: Clusterer, matrix: Matrix, params: ClusterParams
) -> tuple[list[int], list[float]]:
    """Return one validated label and score per row of ``matrix``."""
    labels, scores = clusterer(matrix, params)
    if len(labels) != len(matrix) or len(scores) != len(matrix):
        raise ClusterError("clusterer returned a result for the wrong number of samples")
    return [int(value) for value in labels], [float(value) for value in scores]


def _ari(left: Sequence[int], right: Sequence[int]) -> float:
    """Return the Adjusted Rand Index of two labelings of the same members.

    A pure-Python closed form, so stability needs no heavy import and the
    default install computes it. The noise label is an ordinary group here:
    two runs that both call a member noise agree about it.
    """
    if len(left) != len(right) or len(left) < 2:
        return 1.0

    def choose_two(value: int) -> float:
        return value * (value - 1) / 2

    cells = Counter(zip(left, right, strict=True))
    rows = Counter(left)
    columns = Counter(right)
    pair_count = choose_two(len(left))
    cell = sum(choose_two(value) for value in cells.values())
    row = sum(choose_two(value) for value in rows.values())
    column = sum(choose_two(value) for value in columns.values())
    expected = row * column / pair_count if pair_count else 0.0
    maximum = (row + column) / 2
    if maximum == expected:
        return 1.0
    return (cell - expected) / (maximum - expected)


@dataclass(frozen=True)
class _Run:
    """One labeling, keyed by the global index of every member it covers."""

    labels: Mapping[int, int]


@dataclass(frozen=True)
class _Space:
    """The canonical full-data labeling of one space plus its stability runs."""

    matrix: tuple[tuple[float, ...], ...]
    labels: tuple[int, ...]
    scores: tuple[float, ...]
    method: str
    stability: Stability


def _mean_ari(runs: Sequence[_Run]) -> float:
    """Return the mean pairwise agreement over ``runs`` on their shared members."""
    total = 0.0
    pairs = 0
    for position, left in enumerate(runs):
        for right in runs[position + 1 :]:
            shared = sorted(set(left.labels) & set(right.labels))
            if len(shared) < 2:
                continue
            total += _ari(
                [left.labels[index] for index in shared],
                [right.labels[index] for index in shared],
            )
            pairs += 1
    return total / pairs if pairs else 1.0


def _space(
    space: str,
    matrices: Mapping[int, list[list[float]]],
    params: ClusterParams,
    clusterer: Clusterer,
    method: str,
) -> _Space:
    """Cluster one space at every seed and summarize its stability.

    The reported labeling is the full set under the first seed, while stability
    averages that full labeling against every seeded subsample. The subsamples
    are what expose a space whose clusters survive less data, and only the first
    full labeling is canonical so repeated identical full runs cannot inflate
    the score.
    """
    canonical_seed = params.seeds[0]
    labels, scores = _fit(clusterer, matrices[canonical_seed], params)
    runs = [_Run({index: label for index, label in enumerate(labels)})]
    for seed in params.seeds:
        for indices in _subsets(len(matrices[seed]), params, seed)[1:]:
            subset = [matrices[seed][index] for index in indices]
            subset_labels, _scores = _fit(clusterer, subset, params)
            runs.append(
                _Run({index: subset_labels[position] for position, index in enumerate(indices)})
            )
    return _Space(
        matrix=tuple(tuple(row) for row in matrices[canonical_seed]),
        labels=tuple(labels),
        scores=tuple(scores),
        method=method,
        stability=Stability(space=space, runs=len(runs), ari=_mean_ari(runs)),
    )


def _facts(content_hash: str, nodes: Mapping[str, NodeFacts]) -> NodeFacts:
    """Return the caller's facts for ``content_hash``, or the hash as its own id."""
    return nodes.get(content_hash, NodeFacts(node_id=content_hash))


def _nearest_member(
    positions: Sequence[int],
    matrix: Sequence[Sequence[float]],
    centroid: Sequence[float],
    content_hashes: Sequence[str],
    nodes: Mapping[str, NodeFacts],
) -> int:
    """Return the position nearest ``centroid``, ties broken by node id."""
    return min(
        positions,
        key=lambda position: (
            math.dist(matrix[position], centroid),
            _facts(content_hashes[position], nodes).node_id,
        ),
    )


def _clusters(
    space: _Space, content_hashes: Sequence[str], nodes: Mapping[str, NodeFacts]
) -> tuple[Cluster, ...]:
    """Label every real cluster from its centroid-nearest member and shared route.

    The representative is the member with the smallest distance to its cluster
    centroid, ties broken by node id. The route is the single non-empty primary
    route every member shares, or ``""`` when they disagree, while ``routes``
    lists every distinct route its members carry so a caller can spot one route
    spread across many clusters. All of it comes from the caller's facts, so a
    label never depends on generated text.
    """
    grouped: dict[int, list[int]] = {}
    for position, label in enumerate(space.labels):
        if label == NOISE:
            continue
        grouped.setdefault(label, []).append(position)

    clusters: list[Cluster] = []
    for label in sorted(grouped):
        positions = grouped[label]
        width = len(space.matrix[positions[0]])
        centroid = [
            sum(space.matrix[position][column] for position in positions) / len(positions)
            for column in range(width)
        ]

        representative = _nearest_member(
            positions, space.matrix, centroid, content_hashes, nodes
        )
        routes = sorted(
            {
                _facts(content_hashes[position], nodes).route
                for position in positions
            }
            - {""}
        )
        members = tuple(
            sorted(_facts(content_hashes[position], nodes).node_id for position in positions)
        )
        clusters.append(
            Cluster(
                id=label,
                representative=_facts(content_hashes[representative], nodes).node_id,
                route=routes[0] if len(routes) == 1 else "",
                routes=tuple(routes),
                members=members,
            )
        )
    clusters.sort(key=lambda cluster: (-len(cluster.members), cluster.representative, cluster.id))
    return tuple(clusters)


def _report(
    spaces: Mapping[str, _Space],
    params: ClusterParams,
    content_hashes: Sequence[str],
    nodes: Mapping[str, NodeFacts],
) -> Clustering:
    """Build the result from the most stable space, keeping noise and outliers apart.

    The space with the highest mean pairwise stability wins; the fixed space
    order breaks a tie in favour of the raw vectors, whose labels do not depend
    on a stochastic fit. A space that claims no cluster is still reported when it
    is the most stable, so the answer is the honest all-noise verdict rather
    than the unstable one.
    """
    order = {space: position for position, space in enumerate(CLUSTER_SPACES)}
    chosen = min(spaces, key=lambda space: (-spaces[space].stability.ari, order[space]))
    space = spaces[chosen]

    members: list[ClusterMember] = []
    for position, content_hash in enumerate(content_hashes):
        facts = _facts(content_hash, nodes)
        score = space.scores[position]
        members.append(
            ClusterMember(
                node_id=facts.node_id,
                route=facts.route,
                cluster=space.labels[position],
                outlier_score=score,
                outlier=score >= params.outlier_threshold,
            )
        )
    members.sort(key=lambda member: member.node_id)

    return Clustering(
        available=True,
        space=chosen,
        method=space.method,
        reason="",
        params=params,
        members=tuple(members),
        clusters=_clusters(space, content_hashes, nodes),
        noise=tuple(sorted(member.node_id for member in members if member.cluster == NOISE)),
        outliers=tuple(sorted(member.node_id for member in members if member.outlier)),
        stability=tuple(spaces[name].stability for name in CLUSTER_SPACES if name in spaces),
    )


def clusters(
    vectors: Mapping[str, Sequence[float]],
    provider: str,
    connection: sqlite3.Connection,
    nodes: Mapping[str, NodeFacts] | None = None,
    params: ClusterParams | None = None,
    reducer: reduction.Reducer | None = None,
    clusterer: Clusterer | None = None,
) -> Clustering:
    """Cluster cached embeddings over the raw vectors and the reduced coordinates.

    ``vectors`` maps each embedded text's content hash to its provider vector,
    such as :func:`braintree.semantic.vectors` returns, and ``nodes`` maps the
    same hashes to the node id and primary route a cluster label is built from;
    a missing entry falls back to the content hash with no route. Both the raw
    vectors and the seed-specific UMAP coordinates (:mod:`braintree.reduction`)
    are clustered, and the more stable space wins. The answer is advisory and
    bounded: at most :data:`MAX_SAMPLES` nodes, noise and outliers reported
    separately from real clusters, and an empty embedding set returns the
    explicit unavailable result instead of raising.
    """
    selected = params or ClusterParams()
    content_hashes, rows = _bounded(vectors)
    if not content_hashes:
        return Clustering(
            available=False,
            space="",
            method="",
            reason="no embeddings",
            params=selected,
            members=(),
            clusters=(),
            noise=(),
            outliers=(),
            stability=(),
        )
    effective = parameters(len(content_hashes), selected)
    fit = hdbscan if clusterer is None else clusterer
    facts = nodes or {}
    raw = {seed: rows for seed in effective.seeds}

    spaces: dict[str, _Space] = {
        "raw": _space("raw", raw, effective, fit, method=""),
    }
    bounded = dict(zip(content_hashes, rows, strict=True))
    reduced = _reduced_matrices(
        content_hashes, bounded, provider, connection, effective, reducer
    )
    if reduced is not None:
        matrices, method = reduced
        spaces["reduced"] = _space("reduced", matrices, effective, fit, method=method)
    return _report(spaces, effective, content_hashes, facts)
