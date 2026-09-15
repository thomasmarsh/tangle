---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State the default lease duration and renew-on-reclaim rule, show remaining lease time, and distinguish an expired lease from one never held.
---

# Context

Parent [[TAS-099-usage-feedback-hardening-round-five]].

Hekate `FBK-005` at `0.5.0+gd1a4b82`. Reproduced in
[[THO-014-round-five-usage-feedback-analysis]] with the probe vault `/tmp/tangle-r5`
and an isolated sidecar:

- The default lease is `900` seconds, set only in `src/tangle/cli.py`
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
- `tangle claim` and `tangle release` report remaining lease time, or an equally explicit expiry signal, on every call.
- `tangle release` returns a distinct `expired` result, naming that a matching lease lapsed, instead of the undifferentiated `no-op` when the node held an expired lease.
- Tests cover the default duration, renew-on-reclaim extension, and the expired-versus-never-held distinction, and `make test` passes.

# Result

`SKILL.md`'s hybrid sidecar bullet now states the 900-second default lease, that
`--lease-seconds N` chooses another duration, and that a claim repeating the
same agent and base hash renews the lease to a fresh `N` seconds. It also states
that `claim` and `release` report `lease_remaining_seconds` and that `release`
distinguishes `expired` from `no-op`.

`sidecar.claim` returns the remaining seconds alongside owner, hash, and expiry,
and `cli._claim` prints `lease_remaining_seconds`. `sidecar.release` now returns
`(result, remaining)`: `released` for the matching live lease, `expired` when the
caller's matching lease had lapsed (checked before the expiry sweep clears the
row), and `no-op` when no matching claim is recorded. `cli._release` prints
`lease_remaining_seconds` on every result, and the help tables in
`src/tangle/cli.py` and `src/tangle/main.py` name the 900-second default
and the expired result.

Evidence: new `tests/test_tangle_foundation.py` tests
`test_claim_states_the_default_lease_duration` (default reports 900),
`test_reclaim_with_the_same_agent_and_hash_renews_the_lease` (60 then 300
seconds, proving the stored expiry is replaced), and
`test_release_separates_expired_from_never_held` (no-op with no claim, expired
after a lapsed matching claim, then a second agent can claim);
`test_tangle_verification.py::test_expiry_and_base_hash_mismatch` extends the
cross-process screen with the expired-versus-never-held distinction;
`test_skill.py::test_skill_lease_lifecycle_contract` pins the new `SKILL.md`
text. `tangle check nodes`, `make test`, `uv run ruff check`, and
`uv run mypy` pass.

Limitations: `release` reports `no-op` when a *different* agent's lapsed claim is
the only record for the node, matching the prior pre-sweep behavior; the
distinction the node asks for is between the caller's own lapsed lease and a node
that never held one. The default is stated in prose and covered by a test rather
than exposed as a named constant.
