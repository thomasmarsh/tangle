---
context_rev: 1
priority: P2
updated: 2026-09-12T17:32:35Z
summary: Fix or dispose the round-four Tangle feedback findings and close the one admitted portfolio gap in the node-capture path.
next: "[[TAS-096-base-hash-validation]]"
---

# Context

Parent [[THO-013-round-four-usage-feedback-and-portfolio-analysis]].

`FBK-003` and `FBK-004` verified in the parent at `0.5.0`
(`0.5.0+g64359e6`); `FBK-001` and `FBK-002` are disposed there as already fixed
by [[TAS-086-unresolved-dependency-representation]] and
[[TAS-085-hash-addressing-and-operand]].

# Outcome

Every confirmed round-four finding is fixed or explicitly disposed, and the one
admitted portfolio gap is closed or disposed, with regression tests wherever
behavior changes.

# Done when

- `braintree claim` and `braintree release` reject a `--base-hash` that is not a bare 64-character lowercase hex digest, naming the offending form.
- `SKILL.md` states the slice write-set rule for authoring a minimal primitive or seam a gate needs.
- A client creates a routed, correctly-stamped node of any type in one documented step.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-096-base-hash-validation]] — `FBK-004`.
- [[TAS-097-slice-primitive-scope]] — `FBK-003`.
- [[TAS-098-node-capture-path]] — the portfolio capture gap.
