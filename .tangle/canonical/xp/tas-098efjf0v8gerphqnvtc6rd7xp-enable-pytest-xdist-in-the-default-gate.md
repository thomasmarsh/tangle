---
context_rev: 1
status: proposed
priority: P2
updated: 2026-09-15T15:07:20Z
summary: Enable pytest-xdist in the default gate.
next: Add pytest-xdist to dev dependencies and pin the worker count in the pytest invocation.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

The xdist probe ran green at -n 4 (about 3x) with no vault mutation. Land
intra-suite parallelism after hermeticity:

- Add pytest-xdist to dev dependencies.
- Run pytest with a pinned worker count after the hermeticity slice lands.
- Verify three consecutive green make test runs.

# Outcome

make test runs pytest under xdist at a pinned worker count with a materially
lower wall time and no new flakiness.

# Done when

- pytest runs under xdist in make test.
- Wall time is materially reduced.
- Three consecutive make test runs are green.
