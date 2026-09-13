---
context_rev: 1
priority: P1
updated: 2026-09-13T16:08:58Z
summary: Audit whether repository-only and oracle conditions separate on a bounded pilot.
next: Run the authorized two-arm pilot over the preregistered subset and record the graded decision.
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

# Authorization

The owner explicitly authorized the bounded live pilot in session on
2026-09-13, before execution. Scope: the 12 preregistered development cases,
the two pilot arms (`repository-only`, `oracle`), one repetition per sample.
Pins for the run: protocol `memory-pilot-v1`; corpus digest
`sha256:8caf44eae2a841e4ff4e2ad4f11ee85bfa87cbca048065539a94f18f65ed7d02`;
grader `memory_scenario.grade`; model `deepseek/deepseek-v4-pro` at reasoning
effort `high`; harness `pi-subagents`. The run is delegated to one
fresh-context subagent per `(case, arm)` sample, each given only its arm's
fixture.
