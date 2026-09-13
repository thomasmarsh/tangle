---
context_rev: 1
priority: P1
updated: 2026-09-13T14:55:24Z
summary: Validate, balance, split, and digest the gold memory-evaluation corpus.
next: Implement corpus validation and freeze deterministic development and held-out splits.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-131-admission-scenarios]] at context_rev 1.
Depends on [[TAS-132-resumption-retrieval-scenarios]] at context_rev 1.
Gated on [[TAS-133-revision-conflict-scenarios]].
Gated on [[TAS-134-transfer-interference-authority-scenarios]].

# Outcome

An offline validator proves the corpus is structurally valid, balanced enough for diagnosis, free of obvious answer leakage, reproducibly split, and content-addressed before experiments select mechanisms.

# Done when

- Validation covers schema, unique IDs, source revisions, paths, episode order, gold evidence, graders, family labels, and case counts.
- Development and held-out splits are deterministic, stratified by family and outcome, and prevent variants of one source incident from crossing splits.
- Leakage checks flag node IDs, gold phrases, or answers exposed outside the intended arm.
- The committed corpus carries a digest and verify mode that imports no optional model runtime.
- Tests include one valid corpus and focused failures for every invariant.
