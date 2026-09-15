---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: A mismatched bt release fails loudly with a named cause and non-zero status; no-op now means only that no unexpired lease exists.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R4 from Hekate `THO-005-braintree-friction-kitty-spike` F2: releasing
with the post-edit hash prints `result: "no-op"` and exits 0 while the lease
stays held, so a worker can hand off with the claim still blocking others.

# Outcome

A mismatched `bt release` fails with a non-zero exit and an explicit message, or
the no-op case is named distinctly from success, and the release-hash rule is
documented.

# Done when

- A hash or owner mismatch returns a distinct non-zero status and names the cause.
- `SKILL.md` states that the release hash must be the recorded starting hash.
- A regression test covers the mismatch and the successful release.
- `make test` passes.

# Result

Took the fail-loudly branch. `sidecar.release` now reads the node's unexpired
lease and removes it only when both the agent and the base hash match; it
returns `released` on a match and `no-op` only when the node holds no unexpired
lease. When a lease exists for another agent or records a different hash it
raises `ReleaseConflict` carrying the recorded owner and hash. `bt release` maps
that conflict to exit `1` and an `error` field naming the owning agent or the
base-hash mismatch, so a post-edit hash can no longer masquerade as a successful
release while the claim stays held.

Evidence:

- `sidecar.release` returns `released`/`no-op` and raises `ReleaseConflict` on a
  hash or owner mismatch.
- `bt release` names the cause and exits `1` on a mismatch while the success and
  no-op paths keep their existing `result` output and exit `0`.
- `SKILL.md` states the release hash must be the starting hash recorded by the
  claim and reserves `no-op` for a node with no unexpired lease.
- `test_claim_renew_conflict_and_release` and `tests/bt-foundation.sh` cover a
  wrong hash, a wrong owner, the still-held lease, the successful release, and
  the idempotent no-op.
- `make test` passes.
