---
context_rev: 1
status: proposed
priority: P3
updated: 2026-09-15T15:07:20Z
summary: Collapse the test_skill.py prose-lock apparatus.
next: Collapse the 23 falsification-probe tests into one parametrized test.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

Collapse the test_skill.py prose-lock apparatus:

- 23 falsification-probe tests collapse to one parametrized test.
- Remove prose locks already proven behaviorally by test_manifest.py,
  test_decompose.py, test_feedback_record.py, test_graph_check.py,
  test_node_references.py.
- Remove the duplicate absence assertion and the duplicated core-verb help loop.
- Keep the test_skill.py live-vault graph check.

# Outcome

test_skill.py keeps only behavior-locking tests; its prose-lock apparatus is one
parametrized probe.

# Done when

- One parametrized probe test replaces the 23.
- Removed locks name their behavioral survivor.
- make test is green.
