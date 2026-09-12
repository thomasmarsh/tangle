---
context_rev: 1
priority: P2
updated: 2026-09-12T17:22:00Z
summary: Expose advisory clusters, embedding-reranked similar, and bounded hub and cluster digests through direct braintree answers.
next: Implement the cluster, reranked-similar, and digest answers.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Gated on [[TAS-092-density-clustering]].

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

Clustering is only useful to a client if a bounded command returns it. This
task gives the derived layer a small answer surface, consistent with the
existing direct-answer verbs and their TOON output.

# Outcome

A client can ask for cluster groupings and outliers, get `similar` results
reranked by embeddings, and get a bounded digest of a hub or cluster, all with
an advisory label and identical behavior when the capability is absent.

# Done when

- `braintree clusters` returns bounded advisory clusters, their representative
  members, over-broad route suggestions, and orphan or outlier clusters.
- `braintree similar` uses the embedding rerank when the capability is present
  and is byte-identical to the lexical baseline when it is absent.
- A bounded `digest` answer returns the summaries and `next` of a chosen hub's
  or cluster's unresolved members, without a generative summary.
- Output is compact TOON with explicit limits and an explicit advisory line,
  and no cluster result becomes a claim, assignment, or authority.
- Tests cover the present and absent capability paths, and `make test` passes.
