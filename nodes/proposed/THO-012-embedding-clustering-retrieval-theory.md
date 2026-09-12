---
context_rev: 1
updated: 2026-09-12T17:22:00Z
summary: Theory that off-the-shelf embeddings plus manifold and density clustering improve near-duplicate admission and advisory grouping and cut round trips without training a model.
---

# Question

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Do off-the-shelf sentence embeddings, reduced with UMAP or t-SNE and clustered
with HDBSCAN, improve near-duplicate admission and advisory grouping for the
vault, and reduce client round trips, without training a model and without
weakening the deterministic lexical baseline?

# Hypothesis

Lexical retrieval misses paraphrases that share no tokens, so an agent
re-derives near-duplicates and hand-groups the frontier. Off-the-shelf
embeddings close the paraphrase gap, and manifold plus density clustering turn
the derived embedding space into advisory clusters and outliers a client can
consume in one bounded answer. Because the models are used as published and the
results are advisory and derived, correctness never depends on the capability
and the default install is unchanged.

# Prediction

Cluster and near-duplicate answers computed from published embeddings agree with
the graph's own routes more often than the lexical baseline, and replace several
shell or search round trips with one bounded command. A trained model is not
required for the gain, and under
[[DEC-006-semantic-layer-capability-boundary]] every core answer is identical
when the capability is absent.

# Test

- Model and runtime selection: [[TAS-089-embedding-model-selection]].
- Native provider: [[TAS-090-native-embedding-provider]].
- Manifold and density reduction: [[TAS-091-manifold-reduction]] and
  [[TAS-092-density-clustering]].
- Answer surface: [[TAS-093-cluster-answer-verbs]].
- Quality and round-trip gate: [[TAS-094-clustering-quality-gate]].

# Evidence

No samples recorded yet.
