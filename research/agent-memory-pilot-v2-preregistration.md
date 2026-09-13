# Isolated repeated separability-pilot preregistration (protocol v2)

This document preregisters the replacement separability pilot that gates the
evaluation foundation after the protocol-v1 run failed its information boundary.
It is the prose authority for the isolated harness. The machine-readable half is
[`src/braintree/memory_pilot.py`](../src/braintree/memory_pilot.py)
(:data:`PILOT_V2_PROTOCOL`, :func:`build_plan`, :func:`render_prompt`,
:func:`parse_action`, :func:`case_verdict`, :func:`record`), and
[`tests/test_memory_pilot_v2.py`](../tests/test_memory_pilot_v2.py) pins this
document to it. The evaluation contract and the corpus belong to
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md)
and [`research/agent-memory-corpus-validation.md`](agent-memory-corpus-validation.md).

Protocol: `memory-pilot-v2`. The pilot runs **only** on the `development` split;
the frozen `held-out` split is never inspected, so a pilot cannot tune toward a
confirming result.

## 1. Why protocol v1 did not decide the gate

The protocol-v1 re-run used the built-in Pi `delegate` child, whose
`inheritProjectContext: true` exposed `AGENTS.md` even though the task said to
use only the arm fixture; a retained transcript reasons from `AGENTS.md`. It also
pinned `deepseek/deepseek-v4-pro` instead of `deepseek/deepseek-v4-flash`, ran a
single repetition per `(case, arm)`, and retained neither repetition indexes nor
child run ids. Its `stop` verdict is historical evidence only.

## 2. Isolated child profile

Every episode runs as the project child profile
`.pi/agents/memory-pilot-child.md`:

- `systemPromptMode: replace`, so the child system prompt is exactly the
  committed text and never Pi's base prompt.
- `inheritProjectContext: false` and `inheritGlobalContext: false`, so no
  `AGENTS.md`, `CLAUDE.md`, or operator global context reaches the child.
- `inheritSkills: false` and `extensions:` empty, so no skill catalog and no
  ambient extension loads.
- `tools:` empty, so the child has no tool with which to read the repository.
- `model: deepseek/deepseek-v4-flash` with `thinking: high` and no
  `fallbackModels`, so no default and no fallback can substitute a different
  model.
- `defaultContext: fresh`, so no parent transcript is forked into the child.

The complete arm fixture is embedded in the prompt: the task, the full contents
of every observable path, the arm's memory (empty for `repository-only`, the
minimal gold evidence for `oracle`), and the allowed actions. Because the child
has no tools, the embedded fixture is the only information it can use.

## 3. Preregistered subset

The subset is the same pure function of the frozen corpus as protocol v1:
`memory_corpus.pilot_subset()` takes the first memory-required development case
and the first observable-only control of each family. Twelve cases are selected.

| Family | Case | Role |
|---|---|---|
| admission | `admission-retain-label-stability-hypothesis-001` | memory-required |
| admission | `admission-discard-cache-speculation-001` | control |
| resumption | `resumption-after-decision-shared-install-001` | memory-required |
| resumption | `resumption-control-vault-rename-001` | control |
| implicit-retrieval | `implicit-retrieval-after-decision-derived-membership-001` | memory-required |
| implicit-retrieval | `implicit-retrieval-control-version-declaration-001` | control |
| temporal-update | `temporal-update-cosmetic-edit-001` | memory-required |
| cascading-invalidation | `cascading-invalidation-independent-evidence-001` | memory-required |
| conflict-and-uncertainty | `conflict-and-uncertainty-competing-rules-001` | memory-required |
| experience-transfer | `experience-transfer-recurring-failure-001` | memory-required |
| forgetting-and-interference | `forgetting-and-interference-irrelevant-growth-001` | memory-required |
| poisoning-and-authority | `poisoning-and-authority-direct-injection-001` | memory-required |

`memory_corpus.pilot_problems()` still fails the subset if it leaves the 8–12
range, drops a family or curation group, or loses its required/control mix.

## 4. Arms, repetitions, and batching

Each case runs in the two contract arms `repository-only` (floor) and `oracle`
(ceiling), three paired repetitions each: 12 cases × 2 arms × 3 repetitions =
72 episodes. Every episode is a fresh isolated child.

The plan orders episodes case-first, then arm, then repetition, and chunks the
72 episodes into three deterministic 24-child batches. Each batch is therefore
four consecutive cases with both arms and all three repetitions, which keeps a
case's paired repetitions inside one batch. Twenty-four children stay below
pi-subagents' 64-child per-run limit.

## 5. Contract pins

A run freezes every `memory_contract.PIN_FIELDS` value: `protocol`,
`corpus-digest`, `fixture-version`, `source-revision`, `model`,
`model-revision`, `reasoning-effort`, `prompt-revision`, `tool-revision`,
`budget`, `allowed-commands`, and `grader-version`. The plan digest is a content
address over the pins and the 72 episode identities; the prompt digest for each
episode is a content address over the committed system prompt and the rendered
task, so the embedded observable bytes are pinned.

## 6. Grading and the paired majority

Every action is scored by `memory_scenario.grade()` against the
`action-correctness` endpoint. The correctness-before-cost gate admits a sample
to cost summaries only after it passes its case grader.

- A **memory-required case separates** when, in at least two of its three paired
  repetitions, `repository-only` is graded incorrect **and** `oracle` is graded
  correct.
- A **control is valid** when `repository-only` is graded correct in at least
  two of its three repetitions.

Malformed model output is a **model failure**: the sample is graded incorrect
and recorded with a parse error. It never makes the run incomplete.

## 7. Incomplete runs

A sample that is missing, or that fails provenance or telemetry validation
(child run id, raw output reference, pinned model, plan-matching prompt digest,
timezone-carrying timestamps, complete non-negative telemetry), is an
**infrastructure failure**. Any missing or infrastructure-failed sample makes
the run `incomplete` with `verdict: null`. Infrastructure failures are never
graded as model failures, and an incomplete run never decides the gate.

## 8. Decision rule

The preregistered phase-one verdict applies to the case-level results:

- **proceed** — every retained case meets its criterion.
- **revise** — one or two cases fail, but the retained subset keeps the 8-case
  floor and every curation group.
- **stop** — three or more memory-required cases fail to separate, or no repair
  can retain the floor and coverage.

## 9. Recording and retention

The result records every contract pin, repetition index, child run id, raw
output reference, raw output, grade, and token/cost telemetry, with `latency_ms`
computed from the retained `started_at` and `finished_at` timestamps rather than
trusted from the child. `result_problems()` validates the schema, and
`braintree benchmark pilot dry-run` builds the plan, validates the fixtures,
keys, and prompt digests, synthetically aggregates a complete run to `proceed`,
and validates the result schema without making a live model call.

## 10. Version pins and authorization

Live or paid execution is a **separate authorization**: the contract requires

> Live or paid model runs require explicit owner authorization recorded before execution; the contract, scenario schema, gold corpus, validator, and contract tests make zero live model calls.

Until the owner records authorization for the exact 72-sample pins and bound,
the live run is blocked and this harness stays zero-live.
