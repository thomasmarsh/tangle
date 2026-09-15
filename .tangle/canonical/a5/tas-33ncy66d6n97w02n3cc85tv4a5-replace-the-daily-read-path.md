---
context_rev: 1
status: proposed
updated: 2026-09-15T20:38:27Z
summary: Replace the daily read path with the shared graph snapshot.
next: Move `check` onto the shared snapshot and delete the parser it supersedes.
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md sections 2, 5, and 7.3 move the daily read path onto the shared
snapshot: `check`, `packet`, node inspection, and impact. They must work with no
sidecar, no model installation, and an unwritable package cache, and each
migration removes the parser or duplicate route implementation it supersedes.
The shared snapshot is a direct child of this program, not a dependency of the
current implementation.

This overlaps prior commitments:
[[tas-32btrf71jvz66am5pempkhqapy-assemble-packet-s-manifest-acceptance-context]]
and
[[tas-7y1wpfb0d1shhtq8qq5tfnyx7d-packet-default-entry-point-and-skill-shorten]]
own the packet surface, and [[TAS-204-full-census-indexing-markdown-views]] owns
full-census discovery and generated views. Reference rather than duplicate.

# Outcome

`check`, `packet`, node inspection, and impact answer from one shared snapshot
without a sidecar, model install, or writable cache, and superseded parsers and
duplicate route implementations are gone.

# Done when

- Each of the four read surfaces is served by the shared snapshot and its
  focused tests pass with a read-only package cache and no model installed.
- `tangle check` reports the same graph findings on the live vault before and
  after each surface moves, except for documented deliberate changes.
- Superseded parsing and route code is deleted as each consumer moves.

# Scoping

Needs finer-grained scoping: yes. Create one child per read surface (`check`,
`packet`, node inspection, impact) plus a deletion child for superseded parsers
and duplicate routes; each surface is independently migratable and acceptable.
