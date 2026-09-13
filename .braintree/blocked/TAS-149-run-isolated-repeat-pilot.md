---
context_rev: 1
priority: P1
updated: 2026-09-13T17:04:44Z
summary: Run the isolated three-repetition Pi separability pilot and decide the gate.
next: Obtain explicit owner authorization for the bounded 72-sample live run after TAS-148 resolves.
---

Parent [[TAS-147-pilot-corpus-revision]].

# Context

Gated on [[TAS-148-isolated-repeat-pilot-harness]].

The live run uses the frozen development subset and corpus digest, two arms,
three paired repetitions, one fresh isolated Pi child per episode, and
`deepseek/deepseek-v4-flash` at `high` effort. It does not reuse the prior Pro
samples. Execute the three deterministic 24-child batches from one clean source
revision, stopping without a verdict if a required sample or contract pin is
missing.

# Outcome

A complete, provenance-preserving 72-episode result decides whether TAS-147 can
resolve and whether TAS-121 can advance under the preregistered case-level
majority and phase-one rules.

# Done when

- The owner authorizes the exact paid run pins and 72-sample bound before execution.
- All samples pass isolation and provenance validation and agree with `memory_scenario.grade`.
- The result records per-repetition grades and case-level majority classifications, then reports `proceed`, `revise`, or `stop` without post-outcome rule changes.
- TAS-147 records the decision and either resolves with TAS-121 advanced or keeps the failing path explicit.
- `braintree check`, `make test`, and `make test-benchmarks` pass.

# Blocked

Blocked by the missing owner authorization for the paid 72-sample live run and
by the unfinished isolated harness.

Unblocks when [[TAS-148-isolated-repeat-pilot-harness]] resolves and the owner
authorizes the exact recorded pins and sample bound.
