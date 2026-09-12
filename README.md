# Braintree

Braintree is a Markdown-canonical operating model for agents doing long-running engineering work. It keeps decisions, definitions, tasks, blockers, and dependency state visible in an Obsidian-compatible vault while using an optional external SQLite sidecar for fast derived queries and same-host coordination.

## Purpose

The skill is intended to make repository-local planning competitive with external issue trackers while remaining understandable through ordinary files and shell commands. Its primary job is to answer execution questions quickly and reliably: what should happen next, what remains unfinished, what is blocked, what changed, and which work became stale after a dependency changed.

It is designed for projects that want durable agent memory without a database, service, daemon, generated index, or custom query tool. The graph remains inspectable and editable as Markdown, works with Git, and can be searched with tools such as `find`, `rg`, `awk`, and `sort`.

This is not a general-purpose note-taking system or a replacement for every collaborative workflow offered by hosted trackers. It is a deliberately narrow execution layer for work that benefits from atomic context, explicit relationships, and low-cost resumption.

## Model in brief

Each concern is stored as a small Markdown node. Directory placement is the authoritative workflow status, filenames provide stable identity and type, and wikilinks express relationships. Each relationship has one stored direction: `Parent` lives on the child, `Area` on its assigned node, context dependencies on the consumer, `Superseded by` on obsolete work, and `Indexes` on a deliberate route; inverse child, parent-of, indexed-by, and backlink views are searches. A compact `nodes/index-map.md` routes to durable `IDX` root hubs without duplicating every node. Every non-root node has one primary `Parent` or `Area` link, so unfinished work must reach a hub (or a deliberate Focus route) instead of becoming an orphan. Local semantic `context_rev` values and dependency pins make stale assumptions discoverable without a shared global ledger, without treating every edit as a consumer-visible change. Status is deliberately not stored in stationary node metadata or a symlink/index view: the directory is the one authoritative status representation.

Nodes are an execution-memory admission boundary, not a transcript. Retain durable knowledge and decisions, executable tasks, bugs, debt, blockers, and future features only when they could change a later decision or action or materially reduce future resumption cost. Independent resumability is necessary but insufficient for a new node. Agent, write-set, handoff, failed-check, routine-verification, incidental-cleanup, and mechanical-cleanup boundaries alone stay in the current node's `next`, result, evidence, or handoff; a fresh worker may continue that node. Exclude tool logs, routine narration or status, copied source material, and observations without foreseeable action value.

It is compatible with Codex, Claude Code, and pi because all consume the standard `SKILL.md` skill entrypoint. Codex additionally uses the optional `agents/openai.yaml` interface metadata.

## Hybrid local sidecar

Markdown is authoritative for prose, wikilinks, context revisions and dependency pins, status directories, priority, and next actions. The installed `braintree` command hides SQLite behind specialized commands. It rebuilds derived nodes, edges, backlinks, stale-pin checks, and FTS search from Markdown, while making local claims, expiring leases, and numeric ID allocation atomic.

```sh
braintree init
braintree index nodes
braintree search 'authentication' --limit 10
braintree allocate TAS
```

The sidecar is external and untracked, keyed by the Git common directory under `$XDG_STATE_HOME/braintree` or `~/.local/state/braintree`; all local worktrees share it. It is rebuildable: database loss loses only indexes and leases, recovered by `braintree init` and `braintree index`. SQLite WAL is limited to concurrent processes on one host and a local filesystem. Do not place it on a network or synchronization filesystem. Cross-host coordination needs a server database (for example PostgreSQL) behind the same command interface. Status directories remain Markdown-authoritative; a stationary-path migration is deferred pending evidence that status-renames still cause material churn.

## Install

Clone this repository, then select an explicit destination. The installers never write to `$HOME` implicitly.

```sh
# Project-scoped Codex skill
./scripts/install.sh --codex --project /path/to/project

# Recommended: project-scoped Claude Code skill
./scripts/install-claude.sh --project /path/to/project

# Project-scoped pi skill
./scripts/install.sh --pi --project /path/to/project

# User-scoped install only when deliberately naming the home root
./scripts/install-claude.sh --home "$HOME"
```

The generic installer retains the equivalent legacy Claude Code entry point:

```sh
./scripts/install.sh --claude --project /path/to/project
```

The installer places the skill where the selected coding agent discovers it and writes the single `braintree` command to `<root>/.local/bin/braintree`; a `--home` install therefore places it at `~/.local/bin/braintree`. Put `<root>/.local/bin` on `PATH` so consuming projects run bare `braintree`. Re-running an unchanged install reports a structured `no-op` result and exits successfully. Inspect a planned destination without writes:

```sh
./scripts/install.sh --codex --project /path/to/project --dry-run
```

Restart the relevant coding-agent session after installing so it discovers the skill. The skill’s own `description` controls automatic selection. To guarantee loading, invoke it as `$braintree` in Codex, `/braintree` in Claude Code, or `/skill:braintree` in pi.

## Verify

The offline test uses only temporary directories; it never creates or updates a live user installation.

```sh
make test
```

## Optional semantic extra

A plain install has no third-party runtime dependency and every command answers on the deterministic lexical baseline. Embedding inference for the optional semantic layer installs separately through the explicit `semantic` extra:

```sh
uv sync --extra semantic

# or, where the package is installed as a dependency
pip install 'braintree[semantic]'
```

The extra pins the off-the-shelf inference and clustering libraries that ship: `fastembed` on ONNX Runtime is the in-process inference runtime, with `numpy`, `scikit-learn`, `umap-learn` for UMAP reduction, and `hdbscan` for density clustering. `sentence-transformers` on CPU torch was an evaluation baseline only and is deliberately not shipped: above torch 2.2.2 it publishes no x86_64 macOS wheel, and torch 2.2.2 needs `numpy<2`, which contradicts fastembed's `numpy>=2.1`. No model is trained, fine-tuned, or shipped here; the extra only makes published models usable. Capability probing is a `find_spec` lookup that never imports or loads any of them, so `braintree check`, `braintree frontier`, `braintree orient`, `braintree search`, and every other interactive verb answer exactly as before while the extra is absent.

Model weights are read offline from a local cache, and nothing downloads at query time. Pre-fetch the weights once into the cache, then run offline:

```sh
BT_MODEL_CACHE=/path/to/model-cache braintree similar 'expired authentication grants'
```

`BT_MODEL_CACHE` names the cache directory explicitly. When it is unset, the Hugging Face cache convention applies: `HF_HOME` when set, otherwise `~/.cache/huggingface`, with weights under its `hub/` subdirectory. Point the cache at a directory that already holds the pre-fetched weights; nothing downloads during a query.

## Embedding model and runtime selection

The selected default is **`sentence-transformers/all-MiniLM-L6-v2`**, the fallback is **`BAAI/bge-small-en-v1.5`**, and the chosen in-process runtime is **`fastembed` on ONNX Runtime**, which is what the `semantic` extra installs. `sentence-transformers` on CPU torch was an evaluation baseline only and is not shipped. The choice is recorded with its measurements in `benchmark/embedding-evidence.json` and re-runnable from a fixed corpus.

The default and fallback both run through fastembed's ONNX copies and are offline-available from the documented cache: MiniLM at 0.33 MRR and 0.55 recall@5 against 0.34 and 0.58 for the lexical `braintree similar` baseline, with the best measured paraphrase recall@5 (0.41 against 0.33 lexical) at 19 ms per node and a 0.1 s model load instead of a 2.8 s torch import. No candidate beats the lexical baseline across the board, so the lexical baseline stays the correctness reference and the semantic layer adds paraphrase recall rather than replacing it.

The corpus is committed as `benchmark/embedding-corpus.json` plus `benchmark/embedding-documents.jsonl`. It freezes the vault at one revision and derives two probe families from the vault's own structure: paraphrase probes from canonical context edges (the dependent's summary asks for the dependency it names) and near-duplicate probes from resolved node pairs whose text is nearly identical. Positives are split deterministically into a `dev` and a `heldout` half, so the held-out metrics never reuse a screening positive. Every metric is computed over the whole document set, and the lexical `braintree similar` baseline is scored on the same probes as the reference.

Verify the committed corpus offline, or regenerate it after a deliberate vault snapshot:

```sh
braintree benchmark embedding corpus --verify
braintree benchmark embedding corpus
```

The comparison itself is an explicit batch that imports the extra, downloads weights into the documented cache, and writes the evidence file:

```sh
braintree benchmark embedding run
```

Bound it with `--models`, `--runtimes`, `--probes`, `--limit`, and `--time-budget`. No interactive verb loads a model, and `make test` never downloads one: the tests drive the same pipeline with an injected embedder that reproduces the lexical baseline exactly.

## Native embedding provider

`braintree semantic embed` is the shipped provider command the optional seam probes through `BT_SEMANTIC_PROVIDER`. It reads a JSON array of texts on stdin and writes the protocol's JSON array of equal-width vectors on stdout:

```sh
export BT_SEMANTIC_PROVIDER='braintree semantic embed'
BT_MODEL_CACHE=/path/to/model-cache braintree similar 'expired authentication grants'

echo '["hello world","near duplicate hello world"]' | braintree semantic embed
```

It loads the selected model once per process and embeds in bounded batches, using `sentence-transformers/all-MiniLM-L6-v2` by default and falling back once to `BAAI/bge-small-en-v1.5` when the default cannot load. `BT_EMBEDDING_MODEL` selects the model and `--model NAME` overrides it. The command string is the provider identity the sidecar vector cache is keyed by, so pin `--model` in `BT_SEMANTIC_PROVIDER` whenever it is not the default.

Inference is offline: `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` are forced on before the runtime loads, and weights are read from the `BT_MODEL_CACHE`/`HF_HOME` cache, so nothing downloads at query time. An unpopulated cache or a missing extra exits non-zero, which the seam reads as capability absent: `braintree similar` falls back to the lexical baseline instead of failing. A malformed, empty, or wrong-width model result is refused the same way, and nothing is written to stdout except the vector array. Fastembed is imported lazily inside the command handler, so a plain install still loads no heavy module.

## Advisory density clustering

`braintree.clustering` is the derived layer above the embedding provider and UMAP reduction. Given the content-hash-keyed vectors `braintree.semantic` returns, it runs HDBSCAN over two spaces — the raw provider vectors and the seed-specific UMAP coordinates — and reports the more stable one. Stability is the mean pairwise Adjusted Rand Index across runs that vary the reduction seed and a seeded subsample draw, so no answer comes from a single fit; it is reported as evidence and never gates or hides a result. The layer is derived and advisory under `DEC-006`, only the explicit `braintree clusters` answer reaches it and only when the capability is present, `similar` is unchanged, and Markdown stays authoritative.

`min_cluster_size` defaults to `max(5, round(0.05 * n))` capped at 20 and `min_samples` to a third of it, so a small or uniform vault cannot shatter into spurious micro-clusters and a large one cannot hide sub-structure behind one giant cluster. Both are exposed on the result, and an explicit non-zero value overrides either. HDBSCAN's `-1` is noise: an unclustered node is named in `noise` and never attached to a nearby cluster. Outliers are a separate view of the members whose GLOSH density score reaches `outlier_threshold`, reported as their own tuple. Each cluster is labeled from its centroid-nearest member and the primary `Parent`/`Area` route its members share, so the label is reproducible and no generative summary is involved. An empty embedding set is the capability-absent path and returns an explicit unavailable result instead of raising. `hdbscan`, `numpy`, and `scikit-learn` are imported lazily inside the fit, so a plain install loads no heavy module.

`braintree clusters` is the bounded answer over that layer, and it is explicit about the capability. It probes the optional extra cheaply and, when the extra or the provider is absent, prints one advisory line and exits zero without loading a model or any heavy module. When the capability is present it embeds up to the layer's sample cap, clusters, and prints compact TOON bounded by `--limit` and a documented wall-clock budget: the chosen space and its stability evidence, the clusters with their representative member and route, the routes whose members the clustering separated across clusters (over-broad route suggestions), the noise (orphan) nodes, and the outliers. Everything is advisory and none of it becomes a claim, assignment, or authority.

`braintree digest NODE` is the graph-only companion: bounded by `--limit`, it prints the summaries and `next` of one hub's or coordinating node's unresolved direct members with no generative summary, and it needs no embedding capability, so it stays on the fast path. `braintree similar` is unchanged: with a provider it reranks by embedding cosine, and with the provider absent or unhealthy it is byte-identical to the lexical baseline.

## Embedding and clustering quality gate

`braintree benchmark quality` is the recorded, correctness-gated comparison that decides whether the optional layer earns each answer it backs. It measures on the committed `TAS-089` corpus (the same documents and probes the lexical baseline is scored on), reuses the existing `braintree benchmark verbs --verify` gate and the zero-live staged A/B for the round-trip and token side, and writes `benchmark/clustering-quality-evidence.json` with one keep, revise, or revert verdict per answer.

The measured numbers decide, not belief. On the frozen corpus the embedding ranking loses near-duplicate retrieval to the lexical baseline (MRR 0.44 against 0.59) while improving paraphrase recall (0.25 against 0.19), so retrieval earns a revise: keep the opt-in rerank where it helps and keep lexical as the near-duplicate reference. The clustering is stable across seeds and subsamples but agrees weakly with the graph's own routes (ARI 0.03, purity 0.31), leaves 65 of 118 nodes as noise, and the outlier view flags nothing at the default threshold, so clustering earns a revise. The graph digest is graph-only, bounded, and passes its exact-value gate, so it keeps. The evidence file records the host, the model, and the corpus digest; `verify` re-checks the corpus digest, the lexical baseline, the route parse, the decision shape, and the verb gate offline and loads no model:

```sh
braintree benchmark quality verify
```

The measurement itself is an explicit batch that needs the optional extra for the clustering fit, reads weights from the documented offline cache, and writes the evidence file:

```sh
braintree benchmark quality emit
```

## Validate and collect feedback

Installed projects validate the current graph with the bundled Markdown checker (which needs no sidecar) and query the optional index from any project root:

```sh
braintree check nodes
braintree index nodes
braintree search 'authentication' --limit 10
```

`braintree check` is read-only and intended for grooming or CI. It checks node identities and links, required frontmatter and lifecycle rules, canonical relationships and frontiers, dependency-pin syntax and revision drift, and primary-route reachability/cycles. Normal graph reads and mutations do not require it.

The read-only `braintree feedback scan` collector gathers `FBK` feedback from one or more external vaults without a sidecar or network access, and never writes to the scanned vault:

```sh
braintree feedback scan /path/to/other-vault
```

It prints compact TOON with each feedback node's vault, id, status, Braintree revision, and summary, and states `feedback: 0 nodes` when there is none.

The `braintree feedback record` writer is the recording half of the same mechanism. Run from a consuming project's vault root, it allocates the next `FBK` id from Markdown, routes the node to the vault's root hub unless `--route` overrides it, stamps the revision from the installed record, and writes `nodes/proposed/FBK-<n>-<slug>.md`:

```sh
braintree feedback record \
  --attempted '...' --friction '...' --improvement '...'
```

`--nodes` selects a `nodes/` directory other than the current one, and `--id`, `--summary`, and `--slug` override the allocated id, the derived summary, and the derived slug. The result is a valid, routed `FBK` node that `braintree check` accepts.

## Layout

`SKILL.md` is the portable instruction entrypoint. `agents/openai.yaml` is Codex-specific display metadata. `scripts/install.sh` is the POSIX-shell, AXI-oriented installer single source of truth and selects the Codex, Claude Code, or pi destination; `scripts/install-claude.sh` is its Claude Code wrapper. They return compact TOON-style fields on stdout, including structured errors, copy the skill into place, and generate the `<root>/.local/bin/braintree` command. `braintree` exposes `check`, `feedback scan`, `feedback record`, the index and coordination verbs, and a `benchmark` group for the development benchmarks; it hides the implementation language, package layout, and toolchain behind one command. The installer also writes a generated `installed-revision` stamp recording the semantic version plus the source revision it was copied from, and `braintree --version` reports it (`0.5.0+g1b58d57`, or `0.5.0+unknown` when the source revision cannot be determined). Compare the public `<version>` when deciding whether an installed skill and a vault are compatible; the `+<short-sha>` build metadata is provenance, not a compatibility ordering.

A vault uses this shape:

```text
nodes/
  index-map.md
  proposed/
  active/
  blocked/
  resolved/
```

The status directory and node filename are authoritative. Node frontmatter stores only a semantic `context_rev`, update time, a concise summary, and optional priority, next action, or exceptional disposition. `context_rev` changes only when a pinned consumer should reread the node; `updated` changes for every mutation, while Git retains edit history. Context-bearing links pin the dependency context revision they were last reconciled against. `nodes/index-map.md` holds focus, root-hub routes, and query recipes; it is not a copied node catalog and is not rewritten after every mutation. Hubs do not catalog members: `Parent` and `Area` backlinks provide membership, while a parent’s `next` may deliberately route to one child at the current execution frontier.

`DEF` nodes capture invariants; `DEC` nodes capture settled choices with concise Decision, Rationale, and Consequences sections. `FBK` nodes record Braintree friction for cross-project collection: they carry the installed `braintree_revision` and an `Attempted:`/`Friction:`/`Improvement:` `# Feedback` section, so `find nodes -name 'FBK-*.md'` discovers feedback from Markdown alone, and the read-only `braintree feedback scan` collector gathers those nodes from external vaults for triage into this graph. A resolved definition or decision means the work of establishing that knowledge is complete, not that it has expired: it remains current unless its sparse `disposition` is `deprecated` or `superseded`.

Decompose only when work reaches an independently resumable outcome, blocker, dependency, or verification boundary that also has durable execution-memory value; do not create a speculative child tree. A coordinating task states its own outcome and completion criteria, and its `next` names one current action or direct child frontier rather than cataloging children. Child completion is evidence, not an automatic parent resolution: resolve the parent only when its own criteria and evidence are complete and its created children are resolved or explicitly disposed.

The same threshold governs admission: do not turn chat, tool output, routine status, copied sources, or inert observations into nodes. Add durable knowledge, decisions, tasks, bugs, debt, blockers, and future features only when they alter a future action or materially reduce later resumption cost; otherwise omit them. Advance the existing node when it is the same thread, and split only at a current independently resumable boundary with that durable value.

## Coordinated parallel worktrees

Parallel support is conditional: independently assigned agents can safely work on disjoint node paths when a coordinator gives each worker a direct node path and exclusive write set. A worktree slice does not imply one node per agent: a fresh worker can continue the assigned node. It is not autonomous claiming, locking, or a guarantee that each worktree is globally current. `# Focus`, `priority`, and `active` are navigation signals, not claims; a worktree is a branch snapshot.

Preallocate IDs or give workers disjoint numeric ranges. A local collision search does not reserve an ID; autonomous creation needs an atomically shared reservation. Serialize changes to shared nodes and their status paths, including parents, definitions, root hubs, and the index. Integrate one worker branch at a time, reconcile dependency changes before dependent execution, and let only the coordinator resolve a parent after all child evidence is integrated.

The disposable real-Git-worktree screen demonstrates the supported boundary:

```sh
sh tests/worktree-parallel.sh
```

It covers: disjoint assigned edits; identical Focus selections rejected as duplicate assignments; distinct paths with a duplicate numeric ID; rename versus edit of one node; dependency drift after integration; and a parent blocked until evidence from both child branches is integrated. These are deterministic correctness and merge checks—not model-token measurements, hosted-tracker evidence, proof of autonomous locking, or proof of global freshness.

The design and its local 100/1,000/10,000-node comparison with conventional plans, a GitHub-Issues-style fixture, and a Jira-style fixture are documented in [BENCHMARK.md](BENCHMARK.md). Model-token consumption is the benchmark objective: `make benchmark` is a zero-token protocol entrypoint for a generated isolated, correctness-gated Codex workload. It uses fresh `codex exec -C` sessions and records actual token telemetry only when explicitly opted in. The temporary-fixture behavioral run is only a filesystem diagnostic; reads, bytes, and `work_units` are not model-token measures. The storage comparison also tests directory moves against stationary metadata, symlink views, and a copied index:

```sh
make benchmark
make diagnostic-benchmark
make storage-comparison
```

The packaged skill follows the portable Agent Skills convention; see the [Agent Skills specification](https://agentskills.io/specification) and [Claude Code skills documentation](https://code.claude.com/docs/en/skills) for host behavior.
