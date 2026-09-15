---
context_rev: 1
status: resolved
priority: P2
updated: 2026-09-15T15:07:32Z
summary: Classify each default-suite test as load-bearing, redundant, tautological, or over-expensive.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

The parent coordinates this audit. The default gate collects roughly 854 tests
across about 34 modules and must say which of them earn their runtime.

# Outcome

A guarantee map and a prioritized, evidence-cited cut and cheapen list that
later execution slices can apply without re-deriving coverage.

# Done when

- Every default-suite module is classified as load-bearing, redundant,
  tautological, non-hermetic, or over-expensive.
- Each redundancy cluster names the surviving owner test.
- Each cut candidate names its evidence and a cheap replacement or a surviving
  guarantee.
- Genuine coverage gaps are named so cuts are not blind.

# Result

Four-cluster meaning audit of the default pytest gate, synthesized into six
execution children (all proposed under this parent):

- Core index/graph: heavy duplication, for example the direct-edit reconcile
  guarantee in test_index_upkeep.py and test_census.py, reindex recovery in
  index and upkeep, and reindex seeding in foundation; 70 near-parameterized
  graph-check cases; the suite's only wall-clock sleep.
- Skill/prose: test_skill.py re-reads SKILL.md across 83 functions; 23
  falsification probes and many prose locks duplicate behavioral suites.
- Memory corpora: the modules in the default gate validate committed JSON
  corpora and restate prose; the seven benchmark-marked modules are already
  deselected by the default -m not benchmark filter.
- Semantic/verification: verification lease tests duplicate foundation lease
  tests; the semantic modules skip without numpy.

Execution children: tas-1cbytx85g31seeda06bq7f1nfa (E1 retire duplicates and
the wall-clock sleep, P2), tas-4ysvfgkb6ytqbch8f5ae6qzt3w (E2 collapse the
prose-lock apparatus, P3), tas-1tawqxsrvyby2qwv7gzsbqvb11 (E3 drop
committed-data QA from memory corpora, P3), tas-1tn95z62bqewgvjm94fx9k8nbe
(E4 cheapen subprocess-bound tests, P3), tas-667ytnpsk9ct57488q68pzx68w (E5
make the non-hermetic tests hermetic, P2), tas-098efjf0v8gerphqnvtc6rd7xp (E6
enable pytest-xdist, P2).
