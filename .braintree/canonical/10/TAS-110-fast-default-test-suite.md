---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Keep the default pytest suite fast by running benchmark verification opt-in and caching repeated
---

Area [[IDX-001-execution-graph]].

# Context

The default pytest suite takes about 83 seconds. Most of that is end-to-end benchmark verification: `test_quality_benchmark.py` (24 s) and `test_embedding_benchmark.py` (7 s) recompute full-corpus retrieval over the committed 118-document corpus, and `test_storage_comparison.py` and `test_verb_benchmark.py` rebuild four Git fixtures and spawn the verb gate. That work duplicates the benchmarks own `--verify` commands and `make` targets, so it does not belong in the fast unit suite.

# Outcome

`make test` (the default pytest run) covers the unit and CLI contract tests in well under a minute, benchmark verification runs explicitly, and the shared token-counting hot spot no longer re-tokenizes the same text for every ranked pair.

# Done when

- A `benchmark` pytest marker is excluded by default and the benchmark modules are marked.
- `make test-benchmarks` runs the marked verification and passes.
- `index._token_counts` is cached so repeated lexical ranking does not re-tokenize.
- The default suite runs in well under a minute and `make test` passes.

# Result

Benchmark verification is opt-in and the shared tokenization is cached.

- `pyproject.toml` excludes the `benchmark` marker by default and declares it; seven benchmark test modules carry `pytestmark = pytest.mark.benchmark`.
- `make test-benchmarks` runs `pytest -m benchmark`; `make test` stays the fast gate, and `AGENTS.md` names the extra target for benchmark changes.
- `index._token_counts` is `lru_cache`d, so repeated lexical ranking no longer re-tokenizes the same text.

Evidence: the default suite runs 356 tests in about 40 s with 79 benchmark tests deselected, and `make test-benchmarks` runs 79 tests in about 19 s; both exit 0.
