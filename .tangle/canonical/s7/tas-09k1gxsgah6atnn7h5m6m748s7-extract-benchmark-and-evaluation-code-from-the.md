---
context_rev: 1
status: proposed
updated: 2026-09-16T00:15:58Z
summary: Extract benchmark and evaluation code from the core package.
next: Inventory the benchmark, memory-evaluation, storage-comparison, packaging, and entry-point dependency closure.
---

Parent [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]].

# Context

ARCH.md sections 2, 6, and 7.1 distinguish the shipping graph runtime from research infrastructure. Before this correction, benchmark, `memory_*`, and `storage_comparison.py` modules occupied 11,514 of 23,938 lines under `src/tangle/`; the graph only required frozen fixtures and lazy imports, so it did not preserve the requested physical package boundary.

This node owns the relocation and distribution outcome for `*benchmark.py`, `memory_*.py`, and `storage_comparison.py`, including their internal research-only support. It does not own the optional search implementation in `clustering.py`, `provider.py`, `reduction.py`, or `semantic.py`; that is a separate optional-layer outcome. Moving files is insufficient unless the default installed artifact excludes the research implementation and ordinary core execution has no import edge into it.

Gates my artifact enters: package and entry-point declarations in `pyproject.toml`; `tests/test_scaffold.py` and `tests/install.sh` for installed payloads; default ruff, mypy, and pytest discovery; the focused benchmark and memory suites; and `make test-benchmarks`.

# Outcome

Benchmark, memory-evaluation, and storage-comparison implementation lives in a clearly named development-only research package or tree outside `src/tangle/`; the default Tangle installation contains the core runtime but not the research implementation, while repository benchmark workflows retain an explicit supported entry path.

# Done when

- An inventory classifies every benchmark, `memory_*`, and storage-comparison module plus its imports as research-owned, core-owned, or a deliberately shared primitive, with a recorded reason for every file retained in `src/tangle/`.
- Research-owned implementation is moved out of `src/tangle/`, imports and entry points are updated, and obsolete forwarding modules are deleted unless a time-bounded compatibility requirement names why one remains.
- The default build and installer exclude the research implementation and dependencies; an observable negative test proves an ordinary installed command cannot import the research package.
- Repository benchmark commands either continue through a development-only entry point with compatible help and errors or are deliberately replaced with documented commands; unavailable research commands in the ordinary installation fail explicitly rather than importing or installing on demand.
- Frozen benchmark fixtures and provenance remain reproducible across the move, and generated or installed fixture discovery no longer assumes that every file under `src/tangle/` is research input.
- `tangle check`, `make test`, and `make test-benchmarks` pass.

# Scoping

This is one durable distribution-boundary outcome, executed in coherent slices: inventory and destination contract; research package scaffold with one live benchmark consumer; migration of the remaining benchmark and memory modules; entry-point and installer cutover; then deletion and full verification. A file move, worker handoff, or test repair is not a child boundary.
