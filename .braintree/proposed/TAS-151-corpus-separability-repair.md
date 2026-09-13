---
context_rev: 1
priority: P1
updated: 2026-09-13T18:40:30Z
summary: Repair the round-four non-separating cases so the frozen corpus separates.
next: Repair the three non-separating cases and re-run the authorized separability pilot.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-122-causal-baseline-experiment]] at context_rev 1.

The round-four separability re-run on the repaired corpus returned `stop`:
three memory-required development cases do not separate under the
preregistered 2-of-3 paired majority. TAS-121's recorded residual requires the
frozen corpus to carry no non-separating memory-required case before the
confirmatory evaluation freezes it.

# Outcome

A frozen gold corpus whose retained memory-required development cases separate
repository-only from oracle under the preregistered 2-of-3 paired majority, so
the confirmatory evaluation can freeze it with no non-separating memory-required
case.

# Done when

- Each non-separating case is repaired or replaced with a recorded reason.
- The authorized separability pilot is re-run on the repaired corpus and
  returns `proceed`, or a `revise` that still retains the 8-case floor and every
  curation group.
- The corpus keeps its 40-60 case range, family and curation-group balance,
  control balance, deterministic split, and digest.
- The corpus is re-frozen and `braintree check` and `make test` pass.

# Authorization

The owner's standing authorization of 2026-09-13 covers the separability
re-run; the exact corpus digest, plan digest, and source revision are generated
at the run revision and recorded here before execution, with no further
authorization request.
