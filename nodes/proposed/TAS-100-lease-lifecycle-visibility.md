---
context_rev: 1
priority: P2
updated: 2026-09-12T21:14:39Z
summary: State the default lease duration and renew-on-reclaim rule, show remaining lease time, and distinguish an expired lease from one never held.
next: State the default lease duration and renew-on-reclaim rule in SKILL.md, make claim and release report remaining lease time and separate an expired lease from one never held, then pin it with tests.
---

# Context

Parent [[TAS-099-usage-feedback-hardening-round-five]].

Tangle `FBK-005` at `0.5.0+gd1a4b82`. Reproduced in
[[THO-014-round-five-usage-feedback-analysis]] with the probe vault `/tmp/bt-r5`
and an isolated sidecar:

- The default lease is `900` seconds, set only in `src/braintree/cli.py`
  (`lease_raw = "900"`); `SKILL.md` states no default and never shows a way to
  choose `--lease-seconds` knowingly.
- `claim` with the same agent and base hash already renews the lease, but the
  renew rule is only implied by the word "renews".
- After a one-second lease lapsed, `release` returned `result: "no-op"` — the
  same answer as a node never held — and a second agent then claimed the node,
  exactly the divergence the claim exists to prevent.

# Outcome

Lease lifetime is explicit and observable: the default duration and
renew-on-reclaim rule are documented, a long slice can see its remaining
lease, and an expired lease is distinguishable from one never held, so a
worker cannot silently hand off a lapsed claim.

# Done when

- `SKILL.md` states the default lease duration and that a claim with the same agent and base hash renews the lease.
- `braintree claim` and `braintree release` report remaining lease time, or an equally explicit expiry signal, on every call.
- `braintree release` returns a distinct `expired` result, naming that a matching lease lapsed, instead of the undifferentiated `no-op` when the node held an expired lease.
- Tests cover the default duration, renew-on-reclaim extension, and the expired-versus-never-held distinction, and `make test` passes.
