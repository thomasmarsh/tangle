---
context_rev: 1
priority: P1
updated: 2026-09-13T19:30:46Z
summary: Repair the round-five non-separating conflict case so the corpus separates.
next: Execute the three pilot batches and the nine causal batches, then collect and record both results.
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

The conflict case was repaired at revision `cdcbde6bb90c`, which re-froze the
corpus at digest
`sha256:e7754707c24e04e50460fda994b660ccc51d1cbcafb288405311f5dfea8a63de`.
The separability re-run pins: protocol `memory-pilot-v2`; corpus digest
`sha256:e7754707c24e04e50460fda994b660ccc51d1cbcafb288405311f5dfea8a63de`;
fixture `memory-pilot-v2-fixture-1`; source revision `cdcbde6bb90c`; model
`deepseek/deepseek-v4-flash` (`deepseek-v4-flash`) at `high`; prompt
`memory-pilot-v2-prompt-1`; tools `no-tools`; budget one isolated turn, no
retries; grader `memory-scenario-v1`; plan digest
`sha256:c955e3fd0161c5f2d6dee95e9d67c0f072115cd0936e4d146ff795777726c6b6`;
72 samples (12 cases x 2 arms x 3 repetitions) in three 24-child batches.

Because the repair changes the five-arm runner's fixture, the same standing
authorization also covers the replacement causal run that [[TAS-122-causal-baseline-experiment]]
owns and [[TAS-123-pipeline-diagnostics]] derives from: protocol
`memory-causal-v1`; corpus digest
`sha256:e7754707c24e04e50460fda994b660ccc51d1cbcafb288405311f5dfea8a63de`;
source revision `cdcbde6bb90c`; plan digest
`sha256:15d116445bc018cb0d5220748bd4d2922e9cdaeb2acc93c94706f53fd3e04710`;
540 samples (12 cases x 5 arms x 3 models x 3 repetitions) in nine 60-child
batches, three models at `high`.
