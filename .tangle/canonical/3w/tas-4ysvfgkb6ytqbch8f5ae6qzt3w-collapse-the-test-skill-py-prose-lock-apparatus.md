---
context_rev: 1
status: proposed
priority: P3
updated: 2026-09-15T15:20:48Z
summary: Collapse the test_skill.py prose-lock apparatus.
next: Remove the redundant prose locks whose behavioral survivor is already covered.
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

# Result

Completed the falsification-probe collapse slice. The 22 probe tests that only
asserted `_assert_contains`/`_assert_absent` raise on hand-written pre-change
text read no product surface; they are now one parametrized test,
`test_rule_guards_reject_their_pre_change_probes`, parametrized over
`_FALSIFICATION_PROBES` (22 cases) so each guard still fails by name. The diff
is +129/-166 lines, and `ruff`, `mypy`, and `tests/test_skill.py` are green (22
passed, 101 deselected).

Remaining scope: remove the redundant prose locks whose behavioral survivor is
already covered, the duplicate absence assertion, and the duplicated core-verb
help loop.
