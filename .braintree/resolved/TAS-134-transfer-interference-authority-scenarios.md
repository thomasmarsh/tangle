---
context_rev: 1
priority: P2
updated: 2026-09-13T15:38:43Z
summary: Curate transfer, interference, forgetting, and memory-authority cases.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-130-scenario-schema-grader]] at context_rev 1.

# Outcome

Ten to fifteen reviewed cases test reusable experience, negative transfer, distractor growth, reversible forgetting, and the rule that stored content cannot grant authority.

# Done when

- Cases cover a recurring workflow, recurring failure, cross-task gotcha, misleading prior lesson, old but authoritative decision, low-utility episode, direct injection, and laundered instruction.
- Each transfer case has a related but non-identical target task and a no-memory baseline.
- Interference cases parameterize irrelevant, superseded, and near-duplicate growth.
- Security gold actions distinguish factual use of memory from instruction following or permission expansion.
- Cases remain safe and require no real external side effects.

# Result

`benchmark/memory-corpus/experience-transfer.json`,
`benchmark/memory-corpus/forgetting-and-interference.json`, and
`benchmark/memory-corpus/poisoning-and-authority.json` freeze the last three
memory-evaluation families as `memory-scenario-v1` cases curated at revision
`f91f3be`. The gate on [[TAS-130-scenario-schema-grader]] was promoted to the
pinned `Depends on` edge at `context_rev 1` on execution (commit `ce8075a`).

- Twelve cases, four per family, balance two `development` and two `held-out`
cases each and cover every Done-when kind: recurring workflow, recurring
failure, cross-task gotcha, misleading prior lesson, low utility, irrelevant
growth, superseded growth, near-duplicate growth, old but authoritative
decision, direct injection, laundered instruction, and permission expansion.
- Every transfer case has a related-but-non-identical target task and an empty
repository-only no-memory baseline; every interference case instantiates one of
the three growth classes; the security cases separate factual use from
instruction following and permission expansion and grade only safe actions.
- `research/agent-memory-transfer-interference-authority-cases.md` is the prose
authority and records the constructed-episode convention, the case tables, and
the review record.
- Two independent fresh-context reviews (built-in `reviewer` and external Codex
CLI) plus a targeted re-check found an allocation leak, a fabricated
supersession, an ambiguous near-duplicate grader, unsupported incident
citations, and cross-split duplication; every finding was fixed before freeze.

Evidence: `tests/test_memory_transfer_corpus.py` (20 tests) enforces the
envelopes, schema conformance, kind coverage, transfer targets and no-memory
baselines, interference parameters, authority dispositions, the path and
content leak guards, split population, evidence-path existence, arm-neutral
tasks, and document agreement. `make test` passes (479 passed, 3 skipped, 79
deselected); the corpora make zero live model calls.

Residuals handed to [[TAS-135-corpus-validator-splits]]: the evaluation contract
defines observable information as repository contents at the frozen revision,
while these families use each case's `observable_paths` as the operative
boundary; the whole-corpus leakage audit must reconcile that and note that the
revision-and-conflict conflict norms cite a research authority plus the
still-proposed [[TAS-127-uncertainty-provenance-security]]. The audit also owns
the per-family memory-irrelevant control balance and any growth-size scaling.
