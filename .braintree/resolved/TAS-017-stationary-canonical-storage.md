---
context_rev: 2
priority: P2
updated: 2026-09-10T21:03:15Z
summary: Retain authoritative status directories; stationary storage and derived views add worse tradeoffs.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Outcome

Decide whether canonical nodes should stay in a stationary hash- or prefix-sharded location while status is exposed through symlinks or derived indexes, instead of directory moves.

# Done when

The evaluation records a recommendation with evidence about Git behavior, portability, query ergonomics, authority, and conflict characteristics.

# Result

`scripts/storage-comparison.rb --verify` uses disposable 100-node Git fixtures.
Directory authority stages an unchanged transition as `R100`, reads zero node
bodies for the 25-node active query, has zero different-node merge conflicts,
and has no derived-view failure. Stationary `status` metadata preserves the
canonical editor path but reads all 100 canonical files. Symlink views retain
the `R100` transition and zero body reads, but an omitted link hides an existing
canonical node; they also add filesystem/Git symlink portability constraints.
A copied index reads one file but its concurrent one-line transitions conflict
and an omitted entry hides a node.

Keep the current status-directory representation. It has one authority, no
mandatory generated cache, portable ordinary files, bounded status discovery,
and Git rename tracking; the acceptable cost is that the editor path changes
when status changes while basename wikilinks remain stable.
