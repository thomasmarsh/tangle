---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Define and freeze the first gold corpus for memory-dependent engineering evaluation.
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

# Result

The evaluation foundation is complete. The benchmark claim contract, scenario
schema and grader, nine curated families, whole-corpus validator with
deterministic splits and digest, separability audit, isolated repeat pilot
harness, and the round-three corpus revision are resolved. The round-three
pilot completed 72/72 with verdict `revise` and, under its explicit revise
path, retains 11 cases (8 memory-required plus 3 controls) across all nine
families and all four curation groups, above the 8-case floor. Eight of the
nine memory-required cases separate and all three controls stay valid.

Residual: `resumption-after-decision-shared-install-001` failed the
separability pilot (repository-only correct 3/3) and is dropped from the
retained gate set. It remains in the gold corpus, and a later node must repair
or replace it before the confirmatory evaluation (TAS-128) freezes the corpus
with no non-separating memory-required case. Evidence and paired grades are in
`benchmark/memory-pilot-v2-round3-result.json`.
