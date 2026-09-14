---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Ship a native Python embedding provider over the chosen off-the-shelf model that speaks the existing stdin/stdout vector protocol and caches by content hash.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Depends on [[TAS-089-embedding-model-selection]] at context_rev 1.

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

# Result

`src/braintree/provider.py` is the shipped provider, reached as
`braintree semantic embed` through the new `semantic` group in `main.py`. It
reads a JSON array of texts on stdin and writes only the protocol's JSON array
of equal-width vectors on stdout, loads the selected model exactly once per
process, and embeds in bounded batches of 32 texts, so a whole `similar`
invocation is one process and one load per provider call.

The default is `sentence-transformers/all-MiniLM-L6-v2` and it falls back once
to `BAAI/bge-small-en-v1.5` when the default cannot load. `BT_EMBEDDING_MODEL`
selects the model and `--model NAME` overrides the environment. The flag exists
because the sidecar cache key is the provider command string the seam is given
(`semantic._provider_key`), so a different model must be pinnable in
`BT_SEMANTIC_PROVIDER`; otherwise both 384-dimensional models would share cache
rows.

Offline is enforced before the runtime loads: `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` are set and the load passes `local_files_only=True`
against `semantic.model_cache()` (`BT_MODEL_CACHE`, else `HF_HOME`, else
`~/.cache/huggingface`), so a cache the operator has not pre-fetched exits
non-zero instead of downloading. A missing extra, malformed stdin, a wrong
vector count, an empty vector, and vectors of differing widths take the same
non-zero path with a stderr diagnostic and an empty stdout, which is exactly the
absence `semantic.probe` already reports as the lexical baseline.
`semantic._invoke` and `semantic.vectors` are unchanged. Fastembed is imported
lazily inside the handler, so `check`, `frontier`, `similar`, and every other
interactive verb stay heavy-import-free and `[project].dependencies` stays `[]`;
no pin changed, so `pyproject.toml` and `uv.lock` are untouched.

Evidence. `tests/test_provider.py` drives the command with a deterministic fake
model installed over its one load seam, so the suite imports no fastembed and
downloads nothing. It pins: stdout carries only the JSON vector array; one text
batch per request (one load); 70 texts are one load and batches of 32/32/6 in
order; `--model` beats `BT_EMBEDDING_MODEL`, which beats the default; the
default falls back to bge-small exactly once and an explicitly chosen model does
not fall back; an unloadable default and fallback exit 1 with empty stdout;
wrong count, empty, and ragged results raise; the sidecar cache key follows the
command string, so pinning `--model` changes it; and a fresh interpreter running
`provider --help` and `braintree semantic embed --help` loads no heavy module.
Driving the real `braintree similar` seam through the native command proves
end-to-end that it reranks a paraphrase the lexical baseline scores zero, that a
warm sidecar answers with no re-embedding at all, and that one changed node
triggers exactly one new embedding call, carrying one text.
`BT_FAKE_MODEL_MODE=unavailable` (absent extra or cold cache) and `empty` both
produce output byte-identical to the unconfigured lexical run.

The real extra smoke ran in an isolated environment, leaving the dev `.venv`
clean:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/bt-provider-venv uv sync --extra semantic
echo '["hello world","near duplicate hello world"]' | /tmp/bt-provider-venv/bin/python -m braintree semantic embed
```

It returned two 384-dimensional vectors (cosine 0.635) read from the
pre-fetched `qdrant/all-MiniLM-L6-v2-onnx` cache with no network. With
`BT_SEMANTIC_PROVIDER='/tmp/bt-provider-venv/bin/python -m braintree semantic
embed'`, `uv run braintree similar 'native in-process embedding provider for the
semantic seam' --limit 5` reranked TAS-090 at 0.5136 against the lexical 0.4590
for the same query; pointing `BT_MODEL_CACHE`
at an empty directory made the command exit 1 with empty stdout and the verb
answer the lexical baseline, byte-identical by `diff`.

`braintree check nodes`, `braintree index nodes`, `make test`, and
`make verb-benchmark` pass. Adding `src/braintree/provider.py` moved the token
benchmark's composite local-fixture file count from 70 to 71, updated in the
same change. Resolving this node advanced the parent's `next` to
[[TAS-091-manifold-reduction]].
