---
context_rev: 1
priority: P1
updated: 2026-09-12T17:22:00Z
summary: Evaluate off-the-shelf Hugging Face sentence-embedding models and Python inference runtimes, then settle a default and a fallback; no model is trained.
next: Benchmark the candidate off-the-shelf embedding models on a fixed node corpus.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Gated on [[TAS-088-optional-embedding-extra]].

We do not have training infrastructure and will not train or fine-tune a model.
The choice is which published model and which inference runtime to use, and
whether their retrieval quality earns a place ahead of the existing lexical
`braintree similar` baseline ([[TAS-075-structured-search-and-admission]]).

# Outcome

A documented default embedding model, a documented fallback model, and a chosen
in-process inference runtime, each with version pins and the evidence that led
to the choice.

# Done when

- The evaluation corpus is fixed and committed: paraphrase and near-duplicate
  probes derived from the vault's own link structure and resolved duplicate
  history, with held-out positives and negatives.
- Candidate off-the-shelf models are compared, at least
  `sentence-transformers/all-MiniLM-L6-v2`, `BAAI/bge-small-en-v1.5`,
  `thenlper/gte-small`, `intfloat/e5-small-v2`, `nomic-ai/nomic-embed-text-v1.5`,
  and `Snowflake/snowflake-arctic-embed-s`, against the lexical baseline.
- Candidate runtimes are compared: sentence-transformers on CPU torch versus an
  ONNX-runtime path such as fastembed or optimum.
- Metrics include retrieval quality (MRR and recall@k), model and cache size,
  cold-start latency, per-node embedding cost, license, and offline
  availability.
- A default, a fallback, and the runtime are chosen and recorded here with
  rationale; no model is trained or fine-tuned.
- `make test` passes.
