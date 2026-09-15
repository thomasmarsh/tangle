---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Make a semantic install zero-config by defaulting the provider in the launcher.
---

Parent [[TAS-068-direct-answer-surface]].

# Context

Depends on [[TAS-106-let-the-installer-opt-into-the-optional-semantic]] at context_rev 1.

TAS-106 added the `--semantic` installer opt-in, but a semantic install still
asked the operator to export `TANGLE_SEMANTIC_PROVIDER` before `tangle clusters`
worked. The installer should leave a requested capability ready to use.

# Outcome

A `--semantic` install defaults `TANGLE_SEMANTIC_PROVIDER` to
`tangle semantic embed` in the generated launcher when the operator has not
set one, so `tangle clusters` and semantic `tangle similar` work with no
further configuration. An explicit operator value, including an empty one, is
respected.

# Done when

The generated semantic launcher defaults the provider only when it is unset,
respects an explicit value and an empty value, the install test proves all three
cases offline, the README states the zero-config behavior, and `make test`
passes.

# Result

The generated semantic launcher now defaults `TANGLE_SEMANTIC_PROVIDER` to
`tangle semantic embed` when it is unset, exports it, and leaves an operator
value untouched; it also still requests the extra. A plain launcher is unchanged.
`tests/install.sh` drives the launcher with a fake `uv` that reads the
environment and proves the default, an override, an explicit empty value, and
the plain unset case offline. The README states the zero-config default and the
override. `sh tests/install.sh`, `tangle check nodes`, and `make test`
(438 passed) all passed.
