---
context_rev: 1
status: resolved
priority: P3
updated: 2026-09-15T15:34:50Z
summary: Drop committed-data QA and prose-agreement tests from memory corpus modules.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

The memory corpus modules carry committed-data QA and prose-agreement tests:

- Per-family generic structure tests are subsumed by the test_memory_corpus.py
  whole-corpus verify.
- Prose-agreement tests across the memory modules assert documentation, not
  behavior.
- Keep unique per-family invariants and the corpus validator contract tests.

# Outcome

The memory corpus modules test only unique per-family invariants; shared
structure and prose agreement are owned once by test_memory_corpus.py.

# Done when

- Subsumed tests are removed.
- Unique invariants and test_memory_corpus.py remain.
- make test is green.

# Result

The default memory gate now tests unique per-family invariants; shared corpus
structure and research-prose agreement are owned once by test_memory_corpus.py.
41 test functions and 456 lines were removed across 14 files.

Per-family structure tests removed, with the whole-corpus or behavioral
survivor in test_memory_corpus.py: test_every_case_parses_and_agrees_with(_its)_
envelope (:112 test_committed_corpus_validates, :120
test_committed_manifest_verifies_offline), test_case_ids_are_unique (:220
test_duplicate_case_id_is_reported), test_every_cited_path_exists_in_the_
repository (:243 test_missing_cited_path_is_reported), test_task_prompts_are_arm_
neutral (:389/:400/:408 task-probe tests), test_each_case_names_gold_evidence_
with_a_later_decision(_or_no_value) (:428
test_gold_evidence_restating_an_episode_is_reported), test_splits_are_populated_
for_every_family (:318 test_family_missing_a_split_is_reported, :325
test_unbalanced_family_split_is_reported). Removed from
test_memory_admission_corpus.py, test_memory_resumption_corpus.py,
test_memory_revision_corpus.py, and test_memory_transfer_corpus.py.

Committed-data and prose-agreement tests removed: test_memory_authority.py
test_frozen_gold_corpus_is_untouched and test_document_matches_the_case_set
(:129 test_case_count_and_digest_are_recorded, :139 test_digest_is_deterministic)
and the memory_corpus import those tests alone used; test_memory_corpus.py
test_prose_authority_agrees_with_the_corpus (:112/:120); test_memory_contract.py
test_document_records_the_protocol_literals (:20 test_protocol_is_literal, :101
test_verify_passes_on_the_frozen_contract); test_memory_scenario.py
test_document_records_the_schema_literals (:27 test_schema_version_is_literal,
:32 test_schema_imports_the_frozen_contract_literals); test_memory_causal.py
test_document_preregisters_protocol_arms_models_and_gate; test_memory_confirmatory.py
test_document_preregisters_confirmatory_protocol; test_memory_diagnostics.py
test_document_matches_the_module; test_memory_pilot.py
test_document_preregisters_exactly_the_selected_cases,
test_document_records_protocol_arms_and_verdicts,
test_document_records_the_authorization_gate; test_memory_pilot_result.py
test_result_pins_protocol_model_and_verdict,
test_result_covers_every_preregistered_case_and_arm; test_memory_pilot_v2.py
test_document_preregisters_protocol_subset_and_pins.

Kept: the test_memory_corpus.py validator and mutate-one-invariant suite, the
test_memory_contract.py and test_memory_scenario.py literals/verify/parser
tests, and every unique per-family invariant.

Tradeoff: research-prose presence and preregistration/authorization prose are no
longer positively locked by the default gate; the module behavior and
committed-corpus invariants they described remain covered.

Evidence: make test PASS — ruff "All checks passed!", mypy "Success: no issues
found in 95 source files", worktree-parallel and install tests passed, pytest
794 passed / 3 skipped / 80 deselected in 131.94s (/tmp/e3-make-test.log).
