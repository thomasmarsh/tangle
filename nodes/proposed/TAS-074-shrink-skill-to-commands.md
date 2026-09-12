---
context_rev: 1
priority: P1
updated: 2026-09-12T15:10:30Z
summary: Replace the shell recipes in SKILL.md with the direct-answer verbs and measure the skill's token reduction.
next: Replace the Frontier and dependency backlink recipes with verb invocations once their verbs land.
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
