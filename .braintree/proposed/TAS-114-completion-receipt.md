---
context_rev: 1
priority: P2
updated: 2026-09-13T02:14:00Z
summary: Make a worker's completion signal explicit, so a report-time timeout is distinguishable from an implementation-time failure.
next: State the completion receipt and the trusted completion signal in the contract and pin them.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-010` at `0.5.0+g974b178`, verified in
[[THO-017-round-six-usage-feedback-analysis]]. A slice worker ran the full
1800000 ms budget and the run was reported failed with "Subagent timed out
after 1800000ms", but the worker had already committed its slice, refreshed the
node, run all five gates, and released its claim; it timed out only while
composing the final prose report. The failed status plus the revive-first
guidance implied unfinished work, and the only durable completion signal
(`result: released` at the recorded base hash) was buried near the end of the
run log. `SKILL.md` and `references/coordination.md` name no completion receipt
and never state which signal the coordinator trusts; `receipt` matches only
benchmark code.

# Outcome

A worker emits a compact structured completion receipt before its long
narrative report, and the contract states that a `release` result at the
recorded base hash is the completion signal the coordinator trusts over the run
status, so a report-time timeout is distinguishable from unfinished work.

# Done when

- `references/coordination.md` or `SKILL.md` states that a worker records a compact completion receipt — base hash, `release` result, gate summary, and commit SHAs — before its narrative report.
- The contract states that a `release` result at the recorded base hash is the completion signal the coordinator trusts over the run status when a run times out during reporting.
- A contract test in `tests/test_skill.py` pins the stated rule.
- `make test` passes.
