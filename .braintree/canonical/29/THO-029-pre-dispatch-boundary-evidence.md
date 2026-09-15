---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Several authored acceptance outcomes are pre-dispatch boundary evidence; duration is not.
---

Parent [[TAS-189-usage-feedback-hardening-round-eleven]].

# Question

When a task already names several outcomes with separate acceptance evidence, should a coordinator decompose them before dispatch, even though execution has not yet revealed a new outcome and estimated duration is not a valid split trigger?

# Context

Hekate `FBK-032` finding 1 reports that one `# Done when` named four substantial outcomes and two dispatches each produced green partial work but exceeded a 30-minute worker window. Its proposed remedy is pre-dispatch children for the named deliverables.

The current contract deliberately resists that inference. `SKILL.md` says one node owns one durable outcome rather than an estimated session or amount of code, requires boundary reassessment when execution reveals new evidence, and says that a slice is a unit of execution rather than a split trigger or sizing ritual. The authoring reference permits up-front decomposition for a user-requested plan, but otherwise says to decompose just in time.

# Conclusion

Several already-named acceptance outcomes are pre-dispatch boundary evidence. The authored `# Done when` can expose a distinct independently resumable outcome per child — a separate acceptance, verification, consumption, blocking, resumption, or rollback boundary — before any execution, and that evidence is semantic rather than predictive. A coordinator may therefore create one direct child per outcome while keeping the original node as their coordinating parent; the parent's `# Done when` remains the coordinator's acceptance and its `next` routes to the first child.

Estimated duration, worker windows, token or model budgets, file counts, and anticipated commits are never evidence, so the decision does not turn session size back into node identity. The negative case is the ordinary slice: several implementation steps that together produce one acceptance outcome remain one node and may be advanced as slices. This reconciles the answer with the execution-evidence and slice-not-split-trigger language because the split trigger stays the independently acceptable outcome, not the estimated session.

# Result

`SKILL.md`'s durable-outcome boundary now admits evidence that arrives before dispatch when the authored `# Done when` already names outcomes with independent completion evidence, and `references/authoring.md` states the observable semantic test, the parent-acceptance shape, the never-evidence list, and the negative slice case. `tests/test_skill.py` pins the new rule and its falsification probe. `make test` passes.
