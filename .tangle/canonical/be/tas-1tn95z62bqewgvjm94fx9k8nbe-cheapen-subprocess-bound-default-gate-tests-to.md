---
context_rev: 1
status: resolved
priority: P3
updated: 2026-09-15T17:29:11Z
summary: Cheapen subprocess-bound default-gate tests to in-process calls.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

Subprocess-bound default-gate tests:

- Convert packet, manifest, identity, migration, and usage-error tests to
  in-process main.main or cli.main under a pinned environment.
- Keep one python -m tangle entry-point spawn per file.

# Outcome

Those tests exercise the in-process entry point under a pinned environment
rather than paying a subprocess spawn for each assertion.

# Done when

- The named tests run in-process with pinned env.
- One subprocess entry per file remains.
- make test is green.

# Result

Converted the default gate subprocess-bound CLI tests to the new in-process run_tangle_inproc fixture in tests/conftest.py, which drives tangle.main.main under monkeypatch/capsys and returns a real subprocess.CompletedProcess, so every converted assertion, exit code, and message is unchanged.
Across four verified slices the suite fell from about 303 spawned run_tangle( call sites to 43, all deliberate. The two heaviest files fell from 37.25s to 4.52s serial (test_tangle_foundation.py 82 to 4, test_tangle_index.py 85 to 4). The full default pytest gate fell from 36.0s to about 17.1s wall under pytest -n auto.
Deliberate exceptions, each because the process boundary is the guarantee: tests/test_semantic.py and tests/test_provider.py keep real spawns for fresh-interpreter provider and cache semantics; the Popen concurrency races in tests/test_index_upkeep.py and tests/test_tangle_foundation.py stay spawned; tests/test_migration.py keeps its multi-step stationarize CLI smoke; and every converted file keeps one real python -m tangle entry-point smoke.
Evidence: tangle check passed; make test green (794 passed, 3 skipped) at roughly 18-20s wall versus 36.7s before this node; no src/ or frozen-observable file changed.
