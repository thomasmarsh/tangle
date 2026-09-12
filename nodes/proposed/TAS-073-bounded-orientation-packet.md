---
context_rev: 1
priority: P1
updated: 2026-09-12T15:09:27Z
summary: Add a bounded `braintree orient` packet that answers focus, frontier, blockers, stale pins, recent, and conflicts in one call.
next: Compose focus, frontier, blockers, stale pins, recent, and conflicts into one bounded, section-scoped orientation packet.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

A cold session today reads `SKILL.md`, then `index-map.md`, then runs several
recipes before it can act. The orientation questions are fixed and bounded, so
one command with section flags can replace the pass.

- Builds on the direct answers from [[TAS-071-frontier-and-node-verbs]] and
  [[TAS-072-transitive-dependency-impact]].

# Outcome

`braintree orient` prints one bounded packet with focus, frontier, blockers,
stale pins, recent nodes, and open graph conflicts, section-scoped with a
default limit so it never dumps the corpus.

# Done when

- Each section is independently selectable and bounded.
- The packet is derived only from Markdown plus the rebuildable sidecar.
- Tests cover an empty vault, a single-node vault, and a vault with every
  section populated.
- `make test` passes.
