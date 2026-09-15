# Memory-evaluation confirmatory report

This is the final report of the Tangle memory-evaluation program. It records
the held-out confirmatory run that decides the contract claim, separates the
supported claims from the rejected and untested ones, and records the resulting
contract decisions. The frozen protocol authority is
[`research/agent-memory-confirmatory-preregistration.md`](agent-memory-confirmatory-preregistration.md);
the claim, arms, and decision criteria belong to
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md).

## Verdict

**The contract claim is rejected on the frozen held-out split.** Tangle
memory improves correctness over the repository-only floor and is far cheaper
than the flat-memory and raw-history baselines, but it does **not** improve over
raw-history, which the contract's support criterion requires. No new memory
mechanism is admitted, and the existing Markdown and Git evidence contract
stands.

## The confirmatory run

- Protocol `memory-causal-confirmatory-v1`; split `held-out`; plan digest
  `sha256:4228b2b9f26e25d17726d6508832b123ffb3da5420727ea7da29eac9d5ecac39`;
  source revision `ee7c25d9bc28`; corpus digest
  `sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`.
- 24 held-out cases (19 memory-required, 5 controls) × 5 arms × 3 models × 3
  repetitions = **1,080 samples**. All 1,080 completed; zero missing or
  infrastructure-failed samples. Three models at reasoning effort `high`, no
  tools, one isolated turn per episode.
- Result artifact: [`benchmark/memory-causal-confirmatory-result.json`](../benchmark/memory-causal-confirmatory-result.json).
  All 40 failures are incorrect-action failures; none is a model-output or
  infrastructure failure. Execution used a launch-time throttle of five
  concurrent isolated children per batch (the frozen plan and digest are
  unchanged).

## Paired effects (95% bootstrap over `(case, model)` strata, 72 strata)

| Contrast | Mean effect | 95% CI | Decides claim |
|---|---|---|---|
| `tangle` − `repository-only` | **+0.093** | [0.037, 0.148] | yes — excludes zero |
| `tangle` − `raw-history` | **−0.023** | [−0.065, 0.000] | yes — includes zero → **reject** |
| `tangle` − `flat-memory` | −0.019 | [−0.056, 0.000] | diagnosis |
| `oracle` − `tangle` | +0.028 | [−0.009, 0.069] | diagnosis — tangle ≈ ceiling |

The support criterion requires the primary endpoint to improve over **both**
`repository-only` and `raw-history` with an interval excluding zero. The
raw-history interval includes zero, so the claim is rejected.

## Correctness-cost surface (correctness-gated)

| Arm | correct/admitted | total tokens | monetary cost |
|---|---|---|---|
| `repository-only` | 189 | 571,687 | $0.6323 |
| `raw-history` | 214 | 265,523 | $0.3310 |
| `flat-memory` | 213 | 182,119 | $0.2654 |
| `tangle` | 209 | 112,771 | $0.1668 |
| `oracle` | 215 | 114,962 | $0.1525 |

Tangle is the cheapest memory-bearing arm except the oracle and is
statistically indistinguishable from the oracle ceiling, but raw-history reaches
five more correct samples at roughly 2.4× the token cost. Neither dominates the
other; the contract decides on correctness first.

## What decided the rejection

The aggregate loss is one case. Across 24 held-out cases, tangle and
raw-history are identical on 23; the entire negative contrast comes from
`admission-update-existing-seam-reuse-001`, where tangle answered correctly
**1/3** models while raw-history answered **3/3** and repository-only **0/3**.
The raw transcript of the seam-reuse decision was lexically retrievable; the
tangle dependency-and-decision-chain retrieval did not reconstruct it. That
is a single held-out retrieval failure, not a broad graph-governance effect, but
the preregistered decision rule does not permit dropping it after the outcome is
seen.

`implicit-retrieval-blocker-lease-handoff-001` is the only oracle failure (one
repetition), so the ceiling itself is not perfectly attainable.

## Claim dispositions

- **Supported (development, exploratory):** Tangle beats repository-only on
  the development split (prior exploratory causal result, `tangle −
  repository-only` +0.333, CI [0.167, 0.463]).
- **Rejected (held-out, confirmatory):** the contract claim that Tangle beats
  both repository-only and raw-history; the raw-history contrast includes zero.
- **Exploratory:** all development-split results; they are never relabeled.
- **Untested / not adopted:** retrieval-policy ranking, episode consolidation
  and transfer, and interference and forgetting were retired before the freeze
  on zero retrieval-miss, organization-error, and stale-retrieval labels; the
  sparse-provenance and temporal fields remain untested and not adopted
  (`keep-existing-evidence`).

## Contract decisions and reversal criteria

- **No contract change.** The claim's own held-out criteria reject it, so the
  existing Markdown and Git evidence contract, the graph lifecycle, revision
  pins, and bounded retrieval stand unchanged. The contract literals in
  [`src/tangle/memory_contract.py`](../src/tangle/memory_contract.py) are
  untouched.
- **Reversal criterion.** Reopen the claim only with a fresh preregistered
  held-out run that (a) includes a second provider family or a materially larger
  held-out corpus, and (b) shows the `tangle − raw-history` interval
  excluding zero while no integrity endpoint regresses. The
  `admission-update-existing-seam-reuse-001` retrieval failure is the concrete
  defect a cause-directed repair would target.
- The confirmatory run is reproducible with the commands embedded in the result
  artifact and frozen in the preregistration.
