---
context_rev: 1
priority: P2
updated: 2026-09-12T17:22:00Z
summary: Reduce cached embeddings with UMAP, with PCA and t-SNE comparisons, into derived deterministic coordinates for clustering and inspection.
next: Implement UMAP reduction over the cached vectors with fixed seeds.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Gated on [[TAS-090-native-embedding-provider]].

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
