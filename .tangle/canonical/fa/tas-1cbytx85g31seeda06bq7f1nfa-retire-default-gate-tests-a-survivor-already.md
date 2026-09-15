---
context_rev: 1
status: resolved
priority: P2
updated: 2026-09-15T15:13:52Z
summary: Retire default-gate tests a survivor already covers; drop the wall-clock sleep.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

Delete whole tests only, each with a named survivor in the same default gate:

- tests/test_index_upkeep.py::test_upkeep_writes_nothing_when_markdown_is_unchanged
  (the only wall-clock sleep; survivors test_census.py zero/edit tests and
  test_views.py unchanged-vault test).
- tests/test_tangle_foundation.py::test_reindex_seeds_reservations (survivor
  test_init_seeds_reservations_from_markdown).
- tests/test_tangle_index.py::test_reindex_recovers_after_database_loss
  (survivor tests/test_index_upkeep.py::test_a_lost_state_file_is_rebuilt_from_markdown).
- tests/test_tangle_verification.py::test_expiry_and_base_hash_mismatch
  (survivors test_tangle_foundation.py lease tests).
- tests/test_skill.py::test_stationary_storage_decision (locks a file that no
  longer exists).
- The duplicate observable-path rejection test in
  test_memory_admission/resumption/revision/transfer_corpus.py (survivor
  test_memory_scenario.py::test_parser_rejects_invalid_observable_path).

# Outcome

The default gate retains no test whose guarantee a surviving test already proves,
and no test depends on a wall-clock sleep.

# Done when

- Those tests are removed, each removal cites its surviving test.
- make test is green.

# Result

Removed nine duplicate or dead default-gate tests, each with a surviving test:

- tests/test_index_upkeep.py::test_upkeep_writes_nothing_when_markdown_is_unchanged
  (the only wall-clock sleep; survivors the tests/test_census.py zero/edit tests
  and the tests/test_views.py unchanged-vault test).
- tests/test_tangle_foundation.py::test_reindex_seeds_reservations (survivor
  test_init_seeds_reservations_from_markdown).
- tests/test_tangle_index.py::test_reindex_recovers_after_database_loss
  (survivor tests/test_index_upkeep.py::test_a_lost_state_file_is_rebuilt_from_markdown).
- tests/test_tangle_verification.py::test_expiry_and_base_hash_mismatch
  (survivors the tests/test_tangle_foundation.py lease tests).
- tests/test_skill.py::test_stationary_storage_decision (locks a file that no
  longer exists; its TAS-017 Result assertion is now covered structurally by
  tangle check).
- tests/test_memory_{admission,resumption,revision,transfer}_corpus.py::test_verify_rejects_a_mutated_case,
  four copies (survivor
  tests/test_memory_scenario.py::test_parser_rejects_invalid_observable_path).

Evidence: make test PASS, 842 passed / 3 skipped / 80 deselected in 127.1s wall;
188 deletions across nine test files, no source or fixture change.
