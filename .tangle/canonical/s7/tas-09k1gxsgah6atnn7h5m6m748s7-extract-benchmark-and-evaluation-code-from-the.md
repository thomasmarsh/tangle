---
context_rev: 2
status: active
updated: 2026-09-16T02:04:44Z
summary: Extract benchmark and evaluation code from the core package.
next: Move the verb benchmark through the development-only research package and repository entry point.
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

# Result

Inventory completed from the live source, packaging, installer, help, fixture,
and test closure. The development-only destination is
`research/tangle_research/`; repository workflows may import and execute it,
but the default distribution and installer must not include it.

Research-owned modules to move are `behavioral_benchmark.py`,
`embedding_benchmark.py`, `quality_benchmark.py`, `staged_benchmark.py`,
`token_benchmark.py`, `verb_benchmark.py`, `storage_comparison.py`, and all
seven `memory_*` modules: `memory_authority.py`, `memory_causal.py`,
`memory_contract.py`, `memory_corpus.py`, `memory_diagnostics.py`,
`memory_pilot.py`, and `memory_scenario.py`. The corresponding benchmark and
memory tests, repository runners under `scripts/`, benchmark evidence under
`benchmark/`, and memory-evaluation documents under `research/` are
research-owned consumers or evidence rather than installed runtime.

Core-owned modules retained in `src/tangle/` are `main.py` and `help.py`
because the installed command and its explicit unavailable-research behavior
live there; `graph_check.py`, `index.py`, `vault.py`, `sidecar.py`, `store.py`,
`migration.py`, and `toon.py` because they are production behavior or storage
primitives measured by the research harnesses; and `cli.py`, `revision.py`, and
the remaining runtime modules because frozen evidence evaluates that shipped
behavior rather than owning it. `pyproject.toml` remains the default
distribution authority, `scripts/install.sh` remains the core installer, and
`Makefile` is a deliberately shared repository-only automation surface.
`clustering.py`, `provider.py`, `reduction.py`, and `semantic.py` stay in place
under the separately owned optional-search boundary.

Current closure evidence: `src/tangle/main.py` eagerly imports and dispatches
the research modules; `uv_build` packages all of `src/tangle`; the installer
copies all of that directory and does not remove stale moved modules; and
`tests/install.sh` assumes each source file is installed. Frozen
`research/fixtures/token-install/**` and
`research/fixtures/memory-eval/checkout/**` copies preserve their historic
layout and hashes and must remain byte-identical. `behavioral_benchmark.py` is
the first coherent slice because it has no in-process core imports; its live
consumer, repository command, installed unavailable-command path, default
artifact exclusion, stale-install cleanup, and focused tests move together.

Commit `dca8d70` completed that first slice. It moved
`behavioral_benchmark.py` to `research/tangle_research/` without a forwarding
module, made `make diagnostic-benchmark` the supported repository execution
path, removed the core import and dispatch, and made the installed command fail
explicitly with repository guidance. The default wheel contained zero
`tangle_research` entries and no `tangle/behavioral_benchmark.py` while retaining
the core runtime. Installer coverage proved both research imports unavailable
in an ordinary installation and removed a seeded stale copy on upgrade.

Fresh verification passed Ruff, mypy, 129 scaffold and skill tests, six
behavioral benchmark tests, `make diagnostic-benchmark`, `make test-install`,
and `tangle check` over 283 nodes. The final reviewer returned `OK` with no
findings, and the reviewed and staged patches were byte-identical. Benchmark
baselines, frozen fixtures, provenance, and the four optional-search-owned
modules were unchanged.

Remaining scope is the relocation and command/install cutover for the verb,
token, staged, embedding, and quality benchmarks; storage comparison; all
seven memory-evaluation modules and their runners; fixture discovery assumptions;
and the final `make test` and `make test-benchmarks` acceptance gates.
