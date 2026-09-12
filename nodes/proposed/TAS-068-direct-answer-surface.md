---
context_rev: 1
priority: P1
updated: 2026-09-12T15:38:45Z
summary: Move graph reasoning out of SKILL.md prose into direct `braintree` answers so client agents decide and act in fewer round trips while the always-loaded skill shrinks.
next: "[[TAS-073-bounded-orientation-packet]]"
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

Depends on [[DEC-004-compact-skill-text]] at context_rev 1.

The unified `braintree` command already hides the implementation, but most graph
answers still come from shell recipes in `SKILL.md` and multi-step composition:
the Frontier recipe, `find`/`rg` backlink searches, and manual dependency-impact
repeats. Two facts frame this thrust. First, the cold-resume benchmark shows the
always-loaded contract and re-derivation dominate session tokens. Second,
`braintree stale` and `braintree check` disagree about which relations are
context edges and about whether an unresolved pinned target is a problem, so the
same question has two answers.

This is a user-requested plan, so its children are created up front as proposed
work and resolved or disposed as reality arrives. Order is lowest risk and
highest leverage first; retrieval, reconciliation, and model work follows only
after the direct-answer surface is proven.

- Theory under test: [[THO-010-round-trip-reduction-theory]].
- Staged comparison: [[TAS-080-staged-token-ab]].
- Semantic boundary: [[DEC-006-semantic-layer-capability-boundary]].

Planned order:

1. [[TAS-069-unify-dependency-semantics]] - one canonical context-edge and
   health answer.
2. [[TAS-070-structured-check-output]] - stable machine-readable validator
   output.
3. [[TAS-071-frontier-and-node-verbs]] - answer the frontier and a node
   directly.
4. [[TAS-072-transitive-dependency-impact]] - one call for direct and indirect
   impact.
5. [[TAS-073-bounded-orientation-packet]] - one bounded orientation answer.
6. [[TAS-074-shrink-skill-to-commands]] - remove the recipes the verbs replaced.
7. [[TAS-078-round-trip-telemetry-and-gates]] - record round trips and gate the
   new verbs.
8. [[TAS-075-structured-search-and-admission]],
   [[TAS-076-frontier-ranking-and-clustering]], and
   [[TAS-077-reconciliation-planner]] - retrieval, ranking, and reconciliation.
9. [[TAS-079-optional-semantic-retrieval]] - the capability-bounded semantic
   layer.
10. [[TAS-080-staged-token-ab]] - compare this state with the landed state.

# Outcome

`braintree` answers the core graph questions directly, the always-loaded
`SKILL.md` is smaller, and a staged benchmark shows fewer round trips and tokens
for the same correctness.

# Done when

- Every child is resolved or disposed with rationale.
- `braintree` directly answers the frontier, a node's graph view, and
  dependency impact, with tests tying each answer to the Markdown derivation.
- `SKILL.md` no longer carries the shell recipes its verbs replaced and is
  measurably smaller.
- Round-trip telemetry and a correctness-gated A/B are recorded.
- `make test` passes.
