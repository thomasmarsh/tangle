---
context_rev: 1
priority: P1
updated: 2026-09-13T14:03:33Z
summary: Curate cold-resumption and implicit-retrieval cases with executable next actions.
next: Curate and justify 10–15 resumption and implicit-cue cases.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Gated on [[TAS-130-scenario-schema-grader]].

# Outcome

Ten to fifteen reviewed cases test whether a fresh agent can recover decision-changing memory from vague or paraphrased cues and take the correct next engineering action.

# Done when

- Cases cover interruption after a decision, partial implementation, blocker, failed experiment, and handoff.
- At least half use cues with low lexical overlap to the gold memory.
- Each case names minimal gold evidence, relevant distractors, an executable or deterministic outcome, and acceptable alternative actions.
- Memory-irrelevant controls can be solved from current repository state alone.
- Cases do not expose node IDs or gold vocabulary in the task prompt unless that is the behavior under test.
