---
context_rev: 1
priority: P3
updated: 2026-09-12T13:58:00Z
summary: State in SKILL.md what resolving a frontier THO/DEF/DEC node implies for the coordinating parent's next.
next: Add the knowledge-node frontier rule to the Read and execute loop in SKILL.md.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R2 from Tangle `THO-004-terminal-survey-braintree-friction` F2: the
read/execute and decomposition rules are task-centric, so a worker resolving a
frontier knowledge node must guess whether the coordinating parent's `next`
advances, and the mutation rules read as forbidding the touch.

# Outcome

The skill says that when the frontier is a knowledge node (`THO`/`DEF`/`DEC`),
the worker answers and resolves it and advances the coordinating parent's `next`
to the next deliberate frontier child in the same change.

# Done when

- `SKILL.md` states the knowledge-node frontier rule where it describes the read and execute loop.
- The rule is consistent with the mutation rules on touching the parent's `next`.
- `make test` passes, including the `SKILL.md` contract assertions.
