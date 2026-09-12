---
context_rev: 1
priority: P2
updated: 2026-09-12T15:09:27Z
summary: Add an optional, derived, non-authoritative semantic retrieval layer behind the capability boundary.
next: Add an optional semantic reranking and near-duplicate path that degrades to the lexical baseline.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

Lexical retrieval misses paraphrases and near-duplicates that share no tokens.
A semantic layer can help, but only under the capability boundary: optional,
derived, rebuildable, and never authoritative. The lowest-risk path is a
deterministic lexical baseline first, then either a shipped small reranker or an
opportunistic embedding provider with a clean fallback.

# Outcome

When semantic support is available, `similar` and ranked search improve; when it
is absent, every command behaves identically on the lexical baseline. Nothing
semantic is required for correctness.

# Done when

- The lexical baseline is the default and is unchanged without a provider.
- Any provider is probed, optional, and cached in the derived sidecar keyed by
  content hash.
- Correctness gates are identical with and without the provider.
- A token and round-trip comparison decides whether to keep it.
- `make test` passes.
