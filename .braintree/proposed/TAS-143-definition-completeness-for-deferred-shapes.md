---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Require a definition to cover, or name a successor for, every consumer-visible shape its consumers must author.
next: Require a definition to cover or name a successor for every consumer-visible shape its consumers must author.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-021` at `0.6.0+g3bacaf5`: a resolved `DEF` (metric definition v2)
deliberately deferred a batch-level aggregation slice shape to the implementing
task, so the implementing node invented two slice families, a
zero-versus-not-observed rule, and a per-slice metric-key spelling with no
versioned coverage; an additive output slice did not bump the definition version,
so a consumer could not tell an aggregation with the new slices from one without.
The authoring and dependency references give no definition-completeness rule for
a consumer-visible shape the consumers must author.

# Outcome

The authoring or dependency reference states that a `DEF` resolves only when
every consumer-visible shape its consumers must author is defined, or the
definition explicitly names the successor node that will define it, and names
the version or signal a consumer reads for an additive consumer-visible shape.

# Done when

- The rule is in `references/authoring.md` or `references/dependencies.md` and
  pinned by a contract test.
- The rule names the version or signal a consumer reads for an additive
  consumer-visible shape.
- A deferred shape is either disallowed at resolution or explicitly routed to a
  named successor.
- `make test` passes.
