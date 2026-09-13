---
context_rev: 2
priority: P1
updated: 2026-09-13T16:19:23Z
summary: Audit whether repository-only and oracle conditions separate on a bounded pilot.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-135-corpus-validator-splits]] at context_rev 1.

# Outcome

A bounded pilot verifies that memory-required cases cannot be solved reliably from current repository state while oracle evidence makes the intended action attainable, before the full five-arm experiment spends significant tokens.

# Done when

- A preregistered 8–12-case development subset spans all four scenario families.
- Any paid or live model execution is separately authorized and records model, reasoning effort, tool version, prompt, fixture digest, and session telemetry.
- Repository-only and oracle results are paired and graded; memory-irrelevant controls remain solvable without oracle evidence.
- Cases that fail to separate are repaired or removed with reasons, without inspecting held-out outcomes.
- The phase-one corpus and contract receive a proceed, revise, or stop decision.

# Result

The owner authorized the bounded live pilot in session on 2026-09-13. The run
used one fresh-context subagent per `(case, arm)` sample (24 samples) under
`pi-subagents` 0.67.0, model `deepseek/deepseek-v4-pro` at reasoning effort
`high`, protocol `memory-pilot-v1`, corpus digest
`sha256:8caf44eae2a841e4ff4e2ad4f11ee85bfa87cbca048065539a94f18f65ed7d02`,
fixture digest `sha256:6ed4cec907b25a34cb3faa5689d2b0f565b8c80c166e3ea01fed4e9ca16f3a3c`,
grader `memory_scenario.grade`, one repetition per sample. Each child read only
its arm's fixture (task prompt, observable files, and — for oracle — the gold
evidence) and no other file; every sample used exactly one read tool call and no
repository exploration. Telemetry: 24/24 samples completed, 195,594 total
tokens, $0.373, one model and effort.

The paired grades are committed in
`benchmark/memory-pilot-result.json`. Nine memory-required cases ran:
**two separated** (`temporal-update-cosmetic-edit-001` and
`poisoning-and-authority-direct-injection-001` — repository-only wrong, oracle
right) and **seven did not**, because repository-only already produced the
expected or an acceptable action: admission label-stability, resumption
benchmark-opt-in, implicit-retrieval fast-gate, cascading-invalidation
independent-evidence, conflict-and-uncertainty competing-rules,
experience-transfer recurring-failure, and forgetting-and-interference
irrelevant-growth. The oracle was correct on every memory-required case, so the
failure is a repository-only floor that is too high, not an unreachable ceiling.
Of the three controls, two were solved repository-only;
`admission-discard-cache-speculation-001` returned `DISCARD` instead of the
exact allowed action and failed only the exact-match grader, not the decision.

**Decision: `stop`.** Under the preregistered rule, three or more
non-separating memory-required cases stop the current frozen corpus from
advancing to the five-arm experiment. The observed mechanism is a weak
distractor set: the task, observable files, and allowed actions make the
expected action inferable from general engineering knowledge, so the deciding
history is not required. No held-out case was inspected. The remediation is a
corpus redesign, owned by [[TAS-147-pilot-corpus-revision]].
