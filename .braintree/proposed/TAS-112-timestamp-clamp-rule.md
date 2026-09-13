---
context_rev: 1
priority: P2
updated: 2026-09-13T02:14:00Z
summary: State how a worker treats an assigned node's `updated` when it is ahead of the host clock, so refreshing `updated` never moves it backwards.
next: State the incoming-future `updated` rule in the contract and pin it with a test.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-007` at `0.5.0+gba362e3`, reproduced in
[[THO-017-round-six-usage-feedback-analysis]]: an assigned node arrived with
`updated: 2026-09-13T00:00:00Z`, a day-boundary placeholder, while the host
clock at handoff read about `2026-09-12T21:33Z`, roughly two and a half hours
earlier. `SKILL.md` defines `updated` only as "Refresh `updated` to the current
UTC ISO-8601 time on every mutation" and gives no rule for an incoming future
timestamp, so honoring the instruction literally moves `updated` backwards and
a reader cannot distinguish a coordinator placeholder from a worker
regression. The FBK's secondary note — an integration test needs the tested
crate surface genuinely public — is a write-set closure member and is covered
by [[TAS-113-write-set-change-closure]].

# Outcome

A worker that receives an assigned node whose `updated` is ahead of the host
clock has one stated rule to follow, so refreshing `updated` never silently
moves the field backwards and it stays a monotonic record a reader can trust.

# Done when

- `SKILL.md` states a single rule for an incoming `updated` ahead of the host clock — either the coordinator must stamp the real UTC time rather than a day boundary, or the worker refreshes to `max(now, previous updated)` and notes the clamp — so the two instructions no longer conflict.
- A contract test in `tests/test_skill.py` pins the stated rule.
- `make test` passes.
