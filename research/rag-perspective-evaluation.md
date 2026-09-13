# Braintree from a RAG perspective

## Executive conclusion

Braintree is not primarily a conventional GraphRAG system. Conventional
GraphRAG starts with unstructured documents, extracts an entity graph, clusters
that graph, and uses the result to answer questions. Braintree starts with a
small, human- and agent-authored graph whose nodes already have operational
meaning: tasks, definitions, decisions, hypotheses, feedback, status, a single
frontier route, typed dependencies, and semantic revision pins. Its more useful
category is **versioned execution-memory RAG** or **retrieval-augmented action**.

That distinction should drive the roadmap. Braintree's moat is not that it has
a graph or can run HDBSCAN. Its moat is that it governs what may be written,
keeps Markdown authoritative, distinguishes prospective and semantic memory,
and can mechanically reject stale context. The largest remaining opportunity is
the query layer between this strong store and the agent: select the right query
mode, retrieve a small current evidence closure, explain why each item was
selected, and expand only when the first packet is insufficient.

The recommended order is:

1. Evaluate the real `braintree` retrieval commands rather than injected memory.
2. Add one bounded, query-aware context surface over the existing exact verbs.
3. Fuse lexical, optional semantic, and typed-graph signals instead of choosing
   lexical *or* semantic retrieval.
4. Make retrieval currentness-aware, section-level, source-backed, and
   token-budgeted.
5. Complete transparent incremental indexing.
6. Add query-focused global synthesis only if real global questions justify it.

Do not make clustering authoritative, require embeddings, generate an automatic
entity graph, or persist broad model summaries as project truth.

## What Braintree already does unusually well

### Governed memory construction

Most RAG systems focus on chunking and retrieval after accepting the corpus as
given. Braintree also controls the write boundary. Its admission rule, durable
outcome boundary, node types, status lifecycle, canonical edges, and explicit
disposition prevent a raw transcript from silently becoming permanent memory.
This remains more important than adopting a more elaborate vector store.

### Typed and temporally checked relationships

`Parent`/`Area`, `Depends on`, `Superseded by`, and `next` do different jobs.
`context_rev` pins distinguish a relevant old fact from a relevant *current*
fact. Generic semantic similarity does not provide that guarantee. The exact
`impact`, `stale`, `frontier`, and `node` answers are therefore correctness
mechanisms, not merely retrieval conveniences.

### Progressive disclosure and deterministic fast paths

The routing index, concise node headers, bounded TOON output, `orient`, `digest`,
and direct-answer verbs are already a useful context hierarchy. Known-node,
frontier, blocker, impact, and stale-context questions should remain exact and
model-free. They should not be routed through embeddings or clustering.

### Honest semantic and clustering evidence

The frozen 118-document/76-probe evaluation is a valuable negative result.
Lexical retrieval beat embeddings for near duplicates (recall@5 0.9667 versus
0.7667), while embeddings helped paraphrases (0.4130 versus 0.3261). Overall,
embeddings did not beat the lexical baseline. HDBSCAN had route-agreement ARI
0.0307, left 65 of 118 nodes as noise, and produced no useful outlier signal at
the tested thresholds. Keeping this layer optional and advisory was the right
decision.

### Strong systems and behavioral-test discipline

The project now has deterministic graph validation, fixed retrieval fixtures,
token telemetry validation, corpus leakage checks, causal arms, held-out cases,
bootstrap intervals, authority-injection cases, and preserved raw run artifacts.
This is a stronger empirical base than most local agent-memory projects.

## Audit of the current RAG surface

The current commands cover several retrieval modes, but the agent must compose
them manually:

| Need | Current surface | Assessment |
|---|---|---|
| Cold orientation | `orient`, `frontier`, `next` | Strong, bounded, deterministic |
| Known node | `node`, direct file read | Strong metadata and graph view; body evidence still needs another read |
| Change propagation | `impact`, `stale` | Strong and unusually precise |
| Topical lookup | FTS `search` | Useful BM25 baseline, but not a complete context builder |
| Duplicate/admission lookup | `similar` | Useful lexical baseline; optional embeddings replace rather than complement it |
| Area overview | `digest` | Useful for unresolved direct members; no deep or historical synthesis |
| Latent grouping | `clusters` | Correctly advisory; downstream value is unproven |

Important implementation-level gaps follow.

1. `search` indexes `summary` and body, while `similar` compares `summary` plus
   the whole body. The filename slug and frontmatter `next` are absent from
   both relevance representations. Yet `next` is often the most action-relevant
   text in a task node.
2. Whole-node embeddings and lexical vectors dilute short decisive sections
   such as `# Decision`, `# Invariant`, `# Result`, or one evidence statement.
3. When the semantic provider is present, `similar` returns the semantic rank
   alone. It does not preserve lexical winners or combine the complementary
   signals demonstrated by the project's own measurements.
4. Topical results do not explain the graph path or selection reason and do not
   return a cited evidence span. An agent must open candidates and reconstruct
   the justification itself.
5. Retrieval does not default to a current view. Superseded, deprecated,
   abandoned, unresolved, stale, and current nodes may all be relevant text, but
   they should not carry the same action weight.
6. Bounds are row counts rather than context-token or byte budgets. Ten short
   summaries and ten long summaries have very different inference costs.
7. There is no query-time sufficiency check. A low-confidence lexical hit and a
   complete dependency/decision closure both simply return a list.
8. There is no single local-to-global query surface. `orient`, `node`, `impact`,
   `search`, `similar`, and `digest` are good primitives, but using the right
   combination remains client policy.
9. Some indexed commands rebuild all node and edge rows before answering. The
   proposed transparent incremental index work is therefore directly aligned
   with RAG latency and zero-ceremony use.

## Confirmatory evaluation: what it establishes and what it does not

### Supported conclusions

The held-out program is substantial: 24 cases, five arms, three models, three
repetitions, and 1,080 completed samples. Braintree beat repository-only by
0.093 with a 95% interval of [0.037, 0.148]. It was the cheapest non-oracle
memory arm in the correctness-gated totals: 209 correct samples and 112,771
tokens, compared with raw history's 214 and 265,523. This supports two useful
claims:

- decision-relevant persistent memory improves action correctness over current
  observable files alone on these cases;
- a selective memory packet can be much smaller than raw episodic history while
  remaining near the oracle result.

The preregistered broad claim was correctly marked rejected because the
`braintree - raw-history` interval included zero. The procedural discipline
should be retained.

### The evaluation does not test the actual retriever

The `braintree` arm does not run `search`, `similar`, `node`, `impact`, or any
other graph command. The run is explicitly no-tools. In the harness,
`arm_memory(..., "braintree")` selects the source episodes named by the gold
evidence and injects their statements directly. This is a gold-informed memory
packing condition, not a measurement of whether Braintree can retrieve those
sources from a vault.

Consequently, the result can evaluate how a model acts after receiving a
selective packet, but it cannot estimate retrieval recall, typed graph-expansion
quality, command round trips, files opened, or end-to-end context assembly cost.
The near-oracle score is encouraging for selective packing, but it should not be
described as near-oracle RAG retrieval.

### The decisive case is not evidence of a retrieval miss

The report attributes the whole raw-history contrast to
`admission-update-existing-seam-reuse-001`. Inspection of the committed harness
and preserved raw artifacts shows:

- the case has two episodes;
- both `raw-history` and `braintree` receive the same two statements, in the
  same order;
- both arms have the same recorded prompt digest;
- for the v4-flash and v4-pro runs, the effective user-message bytes are also
  identical across the two arms;
- the raw reasoning shows models choosing different actions because they
  interpret “unrelated seam” differently, not because evidence is absent;
- six of the 24 held-out cases have byte-identical raw-history and Braintree
  memory, including every held-out admission case.

The preregistered aggregate rejection still stands, but the claim that this is a
concrete Braintree retrieval defect is unsupported. It is stochastic reader
variance under identical inputs. It should not, by itself, trigger a retrieval
mechanism.

A read-only check against the current real command strengthens that caution:

```text
braintree similar 'Decide how to record a reuse question raised on a new seam.'
  -> TAS-118 at rank 1, lexical score 0.3389
```

This is not a replacement benchmark, but it shows that the real lexical surface
finds the intended owner for the exact failed-case wording.

### The effective prompt pin is incomplete for some preserved runs

For the older `deepseek-flash` runs, the runtime appended an output-artifact
instruction whose path contained the arm and repetition. The committed
`prompt_digest` covers the benchmark system prompt plus rendered task, but not
this runtime-added wrapper. The only raw-history/Braintree byte difference in a
checked pair was that output path, but the important methodological point is
broader: the digest did not identify the complete effective model input.

Future recordings should hash the actual user and system messages observed by
the child runtime after every wrapper has been applied. If an arm label must
appear in an artifact path, keep that path out of model-visible text or replace
it with an opaque run identifier.

### Other limits on interpretation

- Three closely related DeepSeek models are useful model variants, but not three
  provider families. A second provider family remains necessary for a broad
  product claim.
- The retrieval budget exceeds the largest development case, which explains the
  earlier zero retrieval-miss diagnosis. Retrieval cannot be compared until
  cases contain more plausible memories than fit in the packet.
- Correctness-gated aggregate token totals are useful, but should also be
  reported per accepted sample and on matched case/model strata. Total tokens
  across arms with different numbers of correct samples are not a standalone
  efficiency comparison.
- Identity-equivalent arm inputs should be collapsed into one condition or
  treated as an explicit stochastic-equivalence check; outcome differences
  between identical prompts are not representation effects.

## Recommended directions

### P0 — Benchmark the real retrieval and context-assembly path

This is the highest-value next research deliverable. Build a held-out benchmark
in which the Braintree arm starts from an actual Markdown vault and may call the
real CLI under a fixed tool, token, and latency budget. Compare at least:

- repository plus ordinary `rg`/file reads;
- raw history with a realistic retrieval budget;
- current Braintree exact/lexical commands;
- candidate hybrid or graph-expansion policies;
- an oracle evidence packet.

Cases must have more distractors than fit in the retrieval budget, and must
separate local, global, and action-oriented query types. Include exact IDs,
paraphrases, semantic disconnect, stale distractors, superseded decisions,
multi-hop dependencies, duplicate admission, and controls that require no
memory. Score these stages separately:

1. seed recall;
2. evidence-closure recall and precision;
3. currentness/conflict correctness;
4. downstream action correctness;
5. tokens, files, nodes, calls, and latency.

Every answer should expose a machine-readable retrieval trace, so failures can
be attributed without inspecting private reasoning. Preserve the complete
effective prompt hash, retrieved node/version hashes, command outputs, and final
action. Freeze evaluation cases before tuning a mechanism.

### P1 — Add one query-aware, bounded context command

Introduce a read-only surface conceptually like:

```text
braintree context QUERY [--mode resume|local|impact|admit|global]
                        [--budget N] [--depth N] [--history]
```

The exact name is secondary. Its job is to compose existing primitives, not to
replace them. A packet should contain:

- selected node ID, type, status, `context_rev`, and path;
- the decisive section or short evidence span, not the whole node by default;
- why it was selected: exact match, lexical rank, semantic rank, frontier route,
  dependency, backlink, parent, supersession, or recency;
- the typed path from seed to evidence;
- currentness warnings, competing nodes, stale pins, and unresolved hypotheses;
- packet budget, omitted count, and whether the sufficiency rules passed.

The initial mode can be explicit rather than inferred. This keeps behavior
deterministic and easy to test while still providing a single low-round-trip
answer. Later, a cheap router may choose among modes if a benchmark demonstrates
value. GraphRAG's separate basic, local, global, and DRIFT modes and Adaptive
RAG's query-complexity routing both support the principle that one retrieval
policy should not handle every query.

### P1 — Fuse lexical, semantic, and typed-graph candidates

The project's evidence says lexical and embedding retrieval fail on different
probe families. The next experiment should therefore test a union, not another
winner-take-all model:

1. retrieve lexical/BM25 candidates;
2. optionally retrieve semantic candidates;
3. combine them with reciprocal-rank fusion or another score-scale-independent
   method;
4. apply typed graph and currentness priors;
5. expand only the top seeds under the packet budget.

The lexical list must remain present when the semantic capability is enabled.
Semantic retrieval should add paraphrase candidates, never erase a strong
near-duplicate candidate. Structural boosts should be query-mode specific:
`Depends on` and `Superseded by` matter for decisions and impact; `Parent` and
`Area` matter for ownership and resumption; backlinks matter for consolidation
and duplicate admission. A bounded weighted BFS is simpler and more auditable
than Personalized PageRank initially. PPR, inspired by HippoRAG 2, can compete
later if held-out multi-hop cases justify it.

### P1 — Make topical retrieval currentness-aware

Add a default current-action view while preserving an explicit history view.
At query time:

- follow `Superseded by` to the replacement;
- demote or exclude `abandoned`, `deprecated`, and superseded nodes from the
  current packet while retaining an explanation that they matched;
- distinguish unresolved `THO` hypotheses from settled `DEF`/`DEC` knowledge;
- flag stale consumers and unresolved dependency targets;
- retain contrary evidence when the graph does not settle a conflict;
- never treat retrieved memory as authorization.

This extends the value of `context_rev` beyond explicit impact queries without
adding mandatory schema fields. Optional event time, validity intervals, or
origin fields should still wait for cases that demonstrate a decision error.

### P1 — Index and retrieve decisive sections

Create derived section records keyed by node content hash. Give separate fields
or weights to:

- node ID and filename slug;
- `summary`;
- `next`;
- primary route and named dependencies;
- `# Decision`, `# Invariant`, and `# Conclusion`;
- `# Result`/`# Resolution` and evidence pointers;
- remaining body text.

This should improve both relevance and token efficiency. A result can return a
heading plus line-bounded excerpt and path, letting the agent verify the source
without opening several full files. Generated summaries are unnecessary for
this step because the Markdown already contains authored semantic sections.

### P1 — Use budgeted iterative expansion and a sufficiency gate

Replace fixed row limits in composed retrieval with a byte or token budget.
Start with a small packet, then expand only when deterministic checks find a
missing closure:

- no current owner or frontier route was found;
- a matched node is superseded but its replacement is absent;
- a selected consumer has a missing, unresolved, or stale dependency;
- a decision query has no settled decision/definition;
- conflicting current candidates remain;
- the packet contains only weak topical matches.

Expansion can add one graph hop, the next rank band, or optional semantic seeds.
It should stop when the closure is sufficient, the budget is exhausted, or the
system must report uncertainty. This takes the useful part of DRIFT-style
iterative search without requiring an LLM loop for every command. LazyGraphRAG's
minimal up-front indexing and query-time work similarly fit Braintree better
than eager model-generated community summaries.

### P1 — Complete transparent incremental indexing

The existing proposed work to maintain the derived index automatically and
incrementally is the right systems direction. Rebuilding remains a repair
operation; routine commands should update only changed content hashes and edge
rows. This reduces latency, removes a client-visible storage concept, and makes
the richer section index feasible without weakening Markdown authority.

The incremental contract should include deletion/status-move detection,
transactional replacement of one node's sections and edges, index-schema
versioning, and an offline equality test proving that incremental state equals a
clean rebuild.

### P2 — Add query-focused global synthesis over explicit routes

Microsoft GraphRAG's community reports help with corpus-global questions that
top-k retrieval cannot answer. Braintree has not established demand for this
class yet, and its explicit hubs are a better starting hierarchy than HDBSCAN.

First extend deterministic digest behavior: support depth, resolved/current/all
views, token budgets, and counts grouped by node type/status. If users need
questions such as “what recurring failure modes span this project?”, add
query-focused synthesis over selected hub branches. Generate it on demand,
retain source node IDs and excerpts, and cache it by the complete input-hash set.
It must remain derived and invalidated automatically; it must never become a
second authority.

If clustering is evaluated again, judge it on downstream cross-cutting/global
queries or duplicate discovery. Agreement with ownership routes is not a
complete gold standard because semantic themes may legitimately cross areas.
The current noise and outlier results still argue against investing in HDBSCAN
before such queries exist.

### P2 — Add a read-only admission advisor

`similar --file` is already an admission aid. A later `admit --dry-run` or
`context --mode admit` could return:

- likely existing owners;
- exact matching result/decision sections;
- parent/area and supersession paths;
- candidates for update-existing, retain-new, or discard;
- a reason and uncertainty, never an automatic mutation.

This targets a real, high-value decision—duplicate versus update—while keeping
semantic output advisory. It should be built on the same hybrid/context packet
and evaluated on the existing admission corpus plus larger realistic vaults.

### P3 — Reopen advanced memory mechanisms only on demonstrated failures

The abandoned consolidation, forgetting, and provenance-field workstreams were
correctly retired under their evidence contract. Reopen them only when the real
retrieval benchmark produces the corresponding failure:

- organization errors justify episode/consolidation work;
- stale or conflicting retrieval under vault growth justifies suppression;
- provenance-caused action errors justify sparse origin fields;
- time-dependent errors justify `observed_at` or validity intervals;
- repeated cross-project failures justify procedural promotion.

This also applies to graph propagation algorithms, learned rerankers, query
classifiers, and model-generated summaries. Each must beat the deterministic
baseline on held-out action quality after cost and integrity are included.

## A concrete retrieval design to test

The following small pipeline fits the current architecture:

```text
query
  -> explicit mode (or later: cheap query router)
  -> exact seeds: IDs, frontier/owner routes, FTS/BM25
  -> optional semantic candidate union
  -> reciprocal-rank fusion
  -> typed, budgeted graph expansion
  -> currentness/conflict normalization
  -> section-level evidence packing
  -> deterministic sufficiency check
  -> return packet, trace, and uncertainty
```

Suggested edge priorities by mode:

| Mode | Highest-value traversal |
|---|---|
| `resume` | coordinator `next`, child, parent/area, live dependencies, blockers |
| `local` | exact/topical seed, definitions/decisions it depends on, supersession replacement |
| `impact` | reverse context edges, current pins, affected unresolved consumers |
| `admit` | lexical/semantic near duplicates, same route, supersession, prior results |
| `global` | hub branches, bounded type/status aggregates, then selected evidence sections |

The response should be compact and auditable rather than prose-heavy. For
example:

```text
context{mode,budget_used,sufficient,truncated}: admit,612,true,false
evidence[2]{id,status,section,path,reason,current}:
  TAS-118,resolved,Result,.braintree/resolved/TAS-118-...,lexical-rank-1,true
  TAS-117,resolved,Result,.braintree/resolved/TAS-117-...,backlink-of-TAS-118,true
paths[1]{from,edge,to}: TAS-117,Parent,TAS-111
warnings: 0
```

The model still decides what to do. The command provides a bounded, cited,
fresh evidence closure.

## Directions not recommended now

- **Do not turn HDBSCAN communities into graph authority.** The measured route
  recovery and outlier behavior do not support it.
- **Do not let embeddings replace lexical retrieval.** The signals are
  complementary, and lexical retrieval is substantially better for exact and
  near-duplicate admission.
- **Do not auto-extract a second entity graph from Braintree nodes.** The source
  graph is already curated and typed; extraction would add lossy duplicate
  structure and provenance problems.
- **Do not eagerly summarize every cluster or hub with a model.** Prefer authored
  sections and query-time synthesis cached by hashes.
- **Do not add mandatory confidence, authority, temporal, utility, or decay
  fields without a demonstrated action error.** Sparse prose plus Git and
  existing lifecycle semantics remain the better default.
- **Do not optimize only retrieval recall or token totals.** The product target
  remains correct downstream action under total cost and integrity constraints.
- **Do not broaden to general document RAG yet.** Repository code and current
  documentation are usually directly observable; Braintree should remain the
  selective historical/decision layer unless a separate corpus use case is
  proven.

## Product positioning

The most defensible description is:

> Braintree is a Markdown-canonical, versioned execution-memory graph that
> retrieves a bounded, current evidence closure for agent action.

This is more specific than “GraphRAG” and highlights the features ordinary RAG
lacks: admission governance, workflow state, semantic revision pins, exact
impact, explicit supersession, and reversible human authority. GraphRAG methods
should be treated as a source of query-layer techniques—mode routing, local and
global traversal, iterative expansion, graph propagation, and provenance—not as
a target architecture to copy wholesale.

## Recommended staged program

1. **Retrieval observability:** add benchmark-only traces and hash the complete
   effective prompts; audit identity-equivalent arms.
2. **Real baseline:** run current CLI versus repository search, raw history, and
   oracle on larger-than-budget held-out vault cases.
3. **Small candidate:** test section indexing plus lexical/semantic reciprocal
   rank fusion; no graph propagation yet.
4. **Context closure:** test typed one-hop expansion, currentness normalization,
   and deterministic sufficiency under a token budget.
5. **One-call surface:** expose the winning composition as a bounded `context`
   command and measure round trips and downstream action.
6. **Scale:** complete transparent incremental indexing and repeat at 1k and 10k
   nodes with superseded and near-duplicate distractors.
7. **Only then:** evaluate PPR, query-focused global synthesis, admission advice,
   consolidation, forgetting, or new provenance/temporal fields one at a time.

## External research consulted

- Microsoft GraphRAG query engine: local, global, DRIFT, basic, and question
  generation modes: <https://microsoft.github.io/graphrag/query/overview/>
- Microsoft, “Introducing DRIFT Search”: iterative community-informed local
  search and bounded follow-up expansion:
  <https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/>
- Microsoft, “LazyGraphRAG”: minimal up-front indexing and query-time scaling:
  <https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/>
- Microsoft, “BenchmarkQED”: local/global query classes, fixed answer budgets,
  and multi-method evaluation:
  <https://www.microsoft.com/en-us/research/blog/benchmarkqed-automated-benchmarking-of-rag-systems/>
- Gutiérrez et al., “From RAG to Memory” (HippoRAG 2): deeper passage
  integration and Personalized PageRank for factual, sense-making, and
  associative retrieval: <https://arxiv.org/abs/2502.14802>
- Jeong et al., “Adaptive-RAG”: select retrieval depth from query complexity:
  <https://arxiv.org/abs/2403.14403>
- Ru et al., “RAGChecker”: diagnose retrieval and generation separately:
  <https://arxiv.org/abs/2408.08067>
- Microsoft, “VeriTrail”: trace generated claims through intermediate outputs to
  source evidence:
  <https://www.microsoft.com/en-us/research/blog/veritrail-detecting-hallucination-and-tracing-provenance-in-multi-step-ai-workflows/>

## Repository evidence consulted

- `research/agent-memory-theory-evaluation.md`
- `research/agent-memory-confirmatory-report.md`
- `research/agent-memory-pipeline-diagnostics.md`
- `research/agent-memory-evaluation-contract.md`
- `benchmark/memory-causal-confirmatory-result.json`
- preserved confirmatory-run artifacts under the recorded temporary paths
- `.braintree/resolved/THO-012-embedding-clustering-retrieval-theory.md`
- `.braintree/resolved/TAS-120-agent-memory-evaluation-program.md`
- `.braintree/resolved/TAS-124-action-weighted-retrieval.md`
- `.braintree/resolved/TAS-125-episode-consolidation-transfer.md`
- `.braintree/resolved/TAS-126-interference-forgetting.md`
- `.braintree/resolved/TAS-127-uncertainty-provenance-security.md`
- `.braintree/proposed/TAS-163-amortized-transparent-index.md`
- `src/braintree/index.py`
- `src/braintree/memory_causal.py`
- retrieval, semantic, clustering, memory-corpus, and benchmark tests

