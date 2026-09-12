---
context_rev: 1
priority: P2
updated: 2026-09-12T17:32:35Z
summary: Reject a claim or release base hash that is not a bare lowercase 64-character hex digest, naming the offending form.
next: Guard the claim and release argument parsing with a digest-shape check before the sidecar write, then update the tests that pass short placeholder hashes.
---

# Context

Parent [[TAS-095-usage-feedback-hardening-round-four]].

Tangle `FBK-004` at `0.5.0+g64359e6`. Reproduced in
[[THO-013-round-four-usage-feedback-and-portfolio-analysis]] with an isolated
sidecar and the probe vault `/tmp/bt-r4`:

- A claim whose `--base-hash` was the whole `braintree hash` output printed
  `result: "claimed"` and echoed the two-line `node:`/`content_hash:` block as
  the recorded `base_hash`, so a mis-piped operand silently became the lease
  identity.
- The bare digest `SKILL.md` tells the worker to pass then failed on release,
  non-zero, with `base hash does not match the recorded claim`, forcing a
  release-and-reclaim once the mistake was noticed.

`_claim` and `_release` in `src/braintree/cli.py` accept any non-empty string;
nothing validates the digest shape. `tests/test_bt_foundation.py` passes the
short placeholders `abc`, `def`, and `ghi`, so the guard has to update those
call sites to real digests.

# Outcome

An operand that is not a bare 64-character lowercase hex digest fails claim and
release immediately, non-zero, naming the offending form, so a malformed base
hash can never become a recorded lease identity.

# Done when

- `braintree claim --base-hash` and `braintree release --base-hash` reject a value that is not a bare 64-character lowercase hex digest, with a diagnostic that names the accepted form.
- The shape check runs before any sidecar write, so a rejected operand leaves no claim and cannot create or renew a lease.
- Tests cover the labelled multi-line block, a short placeholder, an uppercase digest, and a valid digest, and the existing placeholder-hash tests use real digests.
- `make test` passes.
