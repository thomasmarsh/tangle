---
context_rev: 1
status: proposed
priority: P2
updated: 2026-09-15T15:07:20Z
summary: Make the non-hermetic default-gate tests hermetic.
next: Pin the environment of the live frontier recipe test and the live-vault frontier test to tmp_path.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

Pin TANGLE_NODES_DIR, TANGLE_SIDECAR_DIR, and TANGLE_PROJECT_ID to tmp_path for
tests that read or mutate the live vault or ambient sidecar:

- test_skill.py live frontier recipe test.
- test_tangle_index.py live-vault frontier test.
- test_node_references.py.
- test_semantic.py and test_cluster_verbs.py live probes.
- test_decompose.py and test_feedback_record.py upkeep leakage.

Keep the live-vault coverage but remove real-state writes.

# Outcome

No default-gate test writes the developer's real sidecar or views; live-vault
coverage runs on tmp fixtures.

# Done when

- No default-gate test writes the developer's real sidecar or views.
- Coverage is preserved on tmp fixtures.
- make test is green.
