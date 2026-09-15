---
context_rev: 1
priority: P3
status: proposed
updated: 2026-09-15T14:36:52Z
summary: Isolate benchmark and memory-evaluation dispatch from main.py's command set.
next: Move the benchmark and memory_* imports behind lazy or deferred dispatch so ordinary command execution never loads development-only modules.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

`src/tangle/main.py` imports `behavioral_benchmark`, `embedding_benchmark`, `memory_authority`, `memory_causal`, `memory_corpus`, `memory_diagnostics`, `memory_pilot`, `quality_benchmark`, `staged_benchmark`, `token_benchmark`, and `verb_benchmark` unconditionally at module load, alongside ordinary commands like `node`, `check`, and `packet`. Every ordinary invocation pays the import cost of the full development-benchmark surface.

# Outcome

Ordinary command dispatch no longer imports benchmark or memory-evaluation modules; they load only when a `benchmark <subcommand>` is actually invoked.

# Done when

- `main.py`'s top-level imports no longer include the benchmark/memory_* modules; the `_BENCHMARK_COMMANDS` dispatch table resolves them lazily (e.g. import inside `_benchmark` or a deferred mapping).
- Every existing `benchmark <subcommand>` invocation behaves identically, including its help and error text.
- A test asserts an ordinary command (e.g. `tangle check --help`) does not import a named benchmark module (a negative assertion with a falsification probe per the authoring reference), so the isolation cannot silently regress.
- `tangle check` and `make test` pass.
