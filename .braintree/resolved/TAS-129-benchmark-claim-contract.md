---
context_rev: 2
priority: P1
updated: 2026-09-13T15:50:18Z
summary: Specify the benchmark claim, memory boundary, causal arms, and decision criteria.
---

Parent [[TAS-121-evaluation-foundation]].

# Outcome

A concise benchmark contract defines exactly what Braintree claims to improve, what information counts as currently observable, and how correctness and total interaction cost decide the result.

# Done when

- The contract defines memory-dependent downstream action quality as the primary target.
- The reconstructibility test covers unavailable, unreliable, ambiguous, nondeterministic, and disproportionately costly reacquisition.
- Repository-only, raw-history, flat-memory, Braintree, and oracle arms have fixed meanings.
- Primary endpoints, pipeline diagnostics, cost metrics, unit of analysis, statistical comparisons, and correctness-before-cost gates are specified.
- Exploratory and held-out decisions, version pins, and authorization requirements for live runs are explicit.
- Contract tests protect any literal protocol required by the harness.

# Result

`src/braintree/memory_contract.py` freezes the protocol as one dependency-free
module: protocol id `memory-eval-contract-v1`; the claim and the primary target
`action-correctness`; the observable-information boundary and the five
reconstructibility tests (`unavailable`, `unreliable`, `ambiguous`,
`nondeterministic`, `disproportionately-costly`) with the cost-sensitive
admission rule; the five fixed arms (`repository-only`, `raw-history`,
`flat-memory`, `braintree`, `oracle`); primary and secondary endpoints, six
diagnostic labels, and cost metrics whose token names reuse
`braintree.token_benchmark.FIELDS`; nine scenario families partitioned across
four curation groups; development/held-out splits with a three-model,
three-repetition, 10,000-resample 95% paired rule and a correctness-before-cost
gate; the version-pin list; and the live-run authorization requirement.
`contract()` emits the whole protocol as JSON and `verify()` returns its
structural inconsistencies.
`research/agent-memory-evaluation-contract.md` is the prose authority and
states the same literals.

Evidence: `tests/test_memory_contract.py` (12 tests) pins the protocol version
and primary target, the five arm ids and their order, the five
reconstructibility categories, endpoint/label uniqueness, the token
vocabulary's agreement with `token_benchmark.FIELDS`, the family partition, the
statistical thresholds, the authorization string, a deterministic
JSON-serializable `contract()`, an empty `verify()`, tamper detection for arm
drift and a family-partition gap, and the document's agreement with every arm,
family, diagnostic label, and protocol literal. Targeted `ruff format`,
`ruff check`, `mypy`, and `pytest tests/test_memory_contract.py` (12 passed)
pass; the contract and its tests make zero live model calls.
