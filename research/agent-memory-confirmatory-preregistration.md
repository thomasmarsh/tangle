# Confirmatory held-out preregistration (protocol `memory-causal-confirmatory-v1`)

This document freezes the confirmatory stage of the Braintree
memory-evaluation program. It is the prose authority for the confirmatory
run; the machine-readable half is
[`src/braintree/memory_causal.py`](../src/braintree/memory_causal.py) with
`split="held-out"`, and
[`tests/test_memory_confirmatory.py`](../tests/test_memory_confirmatory.py)
pins this document to it. The claim, observable-information boundary, causal
arms, endpoints, statistical rules, decision criteria, and version pins belong
to [`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md);
the corpus and its deterministic split belong to
[`research/agent-memory-corpus-validation.md`](agent-memory-corpus-validation.md);
the shared five-arm runner belongs to
[`research/agent-memory-causal-preregistration.md`](agent-memory-causal-preregistration.md).
This document must not restate those literal sets.

The exploratory runner plans only the `development` split. The confirmatory
runner plans only the frozen `held-out` split, which the exploratory program
never inspected for tuning. The confirmatory plan's protocol is
`memory-causal-confirmatory-v1`; the development plan keeps
`memory-causal-v1`, so the two plans cannot be confused.

## 1. Selected mechanisms

The confirmatory stage tests the contract's single causal claim, not a menu of
new mechanisms. The mechanisms admitted to the claim are exactly those that
survived the program's per-mechanism decisions, and the `braintree` arm
represents them:

- **Graph lifecycle and governance.** Typed nodes, authoritative status
  directories, revision-pinned dependencies, and bounded retrieval. The
  transfer, interference, and retrieval workstreams ran no new mechanism.
- **Existing Markdown and Git evidence for provenance and authority.** The
  uncertainty-and-authority workstream (`memory-authority-v1`) measured the
  injection surface and committed the verdict `keep-existing-evidence`: sparse
  provenance fields and temporal fields are **not** adopted, because their
  held-out correctness contribution was zero over the existing evidence.

The following candidate mechanisms are explicitly **not** under test, because
the round-six diagnostics retired them before the freeze:

- retrieval-policy ranking (retrieval-saturated development corpus, zero
  retrieval-miss labels);
- episode consolidation and procedural transfer (zero organization-error
  labels, no demonstrated defect);
- interference and forgetting suppression (zero stale-or-conflicting-retrieval
  labels).

A later run that isolates one of those defects reopens it as a new node; it is
not a confirmatory claim here.

## 2. The confirmatory case set

The case set is the whole frozen `held-out` split:
`memory_causal.held_out_cases(corpus)` returns every case whose `split` is
`held-out`, ordered by the contract's family order and then by case id. It is a
pure function of the corpus digest, so no case can be included or dropped after
an outcome is seen. On the committed corpus it is 24 cases spanning all nine
families and all four curation groups: 19 memory-required cases and 5
memory-irrelevant controls (4 in admission, 1 in implicit-retrieval).

The development separability pilot (`memory-pilot-v2`, round seven) confirmed
that the retained development cases separate repository-only from oracle. The
held-out split was never inspected by that pilot and is not inspected by any
offline command before the confirmatory run; the freeze itself reads only case
metadata (ids, family, split, control label) through the deterministic
selector.

## 3. Arms, models, repetitions, and budget

The run uses the contract's five canonical arms unchanged: `repository-only`
(floor), `raw-history`, `flat-memory`, `braintree` (system under test), and
`oracle` (ceiling). Every arm shares one task prompt, one set of embedded
observable-file bytes, no tools, one model list, one reasoning effort, one
statement memory budget, one repetition count, and the `memory_scenario.grade`
grader. Only the persistent history differs, so a graded action difference is
attributable to memory construction and retrieval.

The frozen model list is the same three text models the development runner
used: `deepseek/deepseek-flash`, `deepseek/deepseek-v4-flash`, and
`deepseek/deepseek-v4-pro`, each at reasoning effort `high`. They are one
provider family; the contract's three-model minimum is met by three distinct
models, and a second provider family remains a later requirement rather than
part of this claim. Each `(case, arm, model)` runs three paired repetitions.

The default confirmatory plan is therefore 24 cases × 5 arms × 3 models ×
3 repetitions = **1,080 episodes**, chunked into **18** deterministic batches
of at most 60 isolated children, below the host's 64-child per-run limit. The
episode order is case-first, then model, then arm, then repetition.

## 4. Correctness-before-cost and analysis

The runner applies the contract's correctness-before-cost gate: a sample enters
a cost summary only after it passes its case grader and its telemetry
validates, so an incorrect cheap arm never wins. It reports:

- per-arm and per-`(case, model)` graded outcomes;
- paired treatment-minus-baseline effects for `braintree` against
  `repository-only` and `raw-history` (the two decision contrasts), plus
  `braintree` against `flat-memory` and `oracle` against `braintree` for
  diagnosis;
- a 95% percentile bootstrap interval over the paired effects, with one mean
  effect per `(case, model)` stratum and at least 10,000 fixed-seed resamples;
- tokens, model turns, tool calls, files and nodes opened, latency, and
  monetary cost per arm, over admitted samples only;
- every failure, labeled infrastructure, model-output, or incorrect-action;
- the correctness-cost Pareto surface rather than one aggregate score.

A missing, infrastructure-failed, or provenance-invalid sample makes the run
`incomplete` and `untested`, and no verdict is reported. A malformed model
answer is a model failure: the sample is graded incorrect and labeled, and it
does not make the run incomplete.

## 5. Decision criteria and reversal criteria

A complete confirmatory run is:

- **confirmed** when both decision contrasts (`braintree` minus
  `repository-only` and `braintree` minus `raw-history`) have a paired 95%
  interval whose lower bound is strictly positive, total interaction cost does
  not regress beyond the preregistered budget, and no integrity or safety
  endpoint (orphan, stale-pin, invalidation, poisoning, authority escalation)
  regresses;
- **rejected** when either decision contrast's interval includes zero or turns
  negative, or when the correctness-cost trade-off is dominated;
- **untested** when the run is incomplete.

An incomplete or failed confirmatory run ships no contract change. If a
mechanism is rejected, the requested contract change is withdrawn and the
existing documented contract stands; the reversal is recorded in the owning
node with the commit that named the rejected direction and whether its change
was kept, reverted, or replaced. If a mechanism is confirmed, the accepted
change records its reversal criterion (the observable condition that would
overturn it) in the same commit. Development-split results from the earlier
workstreams stay `exploratory` and are never relabeled by this run.

## 6. Freeze and version pins

The freeze reads the committed corpus, the runner, the child profile, the
prompts, and the model list, and records every
`memory_contract.PIN_FIELDS` value: `protocol`, `corpus-digest`,
`fixture-version`, `source-revision`, `model`, `model-revision`,
`reasoning-effort`, `prompt-revision`, `tool-revision`, `budget`,
`allowed-commands`, and `grader-version`. A sample that cannot name every pin
is not comparable. The plan digest is a content address over the protocol, the
pins, and the episode identities, so a changed corpus, fixture, prompt, arm,
model, or repetition count changes it; the confirmatory plan digest and the
`memory-causal-confirmatory-v1` protocol are recorded in the owning node before
execution.

## 7. Authorization and reproduction

Live or paid execution requires the owner's authorization recorded before
execution. The evaluation program runs under the owner's standing authorization
of 2026-09-13 covering all paid runs in the program; the confirmatory node
records that grant and the exact digest-bound pins before launch.

> Live or paid model runs require explicit owner authorization recorded before execution; the contract, scenario schema, gold corpus, validator, and contract tests make zero live model calls.

The offline reproduction is:

```sh
uv run braintree benchmark causal plan --split held-out
uv run braintree benchmark causal dry-run --split held-out
uv run python scripts/memory_causal_run.py generate /tmp/memory-causal-confirmatory \
  --split held-out
# launch batch1.js through batch18.js with the subagent tool, one batch per call
uv run python scripts/memory_causal_run.py collect /tmp/memory-causal-confirmatory \
  --out benchmark/memory-causal-confirmatory-result.json
```

`plan --split held-out` renders the deterministic confirmatory plan and pins;
`dry-run --split held-out` builds and validates the plan, synthetically
aggregates a complete confirmatory result, and validates the result schema
without a model call; `collect` rebuilds every sample from retained async run
state and makes no model call. The result embeds its own exact reproduction
commands and plan digest.
