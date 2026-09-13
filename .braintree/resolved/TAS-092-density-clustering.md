---
context_rev: 1
priority: P2
updated: 2026-09-12T19:06:30Z
summary: Cluster reduced and raw embedding space with HDBSCAN to produce advisory clusters, noise labels, and outliers without training a model.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Depends on [[TAS-091-manifold-reduction]] at context_rev 1.

Depends on [[TAS-090-native-embedding-provider]] at context_rev 1.

Density clustering tolerates the variable cluster sizes and outliers a
work-tracking vault produces, and HDBSCAN needs no cluster count. The result is
advisory grouping and outlier detection, never authority.

# Outcome

The tool produces advisory clusters over the vault's nodes, a noise label for
unclustered nodes, and an outlier view, derived from embeddings and reported
deterministically.

# Done when

- HDBSCAN runs over both the UMAP coordinates and the raw vectors, with
  `min_cluster_size` and `min_samples` chosen by vault size and documented.
- Selection uses stability across seeds and subsamples rather than one run.
- Noise and outlier nodes are labeled explicitly, never silently attached to a
  cluster.
- Each cluster gets a deterministic label from its centroid-nearest member and
  its shared primary route; no generative summary is used.
- Tests cover a clean two-cluster fixture, a single-cluster vault, a tiny vault,
  and a no-embedding fallback, and `make test` passes.

# Result

`src/braintree/clustering.py` is the derived clustering seam. `clusters(vectors,
provider, connection, nodes, params)` takes the content-hash-keyed vectors
`semantic.vectors` returns plus optional `NodeFacts` (node id and primary
`Parent`/`Area` route), clusters the raw vectors and the seed-specific reduced
coordinates, and returns a `Clustering`. Nothing calls it yet, and nothing has
to: it is advisory and derived under [[DEC-006-semantic-layer-capability-boundary]],
`similar` is unchanged, no interactive verb imports it, and Markdown stays
authoritative.

Both spaces are clustered because they fail differently: the raw vectors keep
everything the model encoded, while the UMAP coordinates expose the manifold but
are stochastic. Selection is the mean pairwise Adjusted Rand Index over runs
that vary the reduction seed and a seeded subsample draw, so no answer comes
from a single fit; only the first full labeling is canonical, so repeated
identical full runs cannot inflate the score. The two `Stability` rows are
reported as evidence and never gate or hide a result; a tie prefers the raw
space because its labels need no stochastic fit.

`min_cluster_size` defaults to `max(5, round(0.05 * n))` capped at 20 and
`min_samples` to a third of it, resolved by `parameters(n)`. The floor keeps a
small or uniform vault from shattering into spurious micro-clusters, the target
is five percent of the vault, and the ceiling keeps a large vault from hiding
sub-structure behind one giant cluster. Both resolved values are exposed on the
result, and an explicit non-zero value overrides either.

HDBSCAN's `-1` is noise, not a cluster: an unclustered node is named in `noise`
and never attached to a nearby cluster. Outliers are the separate view of
members whose GLOSH density score reaches `outlier_threshold`, reported as their
own tuple, so a clustered member can be both in its cluster and in the outlier
view. Each `Cluster` is labeled from its centroid-nearest member (ties by node
id) and the primary route its members share, with `routes` listing every
distinct route its members carry for [[TAS-093-cluster-answer-verbs]]'
over-broad-route detection; no generative summary is used.

The layer is bounded (`MAX_SAMPLES = 512` in sorted content-hash order) and
advisory. An empty embedding set is the capability-absent path and returns an
explicit `available=False` result, not an exception, and a reduction the seam
refuses drops only the reduced space. `hdbscan`, `numpy`, and `scikit-learn` are
imported lazily inside `hdbscan()`, so a plain install loads no heavy module and
`dependencies = []` still holds. No dependency pin changed, so `pyproject.toml`
and `uv.lock` are untouched.

Evidence. The scientific loop ran before the tests were trusted. The tiny
deterministic fixture (two well-separated 8-D blobs, fixed generator seed, 24
vectors) yielded two clusters with zero noise and raw/reduced stability 1.0,
identical across two independent calls; the uniform single-cluster vault
yielded zero clusters and 24 explicit noise (raw 1.0 against reduced 0.2169, so
the raw all-noise verdict won); a tiny two-vector vault yielded zero clusters
and two noise; and an empty embedding set returned the explicit unavailable
result. The live vault then ran through the native provider in the isolated
environment:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/bt-cluster-venv uv sync --extra semantic
BT_SIDECAR_DIR=/tmp/bt-live-cluster-sidecar BT_PROJECT_ID=live-cluster \
BT_SEMANTIC_PROVIDER='/tmp/bt-cluster-venv/bin/python -m braintree semantic embed' \
/tmp/bt-cluster-venv/bin/python /tmp/bt-cluster-live.py
```

It embedded all 118 nodes (118 distinct bodies, 384 dimensions) offline from the
pre-fetched cache, chose the reduced UMAP space (`min_cluster_size=6`,
`min_samples=2`) with stability 0.5651 against 0.2661 for raw, and reported 8
clusters, 7 noise nodes, and no outliers, with sample deterministic labels
`TAS-059` (29 members), `THO-010` (16), and `DEC-002` (14); a repeated call
returned the same clusters. That snapshot preceded this Result text. Because a
node's own body is part of the embedded corpus, later edits shift the counts
slightly; the chosen parameters, the reduced-space selection, and determinism
do not depend on the exact count.

`tests/test_clustering.py` pins the parameter rule, both-space clustering, the
stability selection and tie-break, the centroid-nearest member and shared-route
label, explicit noise, separate outliers, the tiny and no-embedding cases,
boundedness, refusals, and the import graph with an injected clusterer and
reducer, so the default suite stays offline and fast. The dev `.venv` never
installed the extra: the default run is 15 passed and 1 skipped, and the
isolated run is 16 passed.

`braintree check nodes`, `braintree index nodes`, `make test`, and
`make verb-benchmark` pass. Adding `src/braintree/clustering.py` moved the token
benchmark's composite local-fixture file count from 72 to 73, updated in the
same change. No verb or `SKILL.md` contract changed. Resolving this node
advanced the parent's `next` to [[TAS-093-cluster-answer-verbs]].
