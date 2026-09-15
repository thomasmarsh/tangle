---
context_rev: 1
status: proposed
updated: 2026-09-15T20:38:27Z
summary: Introduce one shared graph model and parser over the vault.
next: Define the model records and the single parser, then run the behavioral comparison over the live vault and adversarial fixtures.
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md sections 1 and 7.2 replace today's several Markdown readers with one
parser and an immutable graph snapshot. Today `index.py` has its own Markdown
interpretation, `graph_check.py` owns parsing primitives shared unevenly with
`index.py`, and `store.py` reads status separately. The new boundary is
`model.py` (records and diagnostics), `format.py` (one parser, source spans,
targeted rendering), and `graph.py` (loading, identity, edges, traversals).
Behavior must be compared against the current implementation over the live vault
and adversarial fixtures for identities, edges, diagnostics, routes, gates, and
pin states; supported behavior is preserved and deliberate differences are
documented rather than treated as defects.

# Outcome

One parser produces one immutable graph snapshot that answers identity, edge,
and diagnostic questions, with a recorded behavioral comparison against the
current implementation.

# Done when

- The shared model records documents, nodes, edges, and diagnostics with source
  locations, and normalizes the relationship behaviors (containment, pinned
  context, gate, reference) while preserving authored labels.
- A comparison harness runs the current and new implementations over the live
  vault plus malformed-metadata and malformed-link fixtures and reports
  identities, edges, diagnostics, routes, gates, and pin states.
- Every difference is classified as preserved, a deliberate documented change,
  or a defect, and the classification is recorded.

# Scoping

Needs finer-grained scoping: yes. Split into the data model and parser, the
behavioral comparison harness, and per-difference disposition; each can be
accepted independently.
