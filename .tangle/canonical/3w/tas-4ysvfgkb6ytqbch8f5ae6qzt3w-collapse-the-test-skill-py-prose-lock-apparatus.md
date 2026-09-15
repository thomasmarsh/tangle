---
context_rev: 1
status: resolved
priority: P3
updated: 2026-09-15T15:25:52Z
summary: Collapse the test_skill.py prose-lock apparatus.
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

Removed the redundant prose-lock apparatus in tests/test_skill.py in two
sub-slices.

Probe collapse (commit efaf6df): the 22 falsification-probe tests only asserted
that the local `_assert_contains`/`_assert_absent` guards raise on hand-written
pre-change text and read no product surface. They are now one parametrized
test, `test_rule_guards_reject_their_pre_change_probes`, over
`_FALSIFICATION_PROBES` so each guard still fails by name.

Prose locks and duplicate assertions removed in this sub-slice. Each lock only
asserted that installed reference prose restates a rule; the underlying
behavior is covered by the named test:

- `test_manifest_schema_is_stated` -> tests/test_manifest.py manifest read and
  validation tests.
- `test_transactional_decomposition_is_stated` -> tests/test_decompose.py
  dry-run and rollback tests.
- `test_capture_summary_limit_is_documented` -> tests/test_feedback_record.py
  `test_summary_limit_is_the_documented_96_characters` and
  `test_capture_help_surfaces_the_summary_limit`.
- `test_allocation_burn_and_visibility_are_stated` ->
  tests/test_tangle_foundation.py
  `test_reservations_lists_burned_ids_apart_from_missing_nodes`.
- `test_pending_advance_transient_is_stated` -> tests/test_graph_check.py
  pending-advance sanction tests.
- `test_opt_in_reconnaissance_reference_is_stated` ->
  tests/test_node_references.py reconnaissance read-surface tests.
- `test_action_sentence_next_forbids_a_wikilink` -> tests/test_packet.py
  action-next quoting and tests/test_graph_check.py
  `test_action_sentence_next_containing_a_wikilink_names_the_token`.

Also removed the duplicate `_SIZING_COMMAND_ABSENT` absence assertion (the first
assertion in `test_core_keeps_the_durable_outcome_boundary` remains), the
duplicated core-verb help loop inside
`test_fresh_worker_can_execute_the_normal_path_from_the_core` (the unique
verb-registry binding remains, and bounded help is still covered by
`test_every_public_verb_has_bounded_help`), and the now-unused
`_PENDING_ADVANCE_RULE`, `_ALLOCATION_BURN_CORE_RULE`, and `_BOUNDED_HELP`
constants.

Tradeoff recorded: reference prose presence for those seven rules is no longer
positively locked; their behavioral coverage remains, and the rule constants
still drive their falsification probes, so a guard that stops detecting its
tokens still fails.

Evidence: make test PASS (835 passed, 3 skipped, 80 deselected, 127.40s; ruff
and mypy clean; install and worktree-parallel suites passed) and
tests/test_skill.py green.
