---
status: resolved
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: Tangle has strong memory governance but lacks causal evidence of downstream agent utility.
---

Area [[IDX-001-execution-graph]].

# Question

How does Tangle’s Markdown-canonical execution memory compare with research on external agent memory when model-weight and new-network-architecture approaches are excluded?

# Context

Reassesses [[THO-002-fit-for-purpose-assessment]] and the evaluation program represented by [[TAS-015-behavioral-benchmark]] and [[TAS-020-token-benchmark]].

The scope is information an agent cannot reliably reconstruct from repository contents, system prompts, or current environment state. Retrieval and in-context presentation are in scope; modifying model weights or inference-network architecture is not.

# Hypothesis

Tangle has strong theoretical foundations in selective episodic retention, temporal/provenance-aware graph memory, and bounded retrieval, but has evaluated storage mechanics and token cost more thoroughly than long-horizon decision utility, retrieval policy, memory quality, and resistance to stale or misleading memories.

# Conclusion

Tangle is best classified as selective external execution memory: prospective task state, semantic definitions and decisions, reflective thoughts and feedback, procedural skill text, and compressed episodic results. Its admission boundary, Markdown authority, lifecycle, semantic revision pins, and bounded graph queries align well with external-memory theory and are more governable than opaque transcript or vector stores.

The proposed “store only what cannot be reconstructed” rule is useful but too strict. Retain the existing broader threshold: preserve decision-relevant historical state that is unavailable, unreliable, ambiguous, or disproportionately costly to reacquire when its expected future value exceeds write, retrieval, interference, staleness, and review costs.

The primary gap is causal evidence. Existing benchmarks establish structural correctness, storage and merge behavior, retrieval proxies, and some token effects; they do not yet show that Tangle improves memory-dependent engineering actions over repository-only, raw-history, flat-memory, and oracle baselines. Admission quality, implicit retrieval, outcome-based consolidation, uncertainty and conflict, forgetting, provenance, and procedural transfer remain unevaluated.

# Result

The literature-backed assessment, scorecard, public-benchmark fit analysis, metrics, and staged evaluation program are recorded in [`research/agent-memory-theory-evaluation.md`](../../research/agent-memory-theory-evaluation.md).
