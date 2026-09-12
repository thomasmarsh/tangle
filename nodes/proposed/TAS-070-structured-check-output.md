---
context_rev: 1
priority: P1
updated: 2026-09-12T15:09:27Z
summary: Add a machine-readable `braintree check` format with stable error codes so the client branches without parsing prose.
next: Add a `--format toon` check mode that emits a stable code, node, and detail per finding.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

`braintree check` currently prints human sentences to stderr and exits `1`.
A client must parse prose to decide what to repair, which drives extra
orientation work and ad hoc shell.

# Outcome

`braintree check --format toon` emits one structured record per finding with a
stable code, the node, and detail; the default human output and exit codes are
unchanged.

# Done when

- Every existing error class maps to a documented stable code.
- The default output and exit codes are unchanged.
- Tests cover the structured format and the code mapping.
- `make test` passes.
