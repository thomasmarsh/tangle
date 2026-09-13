---
context_rev: 1
updated: 2026-09-12T21:14:39Z
summary: Round-five Tangle feedback confirms two new findings at 0.5.0 (gd1a4b82) in lease lifecycle visibility and the coordinator closeout and verification contract, and disposes the four earlier ones.
---

# Question

Area [[IDX-001-execution-graph]].

`braintree feedback scan /Users/thomasmarsh/git/tangle` reports two proposed
feedback nodes recorded after the round analyzed in
[[THO-013-round-four-usage-feedback-and-portfolio-analysis]]: Tangle
`FBK-005` and Tangle `FBK-006`, both at `0.5.0+gd1a4b82`. The ids collide with
this vault's own `FBK` numbering, so they are cited as Tangle `FBK-00N`. Which
findings still hold against this implementation at `0.5.0` (`ba362e3`), and
what self-improvement work do they require?

# Conclusion

Reproduction used an isolated probe vault at `/tmp/bt-r5` with
`BT_NODES_DIR`/`BT_SIDECAR_DIR`/`BT_PROJECT_ID`, so no reservation state and no
vault state was disturbed.

| Feedback | Scan revision | Verdict | Evidence |
|----------|---------------|---------|----------|
| Tangle `FBK-005` | `0.5.0+gd1a4b82` | open, admitted | The default lease is `900` seconds and is set only in `src/braintree/cli.py` (`lease_raw = "900"`); `SKILL.md` says `claim` "acquires or renews a lease" and shows `[--lease-seconds N]` but states no default. Probe: a default `claim` printed `lease_expires_at` 900 s after `now`, a repeat claim with the same agent and hash moved the expiry forward (renew-on-reclaim already holds), and after a one-second lease lapsed `release` returned `result: "no-op"`, indistinguishable from a node never held, after which a second agent claimed the same node. `claim` prints only an absolute epoch and `release` prints no remaining time. |
| Tangle `FBK-006` gap 1 | `0.5.0+gd1a4b82` | open, admitted | `SKILL.md` says "the coordinator ... alone resolves a coordinating parent after all required child work is integrated", but no text says a worker slice prepares closeout evidence only, and the word `closeout` does not appear. A harness that gives a worker a "resolution slice" still has no stated boundary, so it is unclear whether the resolving edit is a coordinator action or must be delegated to a fresh writer. |
| Tangle `FBK-006` gap 2 | `0.5.0+gd1a4b82` | open, admitted | `SKILL.md` names no verification actor, reviewer, or gate transcript; the only verification-boundary text is the node-admission phrase "routine verification ... never qualify". A read-only reviewer with no shell cannot execute the gates it is asked to verify, so its sign-off cannot falsify a recorded gate claim. |

Disposed without re-admission:

- Tangle `FBK-001` and `FBK-002` are fixed and disposed in
  [[THO-013-round-four-usage-feedback-and-portfolio-analysis]]; re-admitting
  fixed friction would be node churn.
- Tangle `FBK-003` and `FBK-004` remain open but are already admitted as
  [[TAS-097-slice-primitive-scope]] and [[TAS-096-base-hash-validation]] under
  [[TAS-095-usage-feedback-hardening-round-four]], so they are not re-admitted
  here.

# Decision

Create the coordinating task [[TAS-099-usage-feedback-hardening-round-five]]
with one child per independently resumable confirmed change:

- [[TAS-100-lease-lifecycle-visibility]] — Tangle `FBK-005`.
- [[TAS-101-resolution-ownership-clarity]] — Tangle `FBK-006` gap 1.
- [[TAS-102-verification-evidence-contract]] — Tangle `FBK-006` gap 2.

Round five is `P2`. Tangle `FBK-005` names a real coordination hazard once a
slice outlives its lease, but the 900 s default, the documented renew-on-reclaim
behavior, and single-writer serial handoff mean no finding blocks coordination
or makes the claim path incorrect; a worker can still claim and release
correctly. It therefore does not displace the `P1` frontier routed by
[[TAS-087-off-the-shelf-embedding-and-clustering]].
