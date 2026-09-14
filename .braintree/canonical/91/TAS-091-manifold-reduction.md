---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Reduce cached embeddings with UMAP, with PCA and t-SNE comparisons, into derived deterministic coordinates for clustering and inspection.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Depends on [[TAS-090-native-embedding-provider]] at context_rev 1.

Depends on [[TAS-088-optional-embedding-extra]] at context_rev 2.

Embedding vectors are high-dimensional and dense, so density clustering and any
human inspection work better on a reduced manifold. UMAP is the primary choice;
PCA is the linear baseline and t-SNE the comparison.

# Outcome

Given cached embeddings, the tool produces derived low-dimensional coordinates
that are deterministic for fixed parameters and seeds, with no model training.

# Done when

- UMAP is implemented with explicit `n_neighbors`, `min_dist`, and metric, and a
  fixed `random_state`.
- PCA is available as a linear baseline and t-SNE as a comparison, and the
  differences are documented.
- Reduced coordinates are cached in the disposable sidecar keyed by content
  hash plus parameters, so a re-run with unchanged inputs recomputes nothing.
- Small or degenerate vaults fall back deterministically (for example PCA)
  rather than failing when UMAP needs more samples than exist.
- Output is advisory and bounded, and `make test` passes.

# Result

`src/braintree/reduction.py` is the derived reduction seam. `coordinates(vectors,
provider, connection, params)` takes the content-hash-keyed vectors
`semantic.vectors` returns, keyed by the same provider command hash the vector
cache uses, and returns a `Reduction`: the coordinates, the method actually
fitted, whether that differed from the request, and whether the sidecar already
held them. Nothing calls it yet, and nothing has to: it is advisory and derived
under [[DEC-006-semantic-layer-capability-boundary]], `similar` is unchanged, no
interactive verb imports it, and Markdown stays authoritative.

The three methods are explicit and their differences are documented in the
module. UMAP is primary and every parameter that changes the layout is named
(`n_neighbors`, `min_dist`, `metric`, `random_state`), with `n_jobs=1` pinned so
the seed alone determines the layout. PCA is the linear baseline: model-free,
deterministic, preserving global variance, and the only method with no
sample-count requirement, which is why it is the fallback. t-SNE is the
comparison: it preserves local neighborhoods under a different divergence, is
slower, and gets a perplexity the sample count allows
(`min(30, max(1, (n - 1) / 3))`) with `init="pca"`. Both stochastic methods are
seed-stable rather than parameter-free, which is what "deterministic for fixed
parameters and seeds" means here.

Coordinates live in the disposable `reduction_cache(provider, params,
inputs_hash, method, coordinates)`, created additively next to the vector cache
so an existing sidecar needs no migration. `params` is the canonical JSON of the
explicit parameters, `inputs_hash` is a digest over the sorted content-hash
input set, and `provider` is the same command-string identity the vector cache
keys on, so a changed parameter, provider, or input row misses while an
identical re-run performs no fit at all. The stored `method` means a cache hit
still reports a PCA fallback accurately.

Output is bounded and advisory. `n_components` is capped at 3 and clamped to
what the sample count and width allow, and at most `MAX_SAMPLES = 512` vectors
are reduced, truncated in sorted content-hash order. `_resolve` sends UMAP to PCA
when there are fewer than three samples or no more than `n_neighbors + 1`, and
t-SNE to PCA below three samples, so a tiny or degenerate vault reduces
deterministically instead of raising. A non-empty zero-width or ragged input is
refused, because the provider seam cannot have produced it.

Heavy modules (numpy, scikit-learn, umap-learn) are imported through
`importlib` inside the `fit` dispatch, mirroring [[TAS-090-native-embedding-provider]],
so a plain install imports nothing heavy and `dependencies = []` still holds. No
dependency pin changed, so `pyproject.toml` and `uv.lock` are untouched.

Evidence. `tests/test_reduction.py` pins the parameters, dispatch, fallback,
cache, bounds, and import graph with an injected counting reducer, so the
default suite stays offline and fast: parameter validation; an unknown method
refused before any import; the explicit parameters reaching the fit unchanged;
one fit for two identical calls and a cache hit that reduces nothing; provider,
parameter, and input-set misses; PCA fallback at n=2, at n = `n_neighbors + 1`,
and for t-SNE; an empty input storing empty coordinates without a fit; bounding
at `MAX_SAMPLES` and `MAX_COMPONENTS`; ragged and zero-width refusals; corrupt
or short cache rows recomputed rather than trusted; and a fresh interpreter
running `braintree --help` that loads no heavy module. With the extra installed
the same file also fits the real runtime on two well-separated 8-D blobs and
asserts seeded UMAP coordinates identical across two independent fits and the
PCA fallback at n=2.

The scientific loop ran before the tests were trusted. The tiny deterministic
fixture (two 8-D Gaussian blobs, fixed generator seed, 24 vectors) fit UMAP to
`(24, 2)` with byte-identical coordinates across two independent fits and across
two separate processes, hit the cache on the second identical call with the
counting reducer unchanged, missed on a changed `n_neighbors`, fell back to PCA
at n=2 with a repeatable result, and fitted t-SNE as the comparison. The live
vault then ran through the native provider in the isolated environment:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/bt-reduce-venv uv sync --extra semantic
BT_SIDECAR_DIR=/tmp/bt-live-reduce-sidecar BT_PROJECT_ID=live-reduce \
BT_SEMANTIC_PROVIDER='/tmp/bt-reduce-venv/bin/python -m braintree semantic embed' \
/tmp/bt-reduce-venv/bin/python /tmp/bt-reduce-live.py
```

It embedded all 118 nodes (118 distinct bodies, 384 dimensions) offline from the
pre-fetched cache, reduced them to `(118, 2)` with UMAP, reported
`first_cached=False second_cached=True` for two identical calls, and compared the
two coordinate sets equal. The dev `.venv` never installed the extra: the
default run is 11 passed and 1 skipped (`importorskip`), and the isolated run is
12 passed.

`braintree check nodes`, `braintree index nodes`, `make test`, and
`make verb-benchmark` pass. Adding `src/braintree/reduction.py` moved the token
benchmark's composite local-fixture file count from 71 to 72, updated in the
same change. No verb or `SKILL.md` contract changed. Resolving this node advanced
the parent's `next` to [[TAS-092-density-clustering]].
