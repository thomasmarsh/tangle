# Memory-evaluation contract

This is the frozen contract for the Braintree memory-evaluation program. It
realizes Stage 0 of the staged plan in
[`research/agent-memory-theory-evaluation.md`](agent-memory-theory-evaluation.md)
and answers the claim question that theory assessment left open. The
machine-readable half is [`src/braintree/memory_contract.py`](../src/braintree/memory_contract.py);
that module is the single source of truth and this prose must not drift from it.

Protocol version: `memory-eval-contract-v1`.

The contract makes **zero live model calls**. It, the scenario schema, the gold
corpus, the validator, and the contract tests are offline artifacts; executing
any live or paid comparison needs the authorization described below.

## 1. The claim

> Selective Braintree memory improves the correctness of memory-dependent
> engineering actions at acceptable total interaction cost relative to
> repository-only, raw-history, and flat-memory baselines, and stays below an
> oracle that supplies the minimal gold memory.

The **primary target** is *memory-dependent downstream action quality* under a
total interaction budget. A case is only evidence when its action cannot be
recovered from currently observable information; a task answerable from the
current repository cannot support the claim, however well Braintree scores it.

## 2. Observable-information boundary and reconstructibility

**Currently observable** information is: repository contents at the frozen
source revision, the system prompt and tool definitions, the current
environment state, and tool output produced within the arm's budget.

The frozen source revision is the **outer envelope**: every path a case cites
must exist at that revision, and the scenario schema records the revision so
the boundary is reproducible. The **operative boundary** for a case is its
`query.observable_paths`, the subset of that revision the arm is given. A case's
deciding history is unobservable when it exists in the repository but outside
the paths the query exposes, which is how the curated families keep their cases
memory-required while still citing real files.

Supported memory is decision-relevant historical state. The scope is
prospective task state, semantic definitions and decisions, reflective thoughts
and feedback, procedural skill text, and compressed episodic results. Model
weights, inference-network architecture, and external entitlements no node owns
are out of scope.

A state belongs in memory when it fails at least one **reconstructibility
test**:

| Test | Question |
|---|---|
| unavailable | Is the historical state absent from every currently observable source? |
| unreliable | Would reacquisition yield a different or contradictory value? |
| ambiguous | Does current observable state fail to identify which prior decision or definition applies? |
| nondeterministic | Would re-deriving the state repeat a nondeterministic experiment or sampling step? |
| disproportionately-costly | Does reacquisition cost more than the expected value of retaining the state? |

This retains the broad admission threshold rather than an absolute
"never reconstructible" rule: *store decision-relevant historical state that is
unavailable, unreliable, ambiguous, or disproportionately costly to reacquire;
prefer a pointer or reproducible derivation when current authoritative material
is cheap and sufficient.*

## 3. Causal arms

Every arm shares identical fixtures, task prompts, tools, model settings,
budgets, and graders. Only the available persistent history differs.

| Arm | Available persistent history | Isolates |
|---|---|---|
| repository-only | current files, prompt, and tools; no episodic history | whether the case actually requires memory |
| raw-history | prior public action/observation transcripts within the same retrieval budget | whether selective consolidation beats recency and lexical search of full history |
| flat-memory | untyped timestamped notes with lexical retrieval and the same budget | whether graph lifecycle and governance beat mere persistence |
| braintree | the graph, lifecycle, revisions, and bounded retrieval commands | the system under test |
| oracle | only the minimal gold memory the case requires, injected directly | loss attributable to construction and retrieval rather than reading and reasoning |

The oracle is an **upper bound**, not a competitor. Repository-only is the
floor. A task prompt must never name an arm-specific answer.

## 4. Scenario families and curation groups

Each case carries exactly one family. Families are partitioned into four
curation groups so a corpus is stratified and balanced by family and outcome:

| Group | Families |
|---|---|
| admission | admission |
| resumption-and-implicit-retrieval | resumption, implicit-retrieval |
| revision-and-conflict | temporal-update, cascading-invalidation, conflict-and-uncertainty |
| transfer-interference-and-authority | experience-transfer, forgetting-and-interference, poisoning-and-authority |

The corpus must carry memory-irrelevant controls in more than one family, so a
system cannot score by always consulting memory. The revision-and-conflict and
transfer-interference-and-authority groups are deliberately all memory-required,
because every case there tests a memory-dependent action or a memory-hostile
outcome; the whole-corpus validator records the per-family control balance and
these reviewed exceptions.

## 5. Endpoints and the correctness gate

**Primary endpoint:** `action-correctness` — exact or partial correctness of the
required memory-dependent action, from the case grader.

**Secondary endpoints:** next-action-correct, avoidable-rework, repeated-failure,
decision-regret, negative-transfer, unnecessary-action.

**Diagnostic labels** attribute each failure to one bottleneck:
write-miss, organization-error, retrieval-miss, stale-or-conflicting-retrieval,
reader-failure, action-failure. Retrieval evidence and downstream use are
scored separately.

**Cost metrics** are reported alongside, never instead of, correctness. Tokens
use the existing token-benchmark vocabulary: input, cached_input,
uncached_input, output, reasoning_output, total. Interaction cost covers
tool_calls, shell_calls, model_turns, files_opened, nodes_opened, latency_ms,
and monetary_cost.

**Correctness-before-cost gate:** a sample enters cost summaries only after it
passes its case grader and telemetry validation. Correctness is decided before
cost; an incorrect cheap arm never wins.

## 6. Unit of analysis and statistics

The unit of analysis is one episode: a `(case, arm, model, repetition)` sample.
Arms are compared **paired** within a case and model. Report paired effects with
a 95% bootstrap confidence interval over at least 10,000 resamples.

Minimum power: at least **three models or model families** and at least **three
repetitions** per case and model, or the missing sample is reported. The Pareto
surface of correctness against cost is reported rather than one aggregate score.

## 7. Exploratory versus held-out and decision criteria

Corpus cases carry a deterministic, stratified split: `development` and
`held-out`. Development is where mechanisms are iterated. Held-out is frozen
before a confirmatory run and is the only split that can confirm a claim;
development and underpowered results are exploratory only.

A claim or mechanism is:

- **confirmed** when the primary endpoint improves on held-out cases against
  both repository-only and raw-history with a paired 95% confidence interval
  excluding zero, total interaction cost does not regress beyond the
  preregistered budget, and no integrity or safety endpoint regresses;
- **rejected** when there is no held-out improvement or the correctness-cost
  trade-off is dominated;
- **exploratory** when the evidence is development-split or underpowered;
- **untested** when no adequate cases or authorization exist.

## 8. Version pins

Every comparison freezes, and every sample names, all of: protocol,
corpus-digest, fixture-version, source-revision, model, model-revision,
reasoning-effort, prompt-revision, tool-revision, budget, allowed-commands, and
grader-version. A sample that cannot name every pin is not comparable.

## 9. Authorization and enforcement

Any live or paid model run requires explicit owner authorization recorded
**before** execution. The contract, schema, corpus, validator, and contract
tests are zero-live.

Contract tests in [`tests/test_memory_contract.py`](../tests/test_memory_contract.py)
protect the literal protocol: the protocol version, the five arm ids, the
reconstructibility categories, the token vocabulary's agreement with the
existing token benchmark, the family partition, the statistical thresholds, and
the document's agreement with the module. `braintree check` and `make test`
remain the gates.
