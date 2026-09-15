---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Reject a claim or release base hash that is not a bare lowercase 64-character hex digest, naming the offending form.
---

# Context

Parent [[TAS-095-usage-feedback-hardening-round-four]].

Hekate `FBK-004` at `0.5.0+g64359e6`. Reproduced in
[[THO-013-round-four-usage-feedback-and-portfolio-analysis]] with an isolated
sidecar and the probe vault `/tmp/tangle-r4`:

- A claim whose `--base-hash` was the whole `tangle hash` output printed
  `result: "claimed"` and echoed the two-line `node:`/`content_hash:` block as
  the recorded `base_hash`, so a mis-piped operand silently became the lease
  identity.
- The bare digest `SKILL.md` tells the worker to pass then failed on release,
  non-zero, with `base hash does not match the recorded claim`, forcing a
  release-and-reclaim once the mistake was noticed.

`_claim` and `_release` in `src/tangle/cli.py` accept any non-empty string;
nothing validates the digest shape. `tests/test_tangle_foundation.py` passes the
short placeholders `abc`, `def`, and `ghi`, so the guard has to update those
call sites to real digests.

# Outcome

An operand that is not a bare 64-character lowercase hex digest fails claim and
release immediately, non-zero, naming the offending form, so a malformed base
hash can never become a recorded lease identity.

# Done when

- `tangle claim --base-hash` and `tangle release --base-hash` reject a value that is not a bare 64-character lowercase hex digest, with a diagnostic that names the accepted form.
- The shape check runs before any sidecar write, so a rejected operand leaves no claim and cannot create or renew a lease.
- Tests cover the labelled multi-line block, a short placeholder, an uppercase digest, and a valid digest, and the existing placeholder-hash tests use real digests.
- `make test` passes.

# Result

`_claim` and `_release` in `src/tangle/cli.py` now validate `--base-hash`
against `_BASE_HASH`, a bare 64-character lowercase hex digest pattern, before
calling the sidecar. A value that does not match — the labelled two-line
`node:`/`content_hash:` block `tangle hash` prints, a short placeholder, or
an uppercase digest — fails the argument path with exit `2` and
`--base-hash must be a bare 64-character lowercase hex digest, not <value>`,
which names the accepted form and echoes the offending value. The guard sits
before any connection is opened, so a rejected operand creates no sidecar, and
records or renews no lease. The regression tests that passed the short
placeholders `abc`, `def`, and `ghi` now pass real digests, and
`tests/test_tangle_verification.py` contention, expiry, and worktree cases do too.

Evidence:

- `test_claim_and_release_reject_a_non_digest_base_hash` covers the labelled
  multi-line block, a short placeholder, and an uppercase digest for both claim
  and release, and asserts no sidecar file is created.
- `test_claim_and_release_accept_a_bare_digest` pins that a valid digest still
  claims and releases, and
  `test_hash_content_hash_is_the_claim_and_release_operand` keeps the
  `tangle hash` → `--base-hash` round trip on a real digest.
- `tangle check nodes` and `make test` pass.

Limitations: the guard covers the operand shape only. A valid-shaped digest
that does not match the recorded claim still follows the existing exit-1
`ReleaseConflict` path, and `claim`/`release` keep treating the digest as an
opaque string rather than re-hashing the node.
