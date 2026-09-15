---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Markdown maxima seed id_sequences, allocation skips existing filenames, and tangle status reports reservations.
---

# Context

Parent [[TAS-044-usage-feedback-hardening]].

Feedback findings F1 (high) and F2 (medium): allocation numbers come only from
the sidecar counter, `tangle init` and `tangle reindex nodes` never seed or repair it
from the Markdown maxima, `tangle allocate` does not check the filesystem, and
reservations have no audit trail or return path.

# Outcome

`tangle allocate PREFIX` returns the next identity that does not collide with any
node filename in the vault, and the sidecar's `id_sequences` state is
reconcilable with and auditable against Markdown.

# Done when

- `tangle init` or `tangle reindex nodes` seeds and repairs each prefix from the
  Markdown maximum, and `tangle allocate` refuses an identity that exists on disk.
- A regression test starts from an empty sidecar with existing nodes and proves
  that no allocated identity collides.
- `tangle status` exposes reserved high-water marks, or a reconcile command lets
  reservations be returned.
- `make test` passes.

# Result

`tangle init` and `tangle reindex nodes` raise each prefix's reservation to the Markdown
maximum plus one; `tangle allocate` models `next_value` as the value the next call
returns and skips any candidate already present on disk; `tangle status` renders a
`reservations{prefix,next}` table.

Evidence:

- `test_init_seeds_reservations_from_markdown` proves init seeds TAS/IDX/THO
  reservations from a vault and that `tangle status` reports them.
- `test_reindex_seeds_reservations` and
  `test_allocate_skips_on_disk_identity_with_empty_sidecar` prove a fresh
  sidecar never returns an identity that already exists on disk.
- `make test` passes.
