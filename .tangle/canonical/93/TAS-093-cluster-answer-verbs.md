---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Expose advisory clusters, embedding-reranked similar, and bounded hub and cluster digests through direct tangle answers.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Depends on [[TAS-092-density-clustering]] at context_rev 1.

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

Clustering is only useful to a client if a bounded command returns it. This
task gives the derived layer a small answer surface, consistent with the
existing direct-answer verbs and their TOON output.

# Outcome

A client can ask for cluster groupings and outliers, get `similar` results
reranked by embeddings, and get a bounded digest of a hub or cluster, all with
an advisory label and identical behavior when the capability is absent.

# Done when

- `tangle clusters` returns bounded advisory clusters, their representative
  members, over-broad route suggestions, and orphan or outlier clusters.
- `tangle similar` uses the embedding rerank when the capability is present
  and is byte-identical to the lexical baseline when it is absent.
- A bounded `digest` answer returns the summaries and `next` of a chosen hub's
  or cluster's unresolved members, without a generative summary.
- Output is compact TOON with explicit limits and an explicit advisory line,
  and no cluster result becomes a claim, assignment, or authority.
- Tests cover the present and absent capability paths; `make test` passes.

# Result

`tangle clusters` is the explicit derived answer. `cli._clusters` probes the
capability cheaply first: `semantic.extra()` (a `find_spec` lookup) must report
the optional extra and `semantic.probe()` must return a provider, or the verb
prints an advisory line and `clusters: capability absent` and exits zero without
importing the clustering module or loading a model. When present it imports
`tangle.clustering` lazily, reads bounded per-node embedding inputs through
`index.cluster_source`, embeds them through the seam's content-hash cache, and
calls `clustering.answer`. Output is compact TOON bounded by `--limit` and a
documented 60 s wall-clock budget with an explicit `advisory:` line: chosen
space and method, resolved density parameters, stability evidence, clusters
(id, centroid-nearest representative, shared route, member count), over-broad
routes, noise (orphan) nodes, and outliers, each tuple truncated with its
unbounded `*_total`. `clustering.answer` and `over_broad_routes` add the
bounded presentation boundary over the unchanged `clusters` fit; an over-broad
route is one whose clustered members span more than one cluster. Nothing is a
claim, assignment, or authority.

`tangle digest NODE` is the graph-only companion and stays on the fast path.
`index.digest` resolves a bare ID or full name and bounds the unresolved direct
members whose primary `Parent`/`Area` resolves to it, ordered by priority then
id, printing each member's own summary and `next` with no generative summary and
no heavy import.

`tangle similar` is unchanged: it already used the embedding rerank behind
the seam, and the absent path stays byte-identical to the lexical baseline.

`src/tangle/clustering.py`, `src/tangle/index.py`, `src/tangle/cli.py`,
and `src/tangle/main.py` carry the change; `tests/test_cluster_verbs.py`
covers the absent and present paths, `tests/test_verb_benchmark.py` and
`benchmark/verb-baseline.json` add the two gated verbs. The default offline
suite drives the absent paths through the real command (including a fresh
interpreter asserting no heavy module loads) and the derived answer with
deterministic stand-in clusterer and reducer functions; a real-runtime test is
skipped unless the extra is present.

Evidence. With the capability absent, `tangle clusters` printed the advisory
line and `clusters: "capability absent"` at exit 0, `tangle digest
IDX-001-execution-graph --limit 3` was bounded TOON over the two unresolved
members, and `tangle similar` with a failing provider was byte-identical to
the no-provider lexical run (`diff` reported no difference). In the isolated
extra environment the live vault answered through the native provider: chosen
reduced UMAP space (`min_cluster_size=6`, `min_samples=2`), 8 clusters, 7
over-broad routes (top `IDX-001` across 8 clusters), 7 noise nodes, and 0
outliers, bounded to `--limit 4`.

`tangle check nodes`, `tangle index nodes`, `make test`, and
`make verb-benchmark` pass. `similar`'s default answer did not regress. No
`context_rev` bump was needed: no node pins this one. Resolving this node
advanced the parent's `next` to [[TAS-094-clustering-quality-gate]].
