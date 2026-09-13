---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Reject a wikilink inside an action-sentence next by name and prescribe anchored dependency searches.
next: Reject a wikilink inside an action-sentence next by name and prescribe anchored dependency searches.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-019` A and B at `0.6.0+g3bacaf5`. Probe: a `next` written as
`Move this node to resolved once [[IDX-001-scratch]] closes.` fails with
`frontier is not a direct child` and the diagnostic names no link, so the
offending link must be found by trial; `SKILL.md` does not say an action sentence
must contain no wikilink. Separately, `references/coordination.md` prescribes
`rg -n -F 'Depends on [[ID]] at context_rev '` and
`references/dependencies.md` prescribes `rg -n -F 'Gated on [[...]]'`; both are
unanchored and match the command text where a node quotes it, so a "zero
consumers" reading requires inspection.

# Outcome

`SKILL.md` states that a `next` written as an action sentence must contain no
wikilink, `braintree check` names the token it treated as the frontier route, and
the dependency references prescribe an anchored search that matches a pin or gate
line rather than a quoted command.

# Done when

- The no-wikilink action-sentence rule is in `SKILL.md` and pinned by a contract
  test.
- The `next-not-direct-child`/`next-resolved-node` diagnostic names the offending
  link or token.
- `references/dependencies.md` and `references/coordination.md` use an anchored
  search form, and the self-match hazard is stated.
- Tests cover the diagnostic and the anchored recipe.
- `make test` passes.
