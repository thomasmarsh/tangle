---
context_rev: 1
priority: P1
updated: 2026-09-12T17:22:00Z
summary: Ship a native Python embedding provider over the chosen off-the-shelf model that speaks the existing stdin/stdout vector protocol and caches by content hash.
next: Implement the native provider module against the chosen model and the existing probe.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Gated on [[TAS-089-embedding-model-selection]].

Depends on [[TAS-079-optional-semantic-retrieval]] at context_rev 1.

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

[[TAS-079-optional-semantic-retrieval]] defines the capability seam: a provider
is a command that reads a JSON array of texts on stdin and writes a JSON array
of equal-width vectors on stdout, cached in the disposable sidecar by provider
identity and content hash. This task supplies the native in-process provider the
project can run itself, with no Ollama or other external service.

# Outcome

A `braintree` entry point that, with the extra installed and the model cache
warm, acts as the embedding provider for the existing seam, so
`similar` and later cluster answers use real embeddings with no network access
and no required dependency.

# Done when

- A native provider command loads the selected model once per process, batches
  texts, and writes exactly the protocol's JSON vector array; it is usable as
  `BT_SEMANTIC_PROVIDER`.
- The provider reads only the local model cache and never downloads at query
  time; a missing cache degrades to the lexical baseline instead of failing.
- A malformed, empty, or wrong-width result is treated as capability absent, as
  the existing seam already does.
- The sidecar content-hash cache is exercised, so unchanged nodes are not
  re-embedded and one changed node triggers exactly one new embedding call.
- Tests use a deterministic fake model so the suite stays offline and fast, and
  `make test` passes.
