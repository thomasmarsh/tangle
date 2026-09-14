---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Make a worker's completion signal explicit, so a report-time timeout is distinguishable from an implementation-time failure.
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

# Result

`references/coordination.md` records the completion receipt and the trusted completion signal, and `tests/test_skill.py` pins the rule.

- Under `## Worker handoff`, the reference now states: "A worker records a compact structured completion receipt before its long narrative report: the recorded base hash, the `release` result, a gate summary, and the commit SHAs. A `release` result at the recorded base hash is the completion signal the coordinator trusts over the run status: when a run times out while the worker is still composing prose, that release states the work is finished even though the run reported failure."
- `tests/test_skill.py` adds the `_COMPLETION_RECEIPT_RULE` constant and `test_completion_receipt_is_the_trusted_signal`, which reads `references/coordination.md` through the existing `_reference` helper in the neighbours' literal-substring style. Removing the rule text fails the test (`1 failed`); restoring it passes.
- No `SKILL.md` edit: the core already routes a worker to the coordination reference before handoff, so the always-loaded surface stays unchanged.

Evidence: `uv run pytest tests/test_skill.py -q -k completion_receipt` passed 1; the deliberate-removal probe failed as intended; `make test` ran 366 passed, 3 skipped, 79 deselected; `braintree check` passed.
