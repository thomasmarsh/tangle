---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: A context_rev bump commits the bumped node alone under the documented staged-staleness gate; reconciliation is separate consumer-owned work.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R1 from Hekate `THO-004-terminal-survey-braintree-friction` F1: a
semantic `context_rev` bump makes pinned consumers stale, but `graph-check nodes`
treats any mismatch as a hard error, and the repo mandates a green checker
before commit and handoff.

# Outcome

A worker never has to choose between the staleness contract and a green
checker: either the bump reconciles pinned consumers in one commit or handoff,
or the sanctioned gate allows staged staleness and reconciliation is tracked as
separate work.

# Done when

- `SKILL.md` states the intended commit shape for a `context_rev` bump.
- `AGENTS.md` and `SKILL.md` agree on the mandated checker invocation.
- No sanctioned workflow requires an undocumented `--allow-stale`.
- `make test` passes, and any new checker behavior has a regression test.

# Result

Took the staged-staleness branch. A semantic `context_rev` bump commits the
bumped node alone and leaves pinned consumers stale on purpose, so the exact
backlink search still finds the reconciliation work. That commit runs the
sanctioned gate `graph-check --allow-stale nodes`; the normal gate stays plain
`graph-check nodes`. Reconciliation is separate consumer-owned work: reread the
dependency, update assumptions, reset the pin to the current `context_rev`, and
pass the plain gate before that consumer executes.

Same-commit reconciliation would contradict the staleness contract, which
deliberately leaves dependents' pins unchanged, and the exclusive write-set
rule, under which the bumping worker may not own the consumers. `--allow-stale`
already suppresses only the revision-equality check while still rejecting a
missing or malformed pin, so it is a precise staged-staleness gate rather than
a bypass, and it is now documented instead of implied.

Evidence:

- `SKILL.md` dependency-revision section states the bump commit shape, the
  sanctioned staged-staleness gate, and the consumer-owned reconciliation step.
- `AGENTS.md` step 5 names the same staged-staleness invocation and requires
  the plain gate before finishing, so both files agree.
- `test_allow_stale_still_rejects_missing_pin` locks `--allow-stale` to
  revision equality only, matching the documented contract.
- `test_skill_canonical_edge_and_lifecycle_contract` asserts the stated shape.
- `make test` passes.
