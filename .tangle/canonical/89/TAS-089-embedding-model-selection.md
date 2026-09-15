---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Choose fastembed on ONNX Runtime with all-MiniLM-L6-v2 as the default off-the-shelf embedding model and bge-small-en-v1.5 as the fallback, against a fixed committed retrieval corpus and the measured lexical baseline.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Depends on [[TAS-088-optional-embedding-extra]] at context_rev 2.

We do not have training infrastructure and will not train or fine-tune a model.
The choice is which published model and which inference runtime to use, and
whether their retrieval quality earns a place ahead of the existing lexical
`tangle similar` baseline ([[TAS-075-structured-search-and-admission]]).

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

# Result

Decision:

- Runtime: `fastembed>=0.7,<0.9` (measured 0.8.0 on ONNX Runtime 1.23.2), the
  chosen and only shipped in-process path, which is what the `semantic` extra
  installs ([[TAS-088-optional-embedding-extra]]). `sentence-transformers` on
  CPU torch was the evaluation baseline for models the fastembed registry does
  not publish and is not shipped: above `torch==2.2.2` there is no x86_64 macOS
  wheel, and `torch==2.2.2` needs `numpy<2`, which contradicts fastembed's
  `numpy>=2.1`, so the two cannot share one extra. The default and fallback
  need no torch either way.
- Default model: `sentence-transformers/all-MiniLM-L6-v2` (Apache-2.0), loaded
  through fastembed's ONNX copy `qdrant/all-MiniLM-L6-v2-onnx` at revision
  `5f1b8cd7`.
- Fallback model: `BAAI/bge-small-en-v1.5` (MIT), loaded through
  `qdrant/bge-small-en-v1.5-onnx-q` at revision `52398278`; the same model runs
  as fp32 weights through sentence-transformers at revision `5c38ec7c`.
- No training, distillation, or fine-tuning; every candidate is a published
  model read from the documented offline cache.

Rationale: the semantic layer exists to recover paraphrases the lexical
baseline misses, and MiniLM through fastembed has the best measured paraphrase
recall@5 of the ONNX models (0.4130 against 0.3261 lexical) at 19 ms per node
and a 0.11 s model load instead of the 2.77 s torch import, so it is the
cheapest model that improves the metric the layer is for. bge-small-en-v1.5
falls back to a slightly higher overall MRR (0.3352 against 0.3277) with a
smaller weight file (66.5 MB against 90.4 MB). ONNX Runtime is chosen over
sentence-transformers on torch because the whole extra then installs without
torch: on x86_64 macOS the declared `torch>=2.4` has no wheel at all, and even
the last Intel build (`torch==2.2.2`) needs `numpy<2` and `transformers<5`,
which contradicts TAS-088's `numpy>=2.0` pin, while onnxruntime installs
cleanly. fastembed's import is 0.08 s against 2.77 s for torch, which is the
cold-start cost every batch would pay.

The fixed corpus is `benchmark/embedding-corpus.json` plus
`benchmark/embedding-documents.jsonl`, frozen at vault revision `5c8faeb4`: 118
documents (the exact `summary` plus body text `tangle similar` compares) and
76 probes. Paraphrase probes come from canonical context edges, where the
dependent's summary is the query and the dependency it names is the positive and
the dependent is excluded; near-duplicate probes come from the resolved
near-duplicate history, 30 resolved pairs whose full text is nearly identical,
one used as the query and the other as the positive. Each probe records the
lexical baseline's three nearest non-positive documents as hard negatives, and
positives split deterministically by digest into `dev` (32) and `heldout` (44),
so a positive is held out in exactly one split.

Measured comparison (whole set, 76 probes, 118 documents; MRR and recall@k
computed over every document, host macOS 13.7.8 x86_64, Python 3.12.14):

```text
results{model,runtime,mrr,recall@1,recall@5,recall@10,paraphrase_mrr,paraphrase_recall@5,ms_per_node,weight_mb,import_s,load_s,license,offline}:
  "lexical baseline","-",0.3441,0.1579,0.5789,0.7105,0.1866,0.3261,-,-,-,-,-,-
  "all-MiniLM-L6-v2","fastembed",0.3277,0.1579,0.5526,0.6447,0.2532,0.4130,19.1,90.4,0.08,0.11,apache-2.0,true
  "bge-small-en-v1.5","fastembed",0.3352,0.1842,0.5526,0.6842,0.2259,0.3696,201.0,66.5,0.00,0.21,mit,true
  "all-MiniLM-L6-v2","sentence-transformers",0.3458,0.2105,0.4737,0.6316,0.2248,0.2826,27.7,90.9,2.77,1.29,apache-2.0,true
  "bge-small-en-v1.5","sentence-transformers",0.3497,0.1974,0.5395,0.6711,0.2292,0.3478,116.0,133.5,-,0.97,mit,true
  "gte-small","sentence-transformers",0.3616,0.1974,0.5789,0.7105,0.2346,0.4130,125.0,66.7,-,0.97,mit,true
  "e5-small-v2","sentence-transformers",0.3175,0.1974,0.4342,0.6579,0.2184,0.3261,115.4,133.5,-,0.98,mit,true
  "nomic-embed-text-v1.5","sentence-transformers",0.3796,0.2368,0.5526,0.6842,0.2734,0.4130,1178.6,546.9,-,2.54,apache-2.0,true
  "snowflake-arctic-embed-s","sentence-transformers",0.3109,0.1842,0.4737,0.5921,0.2193,0.3261,145.0,132.9,-,0.99,apache-2.0,true
```

Near-duplicate recall is already solved lexically (lexical MRR 0.5856 and
recall@5 0.9667 against a best candidate of 0.5564 and 0.8333), so the whole-set
numbers are dominated by a family the lexical baseline wins; the paraphrase
family is where the semantic layer earns its place.

Recorded negatives, exactly as measured:

- `nomic-ai/nomic-embed-text-v1.5` has the best quality of all candidates (MRR
  0.3796, paraphrase MRR 0.2734) but costs 1179 ms per node, 546.9 MB of
  weights, 1.1 GB of cache, and `trust_remote_code` plus `einops`; it is not the
  default because it is 62x MiniLM's per-node cost for +0.05 overall MRR and no
  recall@5 gain at all (0.5526 each, and 0.4130 each on the paraphrase family).
- `thenlper/gte-small` is the best sentence-transformers candidate (MRR 0.3616,
  recall@5 0.5789) and the smallest (66.7 MB), but fastembed's registry does not
  publish it, so choosing it would require the torch path the extra cannot
  carry.
- fastembed's registry lists `nomic-ai/nomic-embed-text-v1.5` and
  `Snowflake/snowflake-arctic-embed-s` but loading them fails with
  `ONNXRuntimeError: NO_SUCHFILE` because the resolved snapshots hold no ONNX
  weights, so those candidates are unavailable on the ONNX path in 0.8.0 rather
  than silently substituted.
- `intfloat/e5-small-v2` applies its required `query:`/`passage:` prefixes and
  still trails the field (MRR 0.3175, recall@5 0.4342), and
  `Snowflake/snowflake-arctic-embed-s` is last (MRR 0.3109); fastembed lists
  neither e5-small-v2 nor gte-small.
- No candidate beats the lexical baseline on the held-out split; the lexical
  `tangle similar` answer stays the correctness reference and the semantic
  layer adds paraphrase recall, not a replacement.

Smoke evidence (one model on a 12-probe strided subset, before the full run):

```sh
uv run tangle benchmark embedding corpus --verify
uv run tangle benchmark embedding run --models sentence-transformers/all-MiniLM-L6-v2 \
  --runtimes sentence-transformers --probes 12 --time-budget 900
```

```text
smoke{probes,mrr,recall@1,recall@5,recall@10}:
  "lexical",12,0.2846,0.0833,0.5833,0.8333
  "all-MiniLM-L6-v2",12,0.3900,0.2500,0.5000,0.7500
smoke{family,probes,mrr,recall@5}: "lexical-paraphrase",7,0.1260,0.2857 | "minilm-paraphrase",7,0.2162,0.1429
```

The smoke held, so the batch was scaled: all six candidates across both runtimes,
76 probes and 118 documents, bounded by `--time-budget 5400` and writing
`benchmark/embedding-evidence.json` (383 s, nothing on the interactive path).
Every candidate is listed there with its status, license, prefixes, resolved
weight revision, weight and cache bytes, import/load latency, per-node and
per-query cost, offline re-load verdict, and MRR/recall@k for the whole set, the
two splits, and both families.

`src/tangle/embedding_benchmark.py` is the harness behind `tangle
benchmark embedding corpus|run`, registered in `main.py` and importing no heavy
module at top level: the loaders import a runtime only when a batch runs, and
`run` records a missing extra as an unavailable candidate instead of raising.
`tests/test_embedding_benchmark.py` proves offline that the harness ranks with
the shipped lexical metric (a vector embedder equal to it reproduces the
baseline exactly), that the committed corpus verifies, that metrics are
computed per split and family, that an absent extra or an unlisted model is
recorded rather than dropped, and that a fresh interpreter running `--help`,
`benchmark embedding --help`, and `corpus --verify` imports no heavy module.
`tangle check nodes`, `tangle index nodes`, and `make test` pass; the
corpus and the evidence are committed so [[TAS-094-clustering-quality-gate]] can
re-run the same comparison. Adding a source module also moved the composite
local-fixture file count the token benchmark asserts from 69 to 70, updated in
the same change.

Resolving this node pinned the TAS-088 extra it consumed and advanced the
parent's `next` to [[TAS-090-native-embedding-provider]].

Reversal: commit `8c24cc5 feat(benchmark): select off-the-shelf embedding model
and runtime` recorded `sentence-transformers>=3.0` on CPU torch as remaining in
the `semantic` extra as a compatibility runtime. That claim is replaced here:
torch and sentence-transformers were an evaluation baseline only and do not ship
(TAS-088 now pins an extra without them). The decision is unchanged: default
fastembed `sentence-transformers/all-MiniLM-L6-v2`, fallback fastembed
`BAAI/bge-small-en-v1.5`.
