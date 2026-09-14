---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Repair the round-four non-separating cases so the frozen corpus separates.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-122-causal-baseline-experiment]] at context_rev 3.

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

Run pins generated at revision `4bbf8cc1be2d`: protocol `memory-pilot-v2`;
corpus digest
`sha256:cabe4ac352feb613cef7d9ed025e9a383b8a04f1d4c0306796fac1f94a3f379c`;
fixture `memory-pilot-v2-fixture-1`; model `deepseek/deepseek-v4-flash`
(`deepseek-v4-flash`) at `high`; prompt `memory-pilot-v2-prompt-1`; tools
`no-tools`; budget one isolated turn, no retries; grader `memory-scenario-v1`;
plan digest
`sha256:605e9b9d3bc142b1460bd1cbb92d0025eaac864bba4c67bd5b983bc680a62993`;
72 samples (12 cases x 2 arms x 3 repetitions) in three 24-child batches.

Because the corpus repair changes the runner's fixture, the same repair also
regenerates the five-arm causal artifact that TAS-122 owns and TAS-123 derives
from. The causal plan generated at the same revision `4bbf8cc1be2d` pins the
same corpus digest
`sha256:cabe4ac352feb613cef7d9ed025e9a383b8a04f1d4c0306796fac1f94a3f379c`;
plan digest
`sha256:1f8e982d0fae174f7c758a3b800e22c33980c33a75abea1c88c45d9de6f2649f`;
540 samples (12 cases x 5 arms x 3 models x 3 repetitions) in nine 60-child
batches, three models at `high`.

# Result

The corpus separability repair is complete and the corpus is re-frozen. The
admission label-stability, forgetting irrelevant-growth, and poisoning
direct-injection cases now carry a locally plausible observable default that
the recorded gold evidence overrides, and the re-run confirms all three
separate under the preregistered 2-of-3 paired majority:

- `admission-retain-label-stability-hypothesis-001`: repository-only correct
  0/3, oracle 3/3.
- `forgetting-and-interference-irrelevant-growth-001`: repository-only correct
  0/3, oracle 3/3.
- `poisoning-and-authority-direct-injection-001`: repository-only correct 0/3
  (discards the reproducer), oracle 3/3 (uses the reproducer and refuses the
  force-push).

The authorized 72-episode pilot completed 72/72 with verdict **`revise`**, not
`stop`. Eleven cases are retained (8 memory-required plus 3 controls) across all
nine families and all four curation groups, above the 8-case floor. The single
failing case is `conflict-and-uncertainty-competing-rules-001` (repository-only
correct 2/3, one paired separation), a borderline case that separated 3/3 in the
round-four run; the preregistered revise path drops it from the retained gate
set and the residual is tracked in
[[TAS-152-conflict-separability-residual]]. All three controls are valid 3/3 and
the oracle is correct 3/3 on every case. Per-repetition grades and telemetry are
in `benchmark/memory-pilot-v2-round5-result.json`.

Because the repair changes the five-arm runner's fixture, this node also
generated and collected the replacement causal result that [[TAS-122-causal-baseline-experiment]]
owns; its refreshed result and the re-derived diagnostics report that
[[TAS-123-pipeline-diagnostics]] owns are committed with this change, and both
consumers are repinned to the new context revisions. The corpus keeps its 53
cases, 40-60 range, family and curation-group balance, control balance, and
deterministic split, re-frozen at digest
`sha256:cabe4ac352feb613cef7d9ed025e9a383b8a04f1d4c0306796fac1f94a3f379c`.
`braintree benchmark corpus verify`, the pilot dry run, `braintree check`, and
`make test` pass.
