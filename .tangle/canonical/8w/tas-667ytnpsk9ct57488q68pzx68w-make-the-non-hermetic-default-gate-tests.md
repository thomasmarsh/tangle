---
context_rev: 1
status: resolved
priority: P2
updated: 2026-09-15T15:51:52Z
summary: Make the non-hermetic default-gate tests hermetic.
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

# Result

Every default-gate test now runs against a temporary derived-state root: no
in-process or spawned ``tangle`` call reconciles this machine's real database
or republishes the shipped vault's views.

Changes:

- ``tests/conftest.py``: the new autouse ``hermetic_sidecar`` fixture pins
  ``TANGLE_SIDECAR_DIR`` to ``<tmp_path>/sidecar`` and ``TANGLE_PROJECT_ID`` to
  ``pytest-hermetic`` for every test. ``run_tangle`` builds its child
  environment from ``os.environ``, so the pin covers both in-process
  ``main.main`` calls and spawned ``python -m tangle`` processes. This also
  hardened ``test_node_references.py``, ``test_decompose.py``,
  ``test_feedback_record.py``, and the live probes in ``test_semantic.py`` and
  ``test_cluster_verbs.py``, which previously pinned only ``TANGLE_NODES_DIR``.
- ``tests/test_skill.py``: ``_run_frontier_recipe`` takes a state root and sets
  ``TANGLE_SIDECAR_DIR`` / ``TANGLE_PROJECT_ID`` in the child environment;
  ``test_frontier_recipe_matches_the_live_vault`` passes ``tmp_path``, so the
  vault stays the read-only subject and the recipe's upkeep writes nowhere real.
- ``tests/test_tangle_index.py``: ``test_frontier_matches_markdown_on_live_vault``
  uses the shared ``_env(tmp_path, nodes)`` helper instead of clearing the
  sidecar and project variables, so it can no longer reconcile the real
  database or republish the shipped ``views``.

Evidence: ``make test`` passed: 794 passed, 3 skipped, 80 deselected in
109.12s; ruff and mypy green; ``tests/install.sh`` and
``tests/worktree-parallel.sh`` passed. The ``.tangle/views/*.md`` list (path and
mtime) was identical before and after the run.

Residual: tests still read the live ``.tangle`` nodes read-only, which is the
intended subject of the live-vault coverage. No default-gate test writes real
state, and no test forces the ambient default state root.
