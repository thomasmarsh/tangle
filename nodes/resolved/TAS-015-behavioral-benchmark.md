---
context_rev: 3
priority: P1
updated: 2026-09-10T21:19:50Z
summary: Reframed deterministic behavioral work as secondary diagnostics; token telemetry is the benchmark objective.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

The existing synthetic benchmark establishes file size, query latency, mutation count, and contention characteristics. It does not establish that a fresh agent can recover the correct current decision or execution frontier from an imprecise prompt months later.

# Intended change

Add evaluations in which a fresh agent must resume an area from a vague topic, distinguish current knowledge from superseded decisions, reconcile only relevant dependencies, and state the next executable action. Measure correctness, files and bytes or tokens read, tool calls, stale false positives and negatives, orphan discovery, and behavior after cosmetic edits, semantic changes, status moves, and concurrent node creation.

# Result

Added `scripts/behavioral-benchmark.rb`, tracked deterministic expectations, and an observable test. Temporary 100- and 1,000-node fixtures exercise cold P0 resumption, superseded-versus-current decision selection, revision-pinned dependency staleness, and orphan discovery. It reports compact deterministic work metrics and advisory timings without network access or third-party packages.

Those metrics are secondary filesystem diagnostics only: they cannot proxy
actual model-token consumption. `make diagnostic-benchmark` now names that
scope explicitly. [[TAS-020-token-benchmark]] supplies the primary
correctness-gated token protocol.
