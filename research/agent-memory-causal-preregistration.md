# Matched five-arm causal-runner preregistration (protocol v1)

This document preregisters the matched five-arm causal runner that realizes
Stage 2 of the staged plan in
[`research/agent-memory-theory-evaluation.md`](agent-memory-theory-evaluation.md).
It is the prose authority for the runner; the machine-readable half is
[`src/braintree/memory_causal.py`](../src/braintree/memory_causal.py), and
[`tests/test_memory_causal.py`](../tests/test_memory_causal.py) pins this
document to it. The claim, observable-information boundary, causal arms,
endpoints, statistical rules, and version pins belong to
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md);
the corpus and its deterministic split belong to
[`research/agent-memory-corpus-validation.md`](agent-memory-corpus-validation.md).
This document must not restate either literal set.

Protocol: `memory-causal-v1`. The preregistered plan runs **only** on the
`development` split; the frozen `held-out` split is never inspected by the
exploratory run, so it cannot tune toward a confirming result.

## 1. What the runner isolates

The contract's causal claim is that selective Braintree memory improves
memory-dependent engineering actions at acceptable total interaction cost
relative to repository-only, raw-history, and flat-memory baselines, and stays
below an oracle that supplies the minimal gold memory. The runner instantiates
that claim as one matched experiment: every arm receives the identical task
prompt, the identical embedded observable-file bytes, no tools, the same model
and reasoning effort, the same memory budget, the same repetition count, and
the same deterministic grader. Only the persistent history differs, so a graded
action difference is attributable to memory construction and retrieval.

## 2. The five arms

The arms are the contract's canonical ids. An arm's memory is a bounded,
deterministic function of the case's construction episodes, so the offline
runner makes no model call to build a fixture.

| Arm | Memory injected into the prompt | Isolates |
|---|---|---|
| `repository-only` | none | whether the case actually requires memory |
| `raw-history` | the task-ranked public episodes as transcript statements, bounded by the shared budget | recency and lexical search of full history |
| `flat-memory` | the same ranked episodes as untyped timestamped notes | whether typed lifecycle and governance beat mere persistence |
| `braintree` | the case's dependency and decision chain, resolved from the episodes the gold evidence cites | the system under test |
| `oracle` | the minimal distilled gold evidence, injected directly | reading and reasoning loss independent of construction and retrieval |

The shared memory budget is a statement count, not a token count, so every arm
is bounded identically and no arm can win by flooding the context. The
`repository-only` arm uses none of the budget. `braintree` retrieves the raw
deciding episodes through the dependency chain; `oracle` receives the distilled
gold evidence. The two are deliberately different: `braintree` exposes
construction and reading loss, while `oracle` is the upper bound the treatment
approaches.

The child profile is the isolated `.pi/agents/memory-pilot-child.md`: replaced
system prompt, fresh context, no project or global context, no skills, no
extensions, and `tools:` empty. Because the fixture is embedded and the child
has no tool, the injected arm memory is the only history it can use.

## 3. Preregistered case set

The case set is the same pure function of the frozen corpus that the pilot uses:
`memory_corpus.pilot_subset()` selects the lexicographically first
memory-required development case and the lexicographically first
observable-only control of each family. The set spans all nine families and all
four curation groups and pairs required cases with controls, so an
always-consult strategy is punished. It cannot be chosen or dropped after an
outcome is seen, and it stays on the development split.

The residual non-separating `resumption-after-decision-shared-install-001` case
was repaired before this preregistration: its task now states a locally
plausible packaging guide that points at a per-project copy, while the
unavailable history still records the shared install as deliberate. The repair
changed only the task text and re-froze the corpus digest; it still needs a paid
separability re-run to prove it separates, which this document records as a
gate rather than a completed result.

## 4. Models, repetitions, and batching

The runner preregisters three text models from the current registry:
`deepseek/deepseek-flash`, `deepseek/deepseek-v4-flash`, and
`deepseek/deepseek-v4-pro`, each at reasoning effort `high`. They are one
provider family; the contract's "three models or model families" minimum is met
by three distinct models, and a second provider family is a later-confirmation
requirement rather than a current claim.

Each `(case, arm, model)` runs three paired repetitions. The plan orders
episodes case-first, then model, then arm, then repetition, so three repetitions
of one case and arm stay together. The default plan is 12 cases × 5 arms × 3
models × 3 repetitions = 540 episodes, chunked into nine deterministic batches
of at most 60 children, below the host's 64-child per-run limit.

## 5. Correctness-before-cost gate

A sample enters a cost summary only after it passes its case grader and its
telemetry validates. Correctness is decided first; an incorrect cheap arm never
wins. The cost record for an arm therefore reports both the number of admitted
samples and the token and interaction totals over only those samples. Latency is
computed from the retained `started_at` and `finished_at` timestamps rather than
trusted from the child.

## 6. Endpoints and analysis

The primary endpoint is `action-correctness` from `memory_scenario.grade`.
Secondary endpoints and diagnostic labels are the contract's. The runner
reports:

- per-arm and per-`(case, model)` graded outcomes;
- paired treatment-minus-baseline effects for `braintree` against
  `repository-only` and `raw-history` (the two decision contrasts), plus
  `braintree` against `flat-memory` and `oracle` against `braintree` for
  diagnosis;
- a 95% percentile bootstrap confidence interval over the paired effects, with
  the bootstrap unit being one mean effect per `(case, model)` stratum so
  repetitions inside a case are not counted as independent evidence, and at
  least 10,000 resamples from a fixed seed so the interval is reproducible;
- tokens, model turns, tool calls, files and nodes opened, latency, and monetary
  cost per arm, over admitted samples only;
- every failure, labeled infrastructure, model-output, or incorrect-action.

The runner never reports one aggregate score in place of the correctness-cost
surface.

## 7. Exploratory and confirmatory labels

A development-split result is **exploratory**, however many repetitions it has.
A held-out result is **confirmatory** only when it completes with at least three
models and three repetitions and both decision-contrast intervals exclude zero;
otherwise the contract's `rejected` or `untested` verdict applies. An incomplete
run is `untested` and never decides anything. This runner's preregistered plan is
development-split, so its result is exploratory by construction.

## 8. Incomplete runs

A sample that is missing, or that fails provenance or telemetry validation, is
an **infrastructure failure**. Any missing or infrastructure-failed sample makes
the run `incomplete` and `untested`, with no analysis verdict. A malformed model
answer is a **model failure**: the sample is graded incorrect and recorded with
a parse error, and it never makes the run incomplete.

## 9. Version pins and reproduction

A run freezes every `memory_contract.PIN_FIELDS` value: `protocol`,
`corpus-digest`, `fixture-version`, `source-revision`, `model`,
`model-revision`, `reasoning-effort`, `prompt-revision`, `tool-revision`,
`budget`, `allowed-commands`, and `grader-version`. The model pin lists all
three models; each sample also names its own model. The plan digest is a content
address over the pins and the episode identities, so a changed corpus, fixture,
prompt, arm, model, or repetition count changes it.

The offline reproduction is:

```sh
uv run braintree benchmark causal plan
uv run braintree benchmark causal dry-run
uv run braintree benchmark causal record --input SAMPLES.json \
  --output benchmark/memory-causal-result.json
```

`plan` renders the deterministic plan and pins; `dry-run` builds and validates
the plan, synthetically aggregates a complete run, and validates the result
schema without a model call; `record` ingests retained child outputs and
telemetry. The result embeds its own exact reproduction commands and plan
digest.

The live fan-out is owned by `scripts/memory_causal_run.py`, which writes one
isolated child prompt per planned episode plus one workflow script per batch and
passes each episode's model as a per-child override, so one workflow spans the
three preregistered models:

```sh
uv run python scripts/memory_causal_run.py generate /tmp/memory-causal-v1
# launch batch1.js through batch9.js with the subagent tool, one batch per call
uv run python scripts/memory_causal_run.py collect /tmp/memory-causal-v1 \
  --out benchmark/memory-causal-result.json
```

The `collect` step rebuilds every sample from retained async run state and
makes no model call; a missing or failed sample leaves the run `incomplete` and
`untested`.

## 10. Authorization

Live or paid execution is a separate authorization. The contract requires

> Live or paid model runs require explicit owner authorization recorded before execution; the contract, scenario schema, gold corpus, validator, and contract tests make zero live model calls.

The owner authorizes the exact plan digest, corpus digest, source revision,
model list, repetition count, and sample bound **before** execution; the
authorization is recorded in the owning node's `# Authorization` section. Until
then the live five-arm run is blocked and this runner stays zero-live.
