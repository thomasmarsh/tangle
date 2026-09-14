---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State that a checked-in source-text guard is acceptable when paired with a falsification probe and names its tokens and modules.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Tangle `FBK-026` finding 5 at `0.6.0+g3bacaf5`: two gates needed to prove the
shared code gained no branch on a mode or scenario name, and the skill gives no
guidance for proving the absence of a pattern. Both leaves used `include_str!`
source-text guards, which are defeatable by string construction and need care to
avoid matching legitimate strings. `rg -in 'negative assertion|source-text|
falsification probe|absence' SKILL.md references/` matches nothing.

# Outcome

The authoring reference states that a checked-in source-text guard is an
acceptable negative assertion when paired with a falsification probe, and that it
names the exact tokens and the modules it covers.

# Done when

- The rule is in `references/authoring.md` and pinned by a contract test.
- The rule covers the falsification probe and the named tokens and modules.
- `make test` passes.

# Result

`references/authoring.md` gains a `## Negative assertions` section between the
decomposition and direct-answer sections. It states that the absence of a branch
on a named mode or scenario is proved with an observable check when the code
offers one, and that when it does not, "a checked-in source-text guard over the
module is an acceptable negative assertion when it is paired with a
falsification probe": a fixture source that carries the forbidden token and that
the guard must reject, so the test fails when the guard stops detecting rather
than when the forbidden token merely moves. The rule names the guard's
obligations — it "names the exact tokens it forbids and the modules it covers",
and "matches whole tokens rather than substrings, because source text is
defeatable by string construction and an over-broad pattern matches legitimate
strings". The reference preamble's load trigger now includes "proving the absence
of a branch with a negative assertion", so the rule is read at the act it covers.

`SKILL.md` is unchanged. The rule is conditional authoring detail for a
verification act, and the core already routes that workflow to
`references/authoring.md`; adding it to the core would only dilate contract text
that the `test_core_stays_concise` bound keeps narrow.

`tests/test_skill.py` pins the new literal with `_NEGATIVE_ASSERTION_RULE`
(guard form plus falsification probe, the fixture that must be rejected, the
guard-stops-detecting failure the probe catches, the named tokens and modules,
and whole-token matching), asserted by the source-named
`test_negative_assertion_names_its_probe_tokens_and_modules`.

Evidence: `uv run pytest -q tests/test_skill.py` -> 64 passed; `make test` ->
passed; `braintree check` -> graph check passed. No context-bearing dependency
was pinned to this node, so no consumer reconciliation was required and
`context_rev` stays at `1`.
