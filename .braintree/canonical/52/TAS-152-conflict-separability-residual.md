---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Repair the round-five non-separating conflict case so the corpus separates.
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

The conflict case was repaired at revision `cdcbde6bb90c` and the temporal
case at `20c88e7ba1ed`, which re-froze the corpus at digest
`sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`.
An initial conflict-only pilot (corpus
`sha256:e7754707c24e04e50460fda994b660ccc51d1cbcafb288405311f5dfea8a63de`,
plan digest
`sha256:c955e3fd0161c5f2d6dee95e9d67c0f072115cd0936e4d146ff795777726c6b6`)
separated the conflict case 3/3 but flipped the temporal case, so the temporal
repair followed. The final separability re-run pins: protocol `memory-pilot-v2`;
corpus digest
`sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`;
fixture `memory-pilot-v2-fixture-1`; source revision `20c88e7ba1ed`; model
`deepseek/deepseek-v4-flash` (`deepseek-v4-flash`) at `high`; prompt
`memory-pilot-v2-prompt-1`; tools `no-tools`; budget one isolated turn, no
retries; grader `memory-scenario-v1`; plan digest
`sha256:0458a693e0477e86744f0bd9f819a2796b5db2b965b05e8405c6851bd34f10df`;
72 samples (12 cases x 2 arms x 3 repetitions) in three 24-child batches.

Because the repair changes the five-arm runner's fixture, the same standing
authorization also covers the replacement causal run that [[TAS-122-causal-baseline-experiment]]
owns and [[TAS-123-pipeline-diagnostics]] derives from: protocol
`memory-causal-v1`; corpus digest
`sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`;
source revision `20c88e7ba1ed`; plan digest
`sha256:636c25705154e95bdd976b24233c0ae88927096091d3ec91e8b8c05603e3aac2`;
540 samples (12 cases x 5 arms x 3 models x 3 repetitions) in nine 60-child
batches, three models at `high`.

# Result

The conflict separability residual is repaired and the corpus is frozen with no
non-separating memory-required case. The conflict case now states that no
precedence is observable and that the standing convention is to keep both
readings and flag the disagreement; the recorded precedence decision in the
unavailable history then makes the narrower later rule controlling. A first
conflict-only pilot (plan `sha256:c955e3fd...`) separated the conflict case 3/3
but flipped `temporal-update-cosmetic-edit-001`, so that case also received a
documentation-only distractor against the hidden contract reword.

The round-seven separability pilot completed 72/72 with the preregistered
verdict **`proceed`**. All nine memory-required development cases separate under
the 2-of-3 paired majority: repository-only is correct 0/3 on every one, and the
oracle is correct 3/3 on every one except
`conflict-and-uncertainty-competing-rules-001` (2/3, one empty model response
graded a model failure). All three controls are valid 3/3. Pins: corpus digest
`sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`;
plan digest
`sha256:0458a693e0477e86744f0bd9f819a2796b5db2b965b05e8405c6851bd34f10df`;
source revision `20c88e7ba1ed`. Evidence is in
`benchmark/memory-pilot-v2-round7-result.json`; the conflict-only round-six
intermediate is `benchmark/memory-pilot-v2-round6-result.json`.

Because the repair changes the five-arm runner's fixture, this node also
generated and collected the replacement causal result that
[[TAS-122-causal-baseline-experiment]] owns and the re-derived diagnostics
report that [[TAS-123-pipeline-diagnostics]] owns, and both consumers are
reconciled to the new revision. The corpus keeps its 53 cases, 40-60 range,
family and curation-group balance, control balance, and deterministic split,
re-frozen at digest
`sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`.
`braintree check`, `make test` (610 passed), and `make test-benchmarks` (79
passed) pass.
