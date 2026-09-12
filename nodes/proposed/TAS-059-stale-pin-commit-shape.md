---
context_rev: 1
priority: P1
updated: 2026-09-12T13:58:00Z
summary: Give a context_rev bump a committable shape that survives the mandated graph-check gate instead of forcing undocumented --allow-stale.
next: Decide whether a context_rev bump reconciles every pinned consumer in the same commit or sanctions a stale-pin gate, then state that shape in SKILL.md and align the mandated command.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R1 from Tangle `THO-004-terminal-survey-braintree-friction` F1: a
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
