---
context_rev: 1
status: proposed
updated: 2026-09-15T21:14:16Z
summary: Separate research and benchmark evidence from the ordinary runtime.
next: "[[tas-1vmzcb5gewppf0y9bv7w49az1j-freeze-the-token-benchmark-s-installed-skill]]"
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md section 7.1 separates research evidence from the runtime in two moves:
move research dispatch out of ordinary startup, and snapshot historical prompt
source under research fixtures while preserving its measurements and provenance.
The runtime-dispatch half is already owned by
[[tas-3h6n5kky4qzdryvkwe1rxg1hx6-isolate-benchmark-and-memory-evaluation]];
do not duplicate it. The fixture half is the remaining work: the benchmark
corpus still treats live production source as frozen prompt content.
`census.py` names `src/tangle/cli.py` and `src/tangle/sidecar.py` as frozen
observable content in `benchmark/memory-authority-cases.json`, and
`staged_benchmark.py` embeds `SKILL.md` and `src/tangle`, so a production move
can invalidate historical evidence.

# Outcome

Benchmark and memory-evaluation harnesses read frozen in-repo fixture copies
instead of live production source, with measurements and provenance preserved,
so later slice refactoring no longer depends on the current source layout.

# Done when

- Every live production-source input of the benchmark corpus is copied into a
  frozen fixture location with recorded provenance (source revision and hash),
  and the harness reads the frozen copy.
- The committed measurements whose recording revision is recoverable re-derive from the frozen fixtures; measurements whose historical source or prompt revision is unrecoverable are retained as historical evidence and recorded with the reason.
- Ordinary startup no longer imports research or benchmark modules, or that
  half is resolved through its existing owner and cited here.

# Scoping

Decomposed into three direct children, one per independently acceptable
outcome: reconcile the runtime-dispatch half with its existing owner, freeze the
memory-evaluation corpus's live observable inputs, and freeze the token
benchmark's installed-skill fixture inputs. Each fixture child owns its own
provenance manifest and reproduction check, and the reconciliation child stays
gated on
[[tas-3h6n5kky4qzdryvkwe1rxg1hx6-isolate-benchmark-and-memory-evaluation]].
