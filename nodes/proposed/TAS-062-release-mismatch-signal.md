---
context_rev: 1
priority: P1
updated: 2026-09-12T13:58:00Z
summary: Make a mismatched bt release fail loudly instead of reporting a silent no-op that leaves the lease held.
next: Return a distinct non-zero status for a hash or owner mismatch in bt release and state the release-hash rule in SKILL.md.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R4 from Tangle `THO-005-braintree-friction-kitty-spike` F2: releasing
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
