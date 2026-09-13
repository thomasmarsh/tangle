---
context_rev: 1
priority: P2
updated: 2026-09-13T21:49:10Z
summary: Maintain the derived index automatically on every interaction and stop naming SQLite or the sidecar as a client concept.
next: Maintain the derived index automatically on all interactions and remove SQLite from the client-facing contract.
---

# Context

Parent [[TAS-161-routine-interaction-zero-ceremony]].

`references/coordination.md` opens with a "Hybrid sidecar contract" that teaches
clients to run `braintree index`, to run `braintree init` before coordinated
work, to recover with `braintree init` then `braintree index`, and to reason
about SQLite/WAL, `BT_SIDECAR_DIR`/`BT_PROJECT_ID`, and network-mounted
locations. `references/authoring.md` and `SKILL.md` also name the sidecar. The
sidecar is derived, disposable coordination state; a client should neither have
to know it exists nor keep it current by hand. Automatic maintenance is the
prerequisite that makes removing it from the client contract truthful, so the two
land together.

# Outcome

Interactions maintain the derived index automatically and incrementally,
`braintree index` survives only as an explicit repair or rebuild, and `SKILL.md`
and `references/` no longer present SQLite, the sidecar, or an index-update step
as a client-managed concept; they state only the markdown-authoritative behavior
and concurrency guarantees a client relies on.

# Done when

- Mutating and direct-answer interactions keep the derived index current without
  a separate client step.
- `braintree index` remains available only as repair or rebuild, and its help
  says so.
- `SKILL.md` and `references/` no longer name SQLite or the sidecar as a client
  concept, while the markdown authority and concurrency guarantees remain stated.
- Rebuilding the index from Markdown alone recovers after its loss.
- Tests cover automatic maintenance and the rebuild-from-markdown recovery.
- `make test` passes.
