---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Require a definition to cover, or name a successor for, every consumer-visible shape its consumers must author.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Hekate `FBK-021` at `0.6.0+g3bacaf5`: a resolved `DEF` (metric definition v2)
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

# Result

`references/authoring.md`'s **Node body and status output** section now carries
the definition-completeness rule the `FBK-021` probe lacked: a `DEF` resolves
only when every consumer-visible shape its consumers must author is defined in
it, or the definition explicitly names the successor node that will define it,
so a shape deferred to an implementing task with no named successor is
disallowed at resolution; and an additive consumer-visible shape names the
definition version — or the other signal a consumer reads — that distinguishes a
consumer with the new shape from one without, because an unversioned additive
slice leaves a consumer unable to tell the two apart. The rule rides the
already-routed **authoring** topic on the surface an author reads before
resolving a `DEF`, so the batch-level aggregation slice shape the Hekate had to
invent is either defined, routed to a named successor, or rejected at
resolution, and the additive metric-key slice carries the version signal the
`FBK-021` consumer needed.

Tests: `tests/test_skill.py` adds
`test_definition_covers_each_consumer_visible_shape_or_names_a_successor`, which
pins `_DEFINITION_COMPLETENESS_RULE` — five literal strings spanning the
coverage, named-successor, deferred-shape, and additive-version clauses —
against `references/authoring.md`, plus
`test_completeness_guard_rejects_the_settled_definition_sentence_alone`, whose
probe `_DEFINITION_COMPLETENESS_DEFERRAL_ONLY` is the pre-change sentence: it
stages the settled/unsettled `DEF` resolution but carries none of the rule
strings, so the guard fails when it stops detecting the rule rather than when
the reference merely reflows.

`SKILL.md` is unchanged: the rule rides the already-routed **authoring** topic,
so the core stays inside its size bound.

`tangle check` passes (196 nodes) and `make test` passes.
