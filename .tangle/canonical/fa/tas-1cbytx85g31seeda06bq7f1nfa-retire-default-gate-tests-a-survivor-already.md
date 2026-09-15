---
context_rev: 1
status: proposed
priority: P2
updated: 2026-09-15T15:07:20Z
summary: Retire default-gate tests a survivor already covers; drop the wall-clock sleep.
next: Delete the eight duplicate or dead default-gate tests listed in this node Context.
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
