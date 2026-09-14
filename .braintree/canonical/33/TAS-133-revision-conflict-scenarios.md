---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Curate temporal update, supersession, conflict, and cascading-invalidation cases.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-130-scenario-schema-grader]] at context_rev 1.

# Outcome

Ten to fifteen reviewed cases test semantic revision, stale-context detection, supersession, independently supported conclusions, unresolved conflict, and clarification under missing premises.

# Done when

- Cases include cosmetic versus semantic edits, changed definitions, stale consumers, reversals, superseded decisions, and conflicts with no single justified answer.
- Gold outcomes identify exactly which consumers change and which remain valid through independent evidence.
- Correct behavior can include reconcile, preserve alternatives, abstain, or ask one targeted clarification.
- Event time and mutation time differ in at least one case.
- False-positive and false-negative invalidation are separately gradeable.

# Result

`benchmark/memory-corpus/temporal-update.json` (4 cases),
`benchmark/memory-corpus/cascading-invalidation.json` (4 cases), and
`benchmark/memory-corpus/conflict-and-uncertainty.json` (3 cases) freeze the
three revision-and-conflict families as `memory-scenario-v1` cases curated at
revision `c08af27`. The gate on [[TAS-130-scenario-schema-grader]] was promoted
to the pinned `Depends on` edge at `context_rev 1` on execution.

- Every Done-when kind is covered: cosmetic versus semantic edits, a changed
  definition, stale consumers, an in-place reversal, a superseded decision, an
  independently supported surviving conclusion, two unresolved conflicts, a
  missing premise, and an event-time-versus-mutation-time case.
- The cascading family makes true, false-positive, and false-negative
  invalidation separately gradeable: a direct consumer and its downstream node
  both change in dependency order, an unchanged separate decision preserves one
  conclusion, and a supersession that leaves the obsolete revision unchanged
  forces a replacement-link follow.
- Correct behavior spans reconcile, preserve alternatives, abstain, and ask one
  targeted clarification.
- The conflict resolution norms are grounded in
  `research/agent-memory-theory-evaluation.md` and the planned uncertainty work
  in [[TAS-127-uncertainty-provenance-security]]; the two conflicting sides stay
  on their real rule nodes.

`research/agent-memory-revision-conflict-cases.md` is the prose authority,
including the kind taxonomy, the invalidation-mode definitions, and the
independent review record.

Evidence: `tests/test_memory_revision_corpus.py` (17 tests) enforces the
envelopes, schema conformance, kind coverage, the separate invalidation modes,
the behavior coverage, the event-time direction, the forbidden-surface leak
guards, split population, evidence-path existence, arm-neutral tasks, the
declared-action grading, and document agreement. Two independent fresh-context
reviews blocked the first drafts on unsourced conflict episodes,
observable-path leakage, a misattributed false-positive case, an inverted
event-time case, and a contestable genuine-conflict gold; a resumed re-check
returned accept-with-minor and the minor items were fixed before freeze.
`make test` passes (459 passed, 3 skipped, 79 deselected); the corpora make
zero live model calls.
