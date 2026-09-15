---
context_rev: 1
status: resolved
updated: 2026-09-15T01:33:51Z
summary: Generate execution manifests for frontier tasks.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

A task can expose affected files, focused tests, final verification, and compatibility constraints without a broad repository search.

# Done when

- The schema distinguishes authored intent from derived data.
- A task can declare source, test, verification, and compatibility surfaces.
- The read surface detects missing or malformed entries and tests its output.

# Result

Defined the authored execution manifest as a strict `# Manifest` body section:
one Markdown list item per entry, `- kind: value`, with the four kinds
`source`, `test`, `verify`, and `compat`. `source` and `test` are
repository-relative paths, `verify` is a final acceptance gate command, and
`compat` is a free-text compatibility constraint. The section holds only
schema entries, so a bullet outside the grammar is a defect rather than prose.

The authored entries are intent; `tangle manifest NODE` derives the resolution
and never writes it back. It resolves each `source`/`test` value against the
project root (the vault's parent) and reports `present` or `absent`, so a
still-to-be-created file is intent rather than a failure; it resolves `verify`
against the known final gates; and it reports `compat` as recorded. A node with
no `# Manifest` section is `empty` with exit 0.

The read surface emits authored intent and derived data separately and detects
missing or malformed entries: a bullet without `kind: value`, an empty value, an
unknown kind, or a duplicate is a `problems` row and exit 1, while well-formed
entries are still printed. `tangle check` rejects the same spelling mistakes
(`manifest-entry-malformed`, `manifest-kind-unknown`,
`manifest-entry-duplicate`), so a malformed entry cannot land.

`src/tangle/graph_check.py` owns the canonical parser (`parse_manifest`) and the
checker findings; `index.manifest` derives the view; `src/tangle/manifest.py` is
the verb, registered in `main.py` and documented by its bounded verb help and
the authoring reference. `tests/test_manifest.py` covers ready, backticked
value, empty, malformed, unknown-kind, duplicate, unknown-node, argument, and
absent-vault cases, and `tests/test_graph_check.py` exercises each new finding
code. `make test` passes: ruff, strict mypy (93 files), 840 passed / 3 skipped /
80 deselected, plus the `worktree-parallel` and `install` shell suites.
