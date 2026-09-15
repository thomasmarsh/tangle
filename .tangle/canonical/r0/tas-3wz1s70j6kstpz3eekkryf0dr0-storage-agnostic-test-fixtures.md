---
context_rev: 1
status: resolved
updated: 2026-09-15T01:24:44Z
summary: Abstract storage-specific Tangle test fixtures.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

Behavioral tests assert node identity and CLI output through shared helpers rather than status-directory or numeric filename assumptions.

# Done when

- Canonical path lookup and deterministic identity injection helpers exist.
- Capture, feedback, decomposition, and installer tests use them.
- A storage-layout change modifies helper fixtures rather than scattered behavior assertions.

# Result

Inventoried the layout and identity coupling across the four named areas. The
stationary shard rule was restated as `.tangle/canonical/<suffix>/` path
construction and `[-2:]` in `test_feedback_scan.py` and `tests/install.sh`;
capture and decomposition tests seeded legacy status directories
(`nodes/.../proposed|active|resolved`) and recovered generated nodes with
`rglob` slug globs and an inline id regex; the installer test globbed
`canonical/*/fbk-*.md` by shard.

Added one test-side spelling of both rules in `tests/vault_helpers.py`:
`canonical_path`/`write_node` (shard path lookup and deterministic fixture
identity), `iter_nodes`/`find_node`/`find_nodes`/`find_typed` (node lookup that
ignores the shard and slug), `deterministic_id`, and `fixed_identity`, which
patches `identity.generate_node_id` to a predictable per-call sequence. The
`deterministic_ids` fixture in `tests/conftest.py` exposes the injection to
in-process writers. `tests/install.sh` gains the `canonical_file` shell helper,
seeds the hub canonically, and passes an explicit `--id`/`--slug` to the
installed command so the cross-process path is deterministic.

Migrated all four areas onto the helpers: `test_feedback_scan.py` seeds its
stationary feedback node through `write_node`; `test_feedback_record.py` seeds a
canonical hub, looks nodes up through `find_nodes`/`find_typed`, asserts the
exact injected `fbk` id, and replaces its `proposed/` existence checks with
canonical node counts; `test_decompose.py` seeds canonical hub and parent and
uses `fixed_identity` to assert the exact child ids and parent route; the
installer test computes the written path from `canonical_file`. The legacy
`_vault` fixtures in `test_feedback_scan.py` and the `nodes/`-to-`.tangle`
migration case remain, because they deliberately cover the frozen legacy
compatibility surface rather than the current layout.

# Evidence

`make test` passes: ruff, strict mypy (91 files), 826 passed / 3 skipped / 80
deselected, plus the `worktree-parallel` and `install` shell suites.

A factual note for the sibling resolved by `tangle packet`: the premise that
`test_frontier_matches_markdown_on_live_vault` fails is stale. The live-vault
recipe already discovers canonical nodes through `store.iter_node_paths`, and
the test passes; no live-vault recipe change was needed here.
