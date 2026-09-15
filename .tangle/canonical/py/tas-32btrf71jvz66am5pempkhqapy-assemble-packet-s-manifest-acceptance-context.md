---
context_rev: 1
priority: P1
status: proposed
updated: 2026-09-15T14:36:52Z
summary: Assemble packet's manifest, acceptance context, and files; support scoped input.
next: Have tangle packet call manifest.derive_manifest for the ready node and print its resolved source, test, verify, and compat entries alongside files.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

Live evidence: `tangle packet` on `TAS-204` prints `files[1]{path}: "canonical/04/TAS-204-..."` -- only the task's own path. `src/tangle/packet.py` never calls `manifest.derive_manifest`, so a fresh worker still has to run `tangle manifest NODE` separately and has no route to an explicitly scoped node or initiative.

Gates my artifacts enter: `tests/test_tangle_index.py` and any new `tests/test_packet.py` for packet behavior, `tests/test_manifest.py` for manifest derivation, `tests/test_skill.py` for the client-responsibility boundary, and default ruff, mypy, and pytest discovery.

# Outcome

`tangle packet` reports a bounded, sufficient-to-start execution context by default: the ready node's manifest-derived source/test/verify/compat entries alongside its own path, and an explicit node or initiative operand narrows the answer instead of only ever returning the sole global frontier candidate.

# Done when

- `tangle packet`'s `files` output includes the ready node's manifest `source` and `test` entries (existing or explicitly `absent`), not only its own path.
- `verification` includes manifest `verify` entries alongside the existing fixed gates, deduplicated.
- `tangle packet NODE` (or an equivalent scoped operand) answers for one explicitly named node/initiative rather than only the global frontier, reporting the same structured ready/blocked/ambiguous/invalid shape scoped to that subtree.
- A packet for a node with an empty `# Manifest` reports `files` unchanged (own path only) rather than failing, matching `tangle manifest`'s `empty` semantics.
- Tests cover a node with a populated manifest, an empty manifest, a manifest naming an absent path, and the scoped-operand case.
- `tangle check` and `make test` pass; this stays an offline, deterministic verification per ASTRA's own evaluation-cost guidance -- no new live-agent benchmark is required to accept it.
