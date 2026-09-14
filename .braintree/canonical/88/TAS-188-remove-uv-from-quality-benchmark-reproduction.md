---
status: blocked
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Remove the uv toolchain from the quality benchmark's recorded reproduction command.
next: Obtain a live-run authorization for the authority re-record.
---

Area [[IDX-001-execution-graph]].

# Context

Depends on [[TAS-144-derived-artifact-regeneration-ownership]] at context_rev 1.
Depends on [[TAS-127-uncertainty-provenance-security]] at context_rev 1.

The round-nine launcher fix
[[TAS-166-installed-launcher-without-a-uv-cache]] removed uv from the installed
command path, but `braintree benchmark quality emit` still renders `_REPRODUCE`
from `src/braintree/quality_benchmark.py`, which names `uv run` and
`UV_PROJECT_ENVIRONMENT`.

`src/braintree/quality_benchmark.py` is one of the seven observable prompt files
the frozen `benchmark/memory-authority-result.json` measurement pins. The
derived-artifact regeneration rule states that a later change to an observable
file owes a faithful live re-record and cannot discharge it with a dry-run or a
degraded artifact. Editing the string drops nine of the thirty-six committed
samples and flips the authority decision from `keep-existing-evidence` to
`untested`, so the cleanup cannot land until the authority measurement is
re-recorded. [[TAS-127-uncertainty-provenance-security]] is the resolved owner of
that artifact.

# Outcome

The quality benchmark's recorded reproduction command names the installed
`braintree` command and no uv toolchain, and the authority artifact is a faithful
re-record at the new observable revision.

# Done when

- A new owner authorization covers a faithful live re-record of the authority
  measurement against the edited observable file.
- `benchmark/memory-authority-result.json` is re-recorded at that revision and
  `braintree benchmark authority verify` passes.
- `_REPRODUCE` in `src/braintree/quality_benchmark.py` names `braintree` without
  `uv run` or `UV_PROJECT_ENVIRONMENT`, and the committed
  `benchmark/clustering-quality-evidence.json` matches it.
- `make test` passes.

# Blocked

Blocked by: a new owner authorization for a live authority re-record; the
2026-09-13 standing authorization covered only the recorded run.

Unblocks when: the owner authorizes a faithful live re-record against the edited
observable file.
