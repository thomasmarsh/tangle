---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Establish causal evidence that Tangle memory improves agent decisions at acceptable cost.
---

Area [[IDX-001-execution-graph]].

# Context

Depends on [[THO-018-evaluate-braintree-external-episodic-memory-agai]] at context_rev 2.

# Outcome

A reproducible evidence program determines whether selective Tangle memory improves memory-dependent engineering actions over credible baselines, and admits new memory mechanisms only when held-out correctness and cost evidence support them.

# Done when

- The evaluation foundation, causal comparison, diagnostics, retrieval, consolidation and transfer, interference and forgetting, uncertainty and security, and confirmatory workstreams are resolved or explicitly disposed.
- The final report separates supported claims from rejected or untested claims and records every resulting contract decision.
- The plain graph check and the applicable offline and benchmark suites pass.

# Result

The agent-memory evaluation program is complete. Every direct child is resolved
or disposed: the evaluation foundation (TAS-121) and its corpus, schema, and
claim subcontracts; the five-arm causal comparison (TAS-122) and its pipeline
diagnostics (TAS-123); the retrieval (TAS-124), consolidation and transfer
(TAS-125), and interference and forgetting (TAS-126) workstreams, retired on
zero diagnostic labels; the uncertainty, provenance, and authority workstream
(TAS-127); the corpus separability repairs (TAS-151, TAS-152); and the
confirmatory held-out evaluation (TAS-128).

`research/agent-memory-confirmatory-report.md` is the final report. It
separates supported, rejected, exploratory, and untested claims and records the
contract decision: the broad causal claim is rejected on the frozen held-out
split, no new mechanism is adopted, and the existing Markdown and Git evidence
contract stands, with an explicit reversal criterion. Development-split results
remain exploratory.

`tangle check`, `make test` (646 passed, 3 skipped), and
`make test-benchmarks` (79 passed) pass.
