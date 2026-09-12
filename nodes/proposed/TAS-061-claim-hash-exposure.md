---
context_rev: 1
priority: P2
updated: 2026-09-12T13:58:00Z
summary: Document the claim base-hash algorithm and expose the value through bt so a worker never infers it from the source.
next: Document that the claim base hash is the SHA-256 of the raw UTF-8 node file and add a bt hash command or a hash field in an existing read command.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R3 from Tangle `THO-005-braintree-friction-kitty-spike` F1:
`SKILL.md` requires hashing the starting node for `bt claim`, but names no
algorithm, and no `bt` read command exposes a content hash, so a worker must
read the Python or guess.

# Outcome

The skill names the exact hash (SHA-256 hex of the raw UTF-8 file bytes,
including frontmatter), and `bt` exposes the value the claim compares against.

# Done when

- `SKILL.md` documents the base-hash algorithm in the hybrid-sidecar section.
- `bt hash NODE` (or a hash field in `bt search`/`bt status`) returns the same value the sidecar records.
- A regression test pins the documented algorithm to the sidecar's `sha256(text)`.
- `make test` passes.
