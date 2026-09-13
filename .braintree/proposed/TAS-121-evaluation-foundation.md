---
context_rev: 1
priority: P1
updated: 2026-09-13T14:55:24Z
summary: Define and freeze the first gold corpus for memory-dependent engineering evaluation.
next: "[[TAS-133-revision-conflict-scenarios]]"
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Outcome

A versioned 40–60-case gold corpus and evaluation contract isolate information unavailable from current repository state, define executable outcomes, and support matched memory ablations without leaking held-out answers.

# Done when

- The benchmark claim, observable-information boundary, causal arms, endpoints, and statistical decision rules are explicit.
- Every case conforms to one schema and names observable state, unavailable history, minimal gold memory, acceptable actions, and an executable or deterministic grader.
- Admission, resumption and implicit retrieval, revision and conflict, and transfer, interference, and authority families each contribute a balanced case set.
- A validator, deterministic development and held-out split, corpus digest, and bounded separability pilot pass.
- Every direct child is resolved or explicitly disposed.
