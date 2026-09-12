---
context_rev: 1
priority: P1
updated: 2026-09-12T12:50:07Z
summary: Markdown maxima seed id_sequences, allocation skips existing filenames, and bt status reports reservations.
---

# Context

Parent [[TAS-044-usage-feedback-hardening]].

Feedback findings F1 (high) and F2 (medium): allocation numbers come only from
the sidecar counter, `bt init` and `bt reindex nodes` never seed or repair it
from the Markdown maxima, `bt allocate` does not check the filesystem, and
reservations have no audit trail or return path.

# Outcome

`bt allocate PREFIX` returns the next identity that does not collide with any
node filename in the vault, and the sidecar's `id_sequences` state is
reconcilable with and auditable against Markdown.

# Done when

- `bt init` or `bt reindex nodes` seeds and repairs each prefix from the
  Markdown maximum, and `bt allocate` refuses an identity that exists on disk.
- A regression test starts from an empty sidecar with existing nodes and proves
  that no allocated identity collides.
- `bt status` exposes reserved high-water marks, or a reconcile command lets
  reservations be returned.
- `make test` passes.

# Result

`bt init` and `bt reindex nodes` raise each prefix's reservation to the Markdown
maximum plus one; `bt allocate` models `next_value` as the value the next call
returns and skips any candidate already present on disk; `bt status` renders a
`reservations{prefix,next}` table.

Evidence:

- `test_init_seeds_reservations_from_markdown` proves init seeds TAS/IDX/THO
  reservations from a vault and that `bt status` reports them.
- `test_reindex_seeds_reservations` and
  `test_allocate_skips_on_disk_identity_with_empty_sidecar` prove a fresh
  sidecar never returns an identity that already exists on disk.
- `make test` passes.
