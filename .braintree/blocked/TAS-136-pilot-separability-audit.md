---
context_rev: 1
priority: P1
updated: 2026-09-13T16:04:02Z
summary: Audit whether repository-only and oracle conditions separate on a bounded pilot.
next: Obtain owner authorization for the bounded repository-only versus oracle pilot over the preregistered development subset.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-135-corpus-validator-splits]] at context_rev 1.

# Outcome

A bounded pilot verifies that memory-required cases cannot be solved reliably from current repository state while oracle evidence makes the intended action attainable, before the full five-arm experiment spends significant tokens.

# Done when

- A preregistered 8–12-case development subset spans all four scenario families. (Offline half done: 12 cases spanning all nine families and four curation groups.)
- Any paid or live model execution is separately authorized and records model, reasoning effort, tool version, prompt, fixture digest, and session telemetry.
- Repository-only and oracle results are paired and graded; memory-irrelevant controls remain solvable without oracle evidence.
- Cases that fail to separate are repaired or removed with reasons, without inspecting held-out outcomes.
- The phase-one corpus and contract receive a proceed, revise, or stop decision.

# Status

The offline half is preregistered. `memory_corpus.pilot_subset()` derives the
12-case development subset deterministically from the frozen corpus — one
memory-required case per family plus one observable-only control from each
control-bearing family — and `memory_corpus.pilot_problems()` fails the subset
if it leaves the 8–12 range or loses a family, a curation group, or its
required/control mix. `research/agent-memory-pilot-preregistration.md` is the
prose authority and fixes protocol `memory-pilot-v1`, the two arms
(`repository-only`, `oracle`), and the `proceed`/`revise`/`stop` decision rule;
`tests/test_memory_pilot.py` pins the document to the module. The subset is a
pure function of the corpus digest, so it cannot be steered after an outcome is
seen, and no held-out case is inspected.

The live half cannot run yet: no owner authorization for a live or paid run is
recorded in the vault or the contract, and the contract requires it before
execution.

# Blocked

Blocked by the missing owner authorization for the bounded two-arm separability
pilot. Unblocks when the owner records that authorization; then the pilot runs
`repository-only` and `oracle` over the 12 preregistered cases, grades each pair
with `memory_scenario.grade()`, repairs or removes any non-separating case with
a recorded reason, and resolves this node with the phase-one `proceed`,
`revise`, or `stop` decision.
