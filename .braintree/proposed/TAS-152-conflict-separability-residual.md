---
context_rev: 1
priority: P1
updated: 2026-09-13T19:19:49Z
summary: Repair the round-five non-separating conflict case so the corpus separates.
next: Repair the conflict case and re-run the authorized separability pilot.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-151-corpus-separability-repair]] at context_rev 1.

The round-five separability pilot on the repaired corpus returned `revise`:
`conflict-and-uncertainty-competing-rules-001` separated in only one of its
three paired repetitions (repository-only correct 2/3). The case separated 3/3
in the round-four run, so the failure is borderline rather than a stable design
defect, but the preregistered rule drops it from the retained gate set and
TAS-121's recorded residual requires the frozen corpus to carry no
non-separating memory-required case before the confirmatory evaluation freezes
it. Evidence and paired grades are in
`benchmark/memory-pilot-v2-round5-result.json`.

# Outcome

A frozen gold corpus whose retained memory-required development cases separate
repository-only from oracle under the preregistered 2-of-3 paired majority,
including a repaired or replaced conflict case, so the confirmatory evaluation
can freeze it with no non-separating memory-required case.

# Done when

- `conflict-and-uncertainty-competing-rules-001` is repaired, replaced, or
  re-tested with a recorded reason and a stable separation.
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
