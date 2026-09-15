---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Fix or dispose the round-four Hekate feedback findings and close the one admitted portfolio gap in the node-capture path.
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

# Result

Resolved. All three children are resolved and every `Done when` criterion is
met:

- [[TAS-096-base-hash-validation]] rejects a `--base-hash` that is not a bare
  64-character lowercase hex digest before any sidecar write, naming the
  offending form (`f550b51`).
- [[TAS-097-slice-primitive-scope]] states the slice write-set authoring rule
  in `SKILL.md` and pins it with a contract test (`b73c08f`).
- [[TAS-098-node-capture-path]] lands `braintree node record`, one command that
  creates a routed, correctly-stamped node of type `THO`, `DEF`, `DEC`, or
  `TAS` (`f3c19b8`).

Evidence: `braintree check nodes` -> `graph check: passed (123 nodes)`; `make
test` -> `399 passed, 3 skipped`.

Limitations: the capture path supplies the stamp, not the semantics, so a
`--next` that does not name a direct child can still produce a node the checker
rejects. `TAS-098`'s worker stopped after its gate and before its release; the
coordinator reran `make test` and released the lapsed claim. The deferred
staged A/B in `TAS-080` and the work gated on it (`TAS-068`, `THO-010`) are
untouched.
