---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Add an optional, derived, non-authoritative semantic retrieval layer behind the capability boundary.
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

# Result

`src/tangle/semantic.py` owns the capability boundary as one seam behind
`tangle similar`. `semantic.probe()` reads the command in
`TANGLE_SEMANTIC_PROVIDER`; an unset or blank value means the capability is absent
and no process runs. A command that fails, times out, or returns a malformed or
empty vector is also absent, so an unhealthy provider degrades instead of
failing the command.

The provider protocol is a command string that reads a JSON array of texts on
stdin and writes a JSON array of equal-width numeric vectors on stdout; it is
split with `shlex` and never run through a shell. `semantic.vectors()` reads
cached vectors from the disposable `semantic_cache` table keyed by provider
identity and content hash, embeds only the missing hashes in one call, and
stores the fresh vectors; a wrong-width vector or a failed call returns `None`.

`index.similar(root, text, limit, provider=None, connection=None)` keeps the
lexical baseline exactly as it was and reranks by the provider's embedding
cosine only when a probed provider and a sidecar connection are supplied. Any
semantic failure falls back to the lexical ranking as a whole, so the two
metrics never mix. `cli` enables the path from the environment and opens the
sidecar only when `semantic.probe()` returns a provider; a sidecar that cannot
open also degrades to lexical. Reranking `search` is deliberately out of scope
here: only the documented near-duplicate path is wired.

Evidence: `tests/test_semantic.py` proves a synonym paraphrase scores zero
lexically and tops the semantic ranking; probe failure and batch failure both
return the lexical answer byte for byte; a warm run embeds nothing new while a
changed node is the only re-embed (2 provider calls cold, 1 warm, and 1 for the
changed content hash after); and the cache holds one row per provider and
content hash. The composite token fixture mirrors the installed package, so
adding `semantic.py` moved its file count from 67 to 68 and
`tests/test_token_benchmark.py` now pins the new count. `uv run tangle check
nodes` passes (97 nodes), `make
verb-benchmark` passes with `benchmark/verb-baseline.json` unchanged (no gated
verb uses `similar`), and `make test` passes.

Comparison and decision: the agent-visible cost is one `tangle similar` call
with an identical output shape with or without a provider, so agent round trips
and tokens are unchanged; the only added cost is provider process calls (0 with
no provider, 2 cold and 1 warm with one), and every vector is cached by content
hash. No real embedding provider or live session was available offline, so no
live token A/B was possible and the deterministic round-trip and recall
comparison above is the basis. Decision: **keep** the optional seam, default
off. Nothing semantic is shipped or required, and any provider deployed later
must repeat the comparison with live telemetry before its value is claimed.
