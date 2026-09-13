---
context_rev: 1
priority: P1
updated: 2026-09-13T14:03:33Z
summary: Define one scenario schema and deterministic grading interface for the gold corpus.
next: Design the versioned scenario record and grader contract.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Gated on [[TAS-129-benchmark-claim-contract]].

# Outcome

One versioned scenario format represents observable repository state, unavailable episodes, memory inserts, task cues, minimal gold evidence, acceptable actions, and deterministic or executable grading across all benchmark families.

# Done when

- The schema records case identity, family, source revision, observable paths, episode order, gold evidence, task, allowed actions, expected outcome, severity, grader, and split metadata.
- The format distinguishes information used to construct memory from information visible at query time.
- A minimal fixture demonstrates each causal arm without arm-specific answers in the task prompt.
- Parser and grader interface tests reject missing evidence, ambiguous outcomes, invalid paths, and unsupported schema versions.
