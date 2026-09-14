---
context_rev: 1
updated: 2026-09-14T13:38:59Z
summary: When do named outcomes justify decomposition before dispatch?
---

Parent [[TAS-189-usage-feedback-hardening-round-eleven]].

# Question

When a task already names several outcomes with separate acceptance evidence, should a coordinator decompose them before dispatch, even though execution has not yet revealed a new outcome and estimated duration is not a valid split trigger?

# Context

Tangle `FBK-032` finding 1 reports that one `# Done when` named four substantial outcomes and two dispatches each produced green partial work but exceeded a 30-minute worker window. Its proposed remedy is pre-dispatch children for the named deliverables.

The current contract deliberately resists that inference. `SKILL.md` says one node owns one durable outcome rather than an estimated session or amount of code, requires boundary reassessment when execution reveals new evidence, and says that a slice is a unit of execution rather than a split trigger or sizing ritual. The authoring reference permits up-front decomposition for a user-requested plan, but otherwise says to decompose just in time.

The unresolved distinction is whether several already named results with independent acceptance, verification, consumption, blocking, resumption, or rollback boundaries are themselves boundary evidence available before execution. Duration alone must remain irrelevant.

# Hypothesis

Pre-dispatch decomposition is justified when the authored acceptance contract already exposes multiple independently durable outcomes, because the evidence is semantic rather than predictive. Multiple hours, worker windows, file counts, or anticipated commits are not evidence. A coordinator may therefore split around the independent acceptance boundaries while preserving the original node as their coordinating parent, but must not manufacture children merely to fit a session.

# Test

- Reconcile the decision with the execution-evidence and slice-not-split-trigger language in `SKILL.md` and the just-in-time decomposition rule in the authoring reference.
- Define observable pre-dispatch evidence without time, token, model, agent, file-count, or commit-count estimates.
- State how the original `# Done when` survives as coordinator acceptance and how direct children receive independent completion evidence.
- Cover the negative case: several implementation steps contributing to one acceptance outcome remain one node and may be executed as slices.
- Add contract tests for any skill or reference wording changed.
- Record the decision and advance [[TAS-189-usage-feedback-hardening-round-eleven]] to its next child.
