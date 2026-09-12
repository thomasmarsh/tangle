---
context_rev: 1
priority: P2
updated: 2026-09-12T12:40:14Z
summary: bt backlinks resolves a full node name, errors on an unknown node, and never reports a silent zero.
next: Add a regression test that a full node name and its bare ID return the same edges and an unknown name exits nonzero.
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
