---
status: resolved
context_rev: 2
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Reject fresh future updated stamps without reversing inherited clamps.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Hekate `FBK-031` finding 2 at `0.6.0+g169bad5`, a recurrence of Hekate `FBK-026`
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

# Result

`SKILL.md` now leads the `updated` bullet with the writer rule: "Every writer
reads the actual host clock when it refreshes `updated` — the real time, not an
estimated or rounded value." The coordinator handoff sentence and the
`max(now, previous updated)` clamp remain unchanged after it.

`references/coordination.md`, "Integration and reconciliation", now carries the
comparison rule before the resolve-parent sentence: on integration, compare each
submitted `updated` with the integration base, replace a fresh future stamp the
submitted mutation introduced with a fresh host-clock reading, but preserve and
report a future stamp the base already carried as an inherited clamp rather than
moving it backward.

`tests/test_skill.py` pins both halves:
`_WRITER_HOST_CLOCK_READ_RULE` in `test_every_writer_reads_the_host_clock`
against `SKILL.md`, and `_FUTURE_STAMP_INTEGRATION_RULE` in
`test_future_stamp_integration_repairs_and_preserves` against
`references/coordination.md`, following the `TAS-154` coordinator-stamp
precedent. Both substring sets are absent from the pre-change text
(`git show HEAD:SKILL.md`, `git show HEAD:references/coordination.md`), so the
pins fail when the rules are removed rather than passing vacuously; no separate
falsification fixture is needed for a positive contract string.

Focused run: `uv run pytest tests/test_skill.py -k "host_clock or future_stamp
or writer_reads"` passed (4 passed, 100 deselected). `make test` passed: ruff,
mypy across 75 source files, the Python suite (725 passed, 3 skipped), and the
`install` and `worktree-parallel` shell suites. No `context_rev` bump: this is a
status move, no consumer pins this node, and no consumer assumption changes.
