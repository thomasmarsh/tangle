---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Fail or warn on an over-long summary, or truncate on a word boundary with an ellipsis, and document the limit.
next: Fail or warn on an over-long summary, or truncate on a word boundary with an ellipsis, and document the limit.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-025` finding 1 at `0.6.0+g3bacaf5`. Probe: `braintree node record`
with a summary longer than 96 characters exited `0` and stored a summary cut
mid-phrase (`...so that a truncation becomes`); `_SUMMARY_LIMIT = 96` in
`node_record.py` applies `[:_SUMMARY_LIMIT]` silently, and `references/authoring.md`
documents no limit, so four stored summaries in a real vault ended mid-sentence.

# Outcome

`braintree node record` and `braintree feedback record` never silently store a
mid-phrase summary: an over-long summary fails or warns, or truncates on a word
boundary with an explicit ellipsis, and the limit is documented in
`references/authoring.md` and printed by the relevant help.

# Done when

- The chosen behavior is implemented for both capture commands.
- The length limit is documented in `references/authoring.md` and surfaced by the
  relevant help.
- Tests cover the boundary and the failure or warning.
- `make test` passes.
