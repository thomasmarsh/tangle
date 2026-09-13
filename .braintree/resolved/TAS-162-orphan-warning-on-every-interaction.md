---
context_rev: 1
priority: P2
updated: 2026-09-13T23:23:54Z
summary: Report an orphaned unfinished node as a loud warning on every braintree interaction, not only in check.
---

# Context

Parent [[TAS-161-routine-interaction-zero-ceremony]].

`SKILL.md` and `braintree check` treat an orphan unfinished node as a
`route-orphan` graph-integrity error, reported only when the caller runs `check`
or the separate `--allow-orphan` gate. The direct-answer verbs a client actually
uses — `frontier`, `next`, `orient`, and `status` — can already report stale
pins, blockers, and conflicts, but they are silent about an orphan, so a vault
can carry an unreachable unfinished node through any number of interactions
without the client learning. The warning surface already exists in `orient`
(`blockers`, `conflicts`).

# Outcome

Every direct-answer interaction loudly warns about each orphaned unfinished node
without failing the interaction, while `braintree check` keeps its existing
non-zero `route-orphan` error and its `--allow-orphan` exception.

# Done when

- Every direct-answer verb surfaces the orphan warning in its output.
- The warning does not change the command's exit code or block a read-only
  answer.
- `braintree check` keeps its existing error and `--allow-orphan` behavior.
- Tests cover the warning on each surface and the suppressed case.
- `make test` passes.

# Result

Implemented the warning as a read-only pre-check in `braintree.main`, the entry
point that fronts every verb, so no observable module changed. `_warn_orphans`
resolves the vault without migrating a legacy directory, reads the shared
`graph_check.findings`, and — before dispatch — prints a count banner plus one
`warning: <path>: orphan unfinished node` line per `route-orphan` finding on
stderr for the four direct-answer verbs `frontier`, `next`, `orient`, and
`status` (`_DIRECT_ANSWER_COMMANDS`, the set this node's `# Context` names). The
warning is on stderr, not stdout, because those verbs emit machine-readable TOON
on stdout; the exit code is untouched, so a read-only answer still succeeds. The
four verb help entries in `help.py` gained the matching hazard line.

Evidence:
- `tests/test_orphan_warning.py`: on a seeded vault each of the four
  direct-answer verbs warns with the orphaned file path and exits 0 while stdout
  stays free of `warning:`; a reachable graph produces empty stderr; re-routing
  the orphan's `Parent` back to the hub silences the warning (falsification
  probe); `check` still exits 1 with `orphan unfinished node` and
  `--allow-orphan TAS-002-orphan` still passes.
- `braintree check` passes on the live vault; `make test` passes (704 passed,
  3 skipped, 79 deselected).
- `braintree benchmark verbs --verify` still passes: the warning is stderr-only,
  so the exact stdout-and-exit baseline is byte-identical.
