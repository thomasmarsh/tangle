---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Add a machine-readable `braintree check` format with stable error codes so the client branches without parsing prose.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

`braintree check` printed human sentences to stderr and exited `1`. A client
had to parse prose to decide what to repair, which drove extra orientation work
and ad hoc shell.

# Outcome

`braintree check --format toon` emits one structured record per finding with a
stable code, the node, and detail; the default human output and exit codes are
unchanged.

# Done when

- Every existing error class maps to a documented stable code.
- The default output and exit codes are unchanged.
- Tests cover the structured format and the code mapping.
- `make test` passes.

# Result

`braintree check --format toon` prints a `result`, a `nodes` count, and a
`findings[code,node,detail]` table; `--format text` is the default and keeps the
existing `error: ...` stderr lines and the `0`/`1` exit codes. Every finding
carries one of the 38 codes documented in `graph_check.FINDING_CODES` and listed
in the module docstring, covering vault, node frontmatter/lifecycle, feedback,
context-edge, index-map, and route/frontier classes. A malformed or unknown
`--format` value exits `1`.

Evidence: `tests/test_graph_check.py` exercises the toon format, the text
default, a missing/unknown format, and one mutation per code class; a coverage
test asserts the union of emitted codes equals `FINDING_CODES`. `make test`
passes.
