---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Deleted the seven shell suites the pytest ports superseded and run the remaining checks concurrently, cutting `make test` from ~48s to ~22s.
---

# Context

Area [[IDX-001-execution-graph]].

`make test` took about 48 seconds: pytest ~15s, the nine shell suites ~31s, and
the rest under a second. Profiling showed the shells are process-spawn bound and
that `tests/bt-foundation.sh`, `tests/bt-index.sh`, `tests/bt-verification.sh`,
`tests/graph-check.sh`, `tests/behavioral-benchmark.sh`,
`tests/storage-comparison.sh`, and `tests/token-benchmark.sh` were all superseded
by explicit pytest ports, so the default gate ran the same coverage twice.
`tests/install.sh` and `tests/worktree-parallel.sh` are not ported and stay.

# Outcome

`make test` runs each coverage once, executes the independent checks
concurrently, and stays under half its previous wall time without losing
behavioral coverage.

# Done when

- The seven superseded shell suites are removed and the shell launchers they
  alone exercised have a cheap pytest smoke test.
- Every token-benchmark case the shell suite covered exists in pytest.
- The two storage-comparison tests share one run of the comparison.
- The `Makefile` test target runs pytest, the surviving shell suites, and lint
  concurrently, and still fails when any check fails.
- `make test` passes.

# Result

Removed the seven mirrored shell suites and kept the two unported end-to-end
screens, `tests/install.sh` and `tests/worktree-parallel.sh`. Coverage moved
into pytest intact:

- `tests/test_launchers.py` statically checks that every `scripts/*` launcher
  execs the right `braintree` module and runs the cheap ones, replacing the only
  coverage the deleted suites gave the historical launcher path.
- `tests/test_token_benchmark.py` gained the three checks the shell suite held
  alone: the `routine-mutation` fixture shape, a valid Reading-prefix recording,
  and rejection of a telemetry-only incomplete stream.
- `tests/test_storage_comparison.py::test_default_run_skips_verification` now
  stubs `_result_for`, so it asserts the flag handling without rebuilding the
  four disposable Git fixtures; the `--verify` integration test still runs the
  real comparison once.
- `Makefile` runs `ruff`, `mypy`, `pytest`, and the two surviving shell suites
  concurrently, waits on every job, and fails the target when any job fails.

Evidence:

- `make test` passes: 139 pytest tests, `ruff`, strict `mypy`, `install tests:
  passed`, and all six `worktree-parallel` scenarios.
- Wall time fell from ~47.8s to ~21.7s on the same host; the removed suites were
  ~14.6s of the ~36.7s of measured CPU work, and the remaining suites now overlap.
- The deleted suites were duplicates by construction: their docstrings say
  "Pytest port of ``tests/<name>.sh``" and the pytest tests are supersets (for
  example `test_bt_foundation.py` adds seed/reindex cases and avoids the shell
  suite's `sleep 1` by expiring the lease directly).
