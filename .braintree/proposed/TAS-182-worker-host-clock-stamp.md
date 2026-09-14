---
context_rev: 2
priority: P2
updated: 2026-09-14T11:27:54Z
summary: Reject fresh future updated stamps without reversing inherited clamps.
next: Define the writer clock read and the fresh-versus-inherited future-stamp integration branches and pin them with a test.
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

The existing clamp makes a bare "correct every future stamp" rule unsafe. The
integration base distinguishes a fresh guessed stamp, which may be replaced,
from a future stamp the worker inherited, which must not move backward.

# Outcome

`SKILL.md` requires every writer to read the host clock when refreshing
`updated`, rather than estimate or round it. The coordination contract requires
the coordinator to compare a submitted future stamp with the integration-base
value: replace a newly introduced future stamp with a fresh host-clock reading,
but preserve and note the existing clamp when the base already carried the
future value.

# Done when

- The contract states that every writer reads the actual host clock when it
  refreshes `updated`, rather than estimating or rounding the value.
- The integration rule compares a future stamp with the integration base and
  corrects one introduced by the submitted mutation from a fresh host-clock
  reading.
- The integration rule preserves and reports an inherited future-stamp clamp
  instead of moving it backward.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
