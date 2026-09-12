---
context_rev: 1
priority: P2
updated: 2026-09-12T17:22:00Z
summary: Cluster reduced and raw embedding space with HDBSCAN to produce advisory clusters, noise labels, and outliers without training a model.
next: Implement HDBSCAN clustering over the reduced and raw vectors.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Gated on [[TAS-091-manifold-reduction]].

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
