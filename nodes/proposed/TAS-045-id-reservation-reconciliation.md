---
context_rev: 1
priority: P1
updated: 2026-09-12T12:40:14Z
summary: Seed and verify id_sequences from Markdown maxima, refuse on-disk collisions, and make reservations auditable.
next: Add a failing regression test proving a fresh sidecar does not allocate an identity that exists on disk, then reconcile allocation.
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
