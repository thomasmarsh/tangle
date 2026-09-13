---
context_rev: 1
priority: P2
updated: 2026-09-13T21:49:10Z
summary: Report an orphaned unfinished node as a loud warning on every braintree interaction, not only in check.
next: Surface orphaned unfinished nodes as a loud warning on every direct-answer interaction.
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
