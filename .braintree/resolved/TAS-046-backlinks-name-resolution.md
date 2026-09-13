---
context_rev: 1
priority: P2
updated: 2026-09-12T12:50:07Z
summary: bt backlinks resolves a full node name or bare ID, errors on an unknown node, and keeps zero for a real edgeless node.
---

# Context

Parent [[TAS-044-usage-feedback-hardening]].

Feedback finding F3 (medium): `bt backlinks` matches only the exact bare ID, so
a full node name returns `backlinks: 0 matching edges` even when edges exist,
and an unknown node returns the same silent zero.

# Outcome

`bt backlinks NODE` accepts a full node name or a bare ID, fails loudly on an
unknown node, and reserves the zero-edge message for a real node with no
incoming edges.

# Done when

- A full node name and its bare ID return identical edges.
- An unknown node exits nonzero with an error that names the node.
- Regression tests cover both cases, and `make test` passes.

# Result

`index.resolve_node` maps a bare ID or a full node name to the indexed ID, and
`bt backlinks` reports `unknown node: <name>` with exit code 1 instead of a
silent zero. A real node with no incoming edges still prints
`backlinks: 0 matching edges`.

Evidence:

- `test_backlinks_resolve_full_name_and_reject_unknown` asserts that
  `DEF-001` and `DEF-001-contract` return the same edges, that an edgeless
  `DEF-002-leaf` returns the zero message with exit 0, and that `DEF-999` exits
  1 naming the node.
- `make test` passes.
