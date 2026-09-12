---
context_rev: 1
priority: P3
updated: 2026-09-12T14:16:02Z
summary: State in SKILL.md what resolving a frontier THO/DEF/DEC node implies for the coordinating parent's next.
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

# Result

The Read and execute loop now states the knowledge-node frontier rule: when the
frontier is a `THO`/`DEF`/`DEC`, the worker answers the question and resolves it
like any other frontier node and, in the same change, advances the coordinating
parent's `next` to the next deliberate frontier child. The advance is part of
resolving the frontier, not bookkeeping on an unrelated node, so the resolving
worker owns the parent edit, refreshes the parent's `updated`, and leaves the
parent's `context_rev` unchanged because `next` is navigation, not
consumer-relevant semantics.

The Mutation rules now name that advance as part of the resolution rather than
bookkeeping, so they no longer read as forbidding the touch while still barring
unrelated-node and index updates.

Evidence:

- `SKILL.md` Read and execute loop states the knowledge-node frontier rule and
  the same-change parent `next` advance.
- `SKILL.md` Mutation rules sanction the parent `next` edit and distinguish it
  from bookkeeping.
- `test_skill_canonical_edge_and_lifecycle_contract` asserts both passages.
- `make test` passes.
