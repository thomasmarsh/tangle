---
context_rev: 1
status: resolved
priority: P2
updated: 2026-09-15T16:01:05Z
summary: Enable pytest-xdist in the default gate.
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

# Result

Landed pytest-xdist for the default gate. Added `pytest-xdist>=3.6` to the
`dev` dependency group; `uv.lock` resolves `pytest-xdist 3.8.0` and
`execnet 2.1.2`. `make test` now runs the Python suite as
`uv run pytest -q -n auto` (4 workers on this 4-CPU host);
`make test-benchmarks` stays serial.

Wall times against the 134.8s baseline:

- pytest phase: 109.3s serial -> 43.3s, 44.8s and 45.1s on three consecutive
  green `make test` runs (a fourth run 52.0s), about 2.1-2.5x.
- full `make test` (release-time measurement): 99s vs 134.8s baseline. The gate
  is now floored by `tests/install.sh` (~67s), which runs concurrently.
- Three consecutive green runs recorded (794 passed, 3 skipped each) with no
  new flakiness and no repo or vault mutation.
