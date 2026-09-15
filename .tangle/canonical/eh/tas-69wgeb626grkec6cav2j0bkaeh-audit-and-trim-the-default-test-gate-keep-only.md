---
context_rev: 1
status: proposed
priority: P2
updated: 2026-09-15T15:25:52Z
summary: Audit and trim the default test gate; keep only distinct load-bearing tests, then parallelize.
next: "[[tas-1tawqxsrvyby2qwv7gzsbqvb11-drop-committed-data-qa-and-prose-agreement]]"
---

Area [[IDX-001-execution-graph]].

# Context

Measured baseline for the default gate: make test 134.8s; pytest serial 109.3s
(851 passed, 3 skipped, 80 benchmark deselected); tests/install.sh 67.1s;
tests/worktree-parallel.sh 3.2s. The suite makes 311 run_tangle subprocess
spawns and the 40 slowest tests are only 43.8s, so cost is a spawn-bound long
tail rather than a few hot tests. A pytest-xdist probe ran green at -n 4
(about 3x) across five repeats with no repo or vault mutation, so intra-suite
parallelism is available but is not the priority: cutting non-load-bearing
tests comes first.

# Outcome

The default make test gate runs only tests that each protect a distinct product
guarantee; redundant, tautological, non-hermetic, and over-expensive tests are
consolidated, cheapened, or retired; intra-suite parallelism amplifies the
reduction rather than masking it.

# Done when

- Each removal or consolidation cites a named surviving guarantee or a cheaper
  equivalent assertion.
- The audit cut list is executed.
- make test stays green and its wall time is materially reduced.
