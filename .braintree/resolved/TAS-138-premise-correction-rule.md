---
context_rev: 1
priority: P2
updated: 2026-09-13T22:23:43Z
summary: State how a worker corrects a claimed node whose recorded premise is factually wrong, and who corrects the parent.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-016` at `0.6.0+g3bacaf5`: a claimed node's `# Outcome` asserted that
a time-of-impact query was not on the tick path, and validating it against the
code showed it was reached every tick. `SKILL.md` covers summary/next/status
edits, `context_rev` semantics, and escalation of a landed seam another node owns,
but states no rule for "the recorded premise I was handed contradicts the code",
and no rule for whether correcting a recorded premise is consumer-relevant.

# Outcome

`SKILL.md`'s read-and-execute loop states that a worker who finds a recorded
premise or `# Outcome` statement wrong records the corrected state with evidence
in `# Result`, bumps `context_rev` only when a pinned consumer relied on the
premise, and escalates only when the correction would change the declared scope,
outcome, or `Done when`; it also names who corrects the same wrong premise when
the parent repeats it.

# Done when

- The rule is in `SKILL.md` and pinned by `tests/test_skill.py` or an equivalent
  contract test.
- The rule distinguishes a factual premise correction from a scope change.
- Parent-premise correction ownership is explicit.
- `braintree check` and `make test` pass.

# Result

`SKILL.md`'s read-and-execute loop gains one paragraph after step 5: "A recorded
premise or `# Outcome` statement that the code contradicts is a factual
correction, not a scope change: record the corrected state and the evidence that
shows it in `# Result`, and bump `context_rev` only when a pinned consumer relied
on the premise. Escalate instead of correcting when the correction would change
the declared scope, outcome, or `Done when`. When the coordinating parent
repeats the same wrong premise, the worker that found it reports the correction
with evidence and the coordinator, which owns the shared parent, edits the
parent; the worker edits only the node it owns."

The rule separates the two cases the node asked for by consequence, not by
wording: contradicting code is a factual correction the finding worker makes
inside its own node, while a correction that would move the declared scope,
outcome, or `Done when` is a scope change the worker escalates instead. The
`context_rev` criterion is the existing consumer-relevance test applied to the
premise, so a correction that changes no pinned consumer's assumption is an
ordinary content mutation. Parent ownership follows the coordinator-owned shared
parent contract in `references/coordination.md` ("Shared parents, `index-map.md`,
definitions, and root hubs are coordinator-owned"): the worker reports the
repeated premise with evidence, and the coordinator makes the parent edit, so no
worker edits outside its write set.

Corrected premise recorded against the code: this node's `# Context` premise
held literally at `HEAD` (`9a9ae3d`).
`git grep -in premise HEAD -- SKILL.md references/ src/` matched no skill text —
only benchmark fixture ids in `tests/test_memory_revision_corpus.py` — so
neither a premise-correction rule nor a consumer-relevance statement existed,
which is the state the new paragraph corrects. The disposition of a
consumer-relevance bump was likewise unstated for a premise: the general
`context_rev` criterion named assumptions, decisions, invariants, and
interfaces, but no rule said whether correcting a recorded premise was
consumer-relevant, and the new paragraph states it is consumer-relevant exactly
when a pinned consumer relied on the premise.

`tests/test_skill.py` pins the paragraph with `_PREMISE_CORRECTION_RULE` (the
factual-correction-versus-scope-change distinction, the `# Result` evidence
record, the pinned-consumer `context_rev` criterion, the escalation boundary at
scope/outcome/`Done when`, and the worker-reports/coordinator-edits parent
ownership), asserted by the source-named `test_premise_correction_rule_is_stated`.
The falsification probe `_PREMISE_CORRECTION_PROBE_STEP_ONLY` feeds the
pre-change read-and-execute step 5 — which already names the evidence,
`context_rev`, and `updated` a worker writes while stating no premise rule —
through the same `_assert_contains` guard and requires `AssertionError` in
`test_premise_correction_guard_rejects_the_loop_step_alone`, so the test fails
when the guard stops detecting the rule rather than passing vacuously. The
widened rule reports all six clause groups missing against both the probe and
`HEAD:SKILL.md`, so neither the pre-change loop step nor the pre-change core
passes.

Evidence: `uv run pytest -q tests/test_skill.py` -> 73 passed; `braintree check`
-> `graph check: passed (196 nodes)`; `make test` -> 657 passed, 3 skipped, 79
deselected. `SKILL.md` grew 13,020 -> 13,624 bytes, inside the 16,000-byte
`test_core_stays_concise` bound. No node pins this node and it pins no
context-bearing dependency, so `context_rev` stays `1` and no consumer
reconciliation was needed. Parent [[TAS-137-usage-feedback-hardening-round-seven]]
named this node in the write set, so its `next` advanced to
[[TAS-139-resolved-child-completion-path]] in this change.
