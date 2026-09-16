---
context_rev: 2
status: proposed
updated: 2026-09-16T00:15:58Z
summary: Separate research and benchmark evidence from the ordinary runtime.
next: "[[tas-09k1gxsgah6atnn7h5m6m748s7-extract-benchmark-and-evaluation-code-from-the]]"
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md section 7.1 separates research evidence from the runtime in two moves:
move research dispatch out of ordinary startup, and snapshot historical prompt
source under research fixtures while preserving its measurements and provenance.
ARCH.md sections 2 and 6 also require a physical source boundary: benchmark,
memory-evaluation, and storage-comparison implementation is research code, not
part of the shipping `src/tangle/` package. Lazy imports are necessary but do
not satisfy that package boundary. The original decomposition omitted this
outcome, so the extraction child restores it explicitly.
The runtime-dispatch half is already owned by
[[tas-3h6n5kky4qzdryvkwe1rxg1hx6-isolate-benchmark-and-memory-evaluation]];
do not duplicate it. The fixture half is the remaining work: the benchmark
corpus still treats live production source as frozen prompt content.
`census.py` names `src/tangle/cli.py` and `src/tangle/sidecar.py` as frozen
observable content in `benchmark/memory-authority-cases.json`, and
`staged_benchmark.py` embeds `SKILL.md` and `src/tangle`, so a production move
can invalidate historical evidence.

Delegation marker: the runtime-dispatch half — ordinary startup no longer
importing the benchmark and `memory_*` modules — is delegated to
[[tas-3h6n5kky4qzdryvkwe1rxg1hx6-isolate-benchmark-and-memory-evaluation]]. Its
`# Done when` owns the lazily resolved `_BENCHMARKS` dispatch table, the
unchanged `benchmark <sub>` help and error text, and the negative-import
assertion proving an ordinary command loads no benchmark module. The delegated
surface is `behavioral_benchmark`, `embedding_benchmark`, `memory_authority`,
`memory_causal`, `memory_corpus`, `memory_diagnostics`, `memory_pilot`,
`quality_benchmark`, `staged_benchmark`, `storage_comparison`,
`token_benchmark`, and `verb_benchmark`, plus the transitively loaded
`clustering`, `reduction`, and `semantic`. Clear this marker and cite the
owner's `# Result` as this parent's integration step; the dispatch half stays
gated on that owner.

# Outcome

Benchmark and memory-evaluation harnesses read frozen in-repo fixture copies
instead of live production source, with measurements and provenance preserved,
and their implementation lives outside the shipping `tangle` package. The
ordinary runtime neither contains nor imports research implementation, so later
core refactoring is independent of benchmark source-layout constraints.

# Done when

- Every live production-source input of the benchmark corpus is copied into a
  frozen fixture location with recorded provenance (source revision and hash),
  and the harness reads the frozen copy.
- The committed measurements whose recording revision is recoverable re-derive from the frozen fixtures; measurements whose historical source or prompt revision is unrecoverable are retained as historical evidence and recorded with the reason.
- Ordinary startup no longer imports research or benchmark modules, or that
  half is resolved through its existing owner and cited here.
- Benchmark, memory-evaluation, and storage-comparison implementation is moved
  out of `src/tangle/` into a development-only research package or tree; the
  default installed runtime excludes it.
- Repository benchmark entry points and verification continue to work from the
  development environment, while an ordinary installation has an explicit,
  tested response for unavailable research commands and no core-to-research
  import edge.

# Scoping

Decomposed into four direct children, one per independently acceptable outcome:
reconcile the runtime-dispatch half with its existing owner, freeze the
memory-evaluation corpus's live observable inputs, freeze the token benchmark's
installed-skill fixture inputs, and extract the research implementation from
the shipping package. Each fixture child owns its own provenance manifest and
reproduction check; the extraction child owns the physical distribution
boundary; and the reconciliation child records the delegation to
[[tas-3h6n5kky4qzdryvkwe1rxg1hx6-isolate-benchmark-and-memory-evaluation]], on
which this parent's dispatch half remains gated.
