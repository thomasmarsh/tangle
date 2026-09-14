---
context_rev: 1
priority: P2
updated: 2026-09-14T11:20:50Z
summary: Stamp updated from the host clock in every writer and verify a future stamp at integration.
next: State the writer host-clock stamp rule and the integration verification in the contract and pin it with a test.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Tangle `FBK-031` finding 2 at `0.6.0+g169bad5`, a recurrence of Tangle `FBK-026`
finding 4 and the third session to record it. Round eight
[[TAS-154-coordinator-clock-stamping]] repinned `SKILL.md` to "A coordinator
stamps the host clock at handoff — the real host clock time, not a rounded or
estimated value". A worker still stamped `updated: 2026-09-14T00:55:00Z` while
the host clock read `2026-09-14T00:50:52Z`, and the clamp rule then forced every
later edit to carry the future stamp or move it backwards.

# Outcome

`SKILL.md` or `references/coordination.md` requires every writer to stamp
`updated` from the host clock, and the coordinator to verify and correct a future
stamp at integration.

# Done when

- The contract states the writer host-clock rule, using the actual host clock
  value rather than an estimate.
- The contract states the coordinator's integration check for a future stamp.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
