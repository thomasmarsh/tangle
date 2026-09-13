---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Fix or dispose the round-seven Tangle feedback findings: premise correction, resolved-child completion, allocation visibility, next/search diagnostics, handoff artifact naming, definition completeness, derived artifacts, session slices, and summary integrity.
next: "[[TAS-138-premise-correction-rule]]"
---

# Context

Parent [[THO-021-round-seven-usage-feedback-analysis]].

Tangle `FBK-016` through `FBK-025` verified in the parent at `0.6.0+g3bacaf5`.
Tangle `FBK-001` through `FBK-015` are handled under
[[TAS-095-usage-feedback-hardening-round-four]],
[[TAS-099-usage-feedback-hardening-round-five]], and
[[TAS-111-usage-feedback-hardening-round-six]] and are not in scope here.
`FBK-018` finding 2 and `FBK-025` finding 2 are merged; `FBK-023` finding 3 is
merged into `FBK-017`; `FBK-023` finding 1 is routed to
[[THO-019-advisory-size-and-effort-hints]]; `FBK-018` finding 1 and `FBK-023`
finding 2 are disposed out of scope.

# Outcome

Every confirmed round-seven finding is fixed or explicitly disposed, with
regression tests wherever behavior changes.

# Done when

- `SKILL.md` states the premise-correction rule and its `context_rev` and
  escalation boundary.
- The contract states the resolved-child worker completion path and the checker
  separates the multi-writer transient from a genuine stale route.
- `braintree allocate` burn semantics are documented and outstanding
  reservations are inspectable.
- A `next` action sentence may not contain a wikilink, the checker names the
  offending token, and the dependency references prescribe an anchored search.
- A handoff that orders reuse of an artifact names its concrete path.
- A definition covers, or names a successor for, every consumer-visible shape
  its consumers must author.
- Derived-artifact regeneration ownership and reporting are stated.
- The session-slice rule and the blocked-to-proposed revision question are
  answered.
- An over-long summary fails, warns, or truncates on a word boundary with an
  ellipsis, and the limit is documented.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-138-premise-correction-rule]] - Tangle `FBK-016`.
- [[TAS-139-resolved-child-completion-path]] - Tangle `FBK-017`, `FBK-023` finding 3.
- [[TAS-140-allocation-lifecycle-visibility]] - Tangle `FBK-018` finding 2, `FBK-025` finding 2.
- [[TAS-141-next-and-pin-search-diagnostics]] - Tangle `FBK-019` A and B.
- [[TAS-142-handoff-names-referenced-artifacts]] - Tangle `FBK-020`.
- [[TAS-143-definition-completeness-for-deferred-shapes]] - Tangle `FBK-021`.
- [[TAS-144-derived-artifact-regeneration-ownership]] - Tangle `FBK-022`.
- [[TAS-145-session-slice-and-blocker-revision]] - Tangle `FBK-024`.
- [[TAS-146-summary-truncation-integrity]] - Tangle `FBK-025` finding 1.
