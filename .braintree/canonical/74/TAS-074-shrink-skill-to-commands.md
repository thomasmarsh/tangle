---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Replace the shell recipes in SKILL.md with the direct-answer verbs and measure the skill's token reduction.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

Depends on [[DEC-004-compact-skill-text]] at context_rev 1.

Every deterministic rule in `SKILL.md` is loaded in every session. Once the
verbs from the direct-answer children exist, the corresponding recipes and
hand-derivation prose are redundant and can be replaced with one command
reference each.

- Verbs from [[TAS-071-frontier-and-node-verbs]] and
  [[TAS-072-transitive-dependency-impact]].

# Outcome

`SKILL.md` names the direct-answer verbs instead of shell recipes, the contract
tests are updated coherently, and the skill text is measurably smaller under the
existing token A/B method.

# Done when

- The Frontier and dependency-impact recipes are replaced by verb references.
- `tests/test_skill.py` asserts the new command references and the removed
  recipes.
- A skill-text A/B records the token change.
- `make test` passes.

# Result

`SKILL.md` and `nodes/index-map.md` now name the direct-answer verbs instead of
carrying the frontier and dependency recipes. The read and execute loop runs
`braintree frontier`; the Common queries block lists `braintree frontier`,
`braintree node ID`, `braintree impact ID`, and `braintree orient`; and the
hand-derivation sentence that restated the frontier from `Parent`/`Area`
backlinks is removed. The pinned-dependents recipe is replaced by `braintree
impact ID`, which answers direct and transitive dependents in one call.
`nodes/index-map.md`'s Frontier query is `braintree frontier` and its
Changed-definition query is `braintree impact ID`, so the vault documents one
answer per question.

Skill-text A/B (method: byte, character, and word counts on `SKILL.md`, pre from
`git show HEAD:SKILL.md` and post from the working tree; this is a text-size
measurement, not a behavioral benchmark): pre 20,472 B / 20,468 chars / 3,014
words; post 20,246 B / 20,242 chars / 2,993 words; delta -226 B (-1.1%), -226
chars, -21 words. The live correctness-gated token A/B remains staged work owned
by [[TAS-078-round-trip-telemetry-and-gates]] and
[[TAS-080-staged-token-ab]].

Evidence: `tests/test_skill.py` asserts the new verb references and the removed
recipe strings, and ties the live frontier answer to the Markdown derivation;
`make test` passes.
