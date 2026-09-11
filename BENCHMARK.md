# Benchmark: file-only knowledge execution graph

## Benchmark objective

Actual model-token consumption is the optimization metric. Fixture bytes,
filesystem reads, elapsed time, and synthetic `work_units` are not token
proxies. A token result is valid only when the controlled task is correct.

`scripts/token-benchmark.rb` reads only `token_usage_record` usage maps from a
fresh Codex session JSONL and reports `input_tokens`, `cached_input_tokens`,
`uncached_input_tokens`, `output_tokens`, `reasoning_output_tokens`, and
`total_tokens`. It derives uncached input as input minus cached input and
rejects invalid total accounting. Codex emits cumulative `turn_token_usage`
snapshots: the script requires a nonempty `payload.turn_id`, rejects per-turn
regressions, and uses only the final valid snapshot for each distinct turn. The
[official OpenAI response usage
schema](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
likewise documents input, cached-input, output, reasoning, and total usage;
the names above are the verified local Codex-session telemetry names.

`make benchmark` makes zero live calls: it reports the opt-in recording command
and an absent baseline rather than silently substituting a filesystem metric.

## Decision

Adopt V3: atomic Markdown nodes in authoritative status directories, a small
routing-only `nodes/index-map.md`, and local semantic `context_rev` pins only on context-bearing
dependencies. Do not use a copied global node ledger.

V3 is hypercompetitive for state discovery and routine mutations: it removes
the mandatory second-file index write and the measured global merge conflict.
It is not strictly superior for every workflow: reverse links, priority, area,
and recency still scan node files. The honest file-only tradeoff is a tiny,
non-authoritative route card plus targeted `rg` scans, not a new cache.

All claims below concern local synthetic Markdown fixtures and local shell
commands. They do not measure hosted GitHub Issues or Jira, whose indexing,
permissions, UI, and network costs differ.

## Normalized task-only results

`unfinished` includes `active`, `proposed`, and `blocked` tasks. `P0` means
non-resolved task P0; `active P0` is shown separately where it selects work.
The deliberately inconsistent TAS-00023 copied state is counted as blocked
from its canonical node, not from the stale ledger/label.

| scale | unfinished | blocked | non-resolved P0 | direct DEF-00020 dependents | external TAS-00043 references | five recent |
|---|---:|---:|---:|---:|---|---|
| small | 86 | 6 | 2 | 19 | TAS-00045, TAS-00046, TAS-00077 | DEF-00100, TAS-00099, TAS-00098, TAS-00097, TAS-00096 |
| 1,000 | 864 | 52 | 11 | 19 | TAS-00045, TAS-00046, TAS-00077 | DEF-01000, TAS-00999, TAS-00998, TAS-00997, TAS-00996 |
| 10,000 | 8,636 | 509 | 90 | 19 | TAS-00045, TAS-00046, TAS-00077 | DEF-10000, TAS-09999, TAS-09998, TAS-09997, TAS-09996 |

These are the expected answers for each equivalent fixture. Earlier evaluator
tables that report 91/910/9,091 include definition records, not only tasks.
The GitHub-style label query reports only 5/53/535 blocked because TAS-00023
has `active` labels but a blocked body; that is an ambiguity demonstration,
not a comparable canonical answer. The original fixture audit was exploratory.
The reproducible behavioral fixture is a secondary filesystem diagnostic. Run
`make diagnostic-benchmark` to regenerate temporary fixtures and compare its
deterministic local-work baseline.

## Four baseline comparison and V3

| representation | 10k records + bytes | state / priority lookup | routine mutation | authority and contention |
|---|---:|---|---|---|
| Current KG | 10,000 + 2.79 MB nodes + 0.92 MB index | index answers status; P0 scans nodes | node **and** global index | copied index can be stale; unrelated edits produced 2 merge conflicts |
| Plan documents | 100 plans + 2.33 MB | whole-plan corpus scan | one plan file | no cache; separate item hunks merge, tail adds conflicted |
| GitHub-style files | 10,000 + 3.39 MB | whole issue corpus scan | one issue file | no cache; duplicated labels/body made TAS-00023 ambiguous |
| Jira-style files | 10,000 + 4.49 MB | whole issue corpus scan | one issue file | no cache; header is comparatively large |
| V3 recommended | 10,000 + 2.17 MB nodes + 890 B index | status by directory; active P0 scans active nodes | one node; status is a rename | no copied state; different-node edits have no shared file |

At 10k, the original ledger was 33.1% of its node corpus and every routine
mutation changed it. The isolated `git merge-file` experiment found two
conflict regions for unrelated current-KG edits and three for concurrent
additions. Different-node V3 edits share no file. V3 status moves do require
rename-aware resolution when another actor concurrently edits that *same*
node.

## Coordinated-worktree correctness screen

`sh tests/worktree-parallel.sh` builds disposable real Git repositories and
worktrees. It is deterministic correctness and merge evidence, not a
model-token result, hosted-tracker comparison, autonomous-locking mechanism, or
proof that a worktree is globally fresh. It supports only disjoint,
coordinator-assigned node paths.

The six scenarios are: (1) two assigned nodes retain both results after serial
integration; (2) two snapshots read the same Focus pointer, so duplicate work
is rejected by the coordinator; (3) independent paths with the same numeric ID
merge but the graph checker rejects the duplicate identity; (4) a status rename
and content edit of one node are divergent and require reconciliation; (5) an
integrated dependency revision makes an unmodified consumer stale before it
executes; and (6) a coordinating parent is ineligible until evidence from every
child branch is integrated.

Accordingly, `# Focus`, `priority`, and `active` are advisory rather than
claims, and each worktree is a branch snapshot. A worktree slice is not a graph
node boundary: a fresh worker can continue its assigned node. Numeric IDs require
coordinator preallocation/disjoint ranges or an atomically shared reservation.
Shared nodes and status paths are serialized. The coordinator integrates one
branch at a time, reconciles stale dependencies, and alone resolves parents after
child evidence. Run the screen directly with `sh tests/worktree-parallel.sh`, or
as part of the full suite with `make test`.

## Scale and content-cost measurements

Exact node bytes were summed with `stat`, never `wc` batch totals.

| approach | small | 1,000 | 10,000 | reported format-cost view at 10k |
|---|---:|---:|---:|---|
| Current KG nodes / index | 27,421 / 9,298 B | 276,414 / 91,678 B | 2,794,024 / 924,500 B | 52.4% format + metadata framing under its conservative classifier |
| Plan documents | 22,963 B | 231,035 B | 2,329,885 B | 37.5% structural framing (values counted useful) |
| GitHub-style files | 32,968 B | 333,802 B | 3,386,601 B | 50.1% metadata; 20.5% actionable body under its classifier |
| Jira-style files | 44,353 B | 445,790 B | 4,486,696 B | 75.4% when all frontmatter is called framing |
| V3 nodes / route index | 21,360 / 890 B | 215,088 / 890 B | 2,170,346 / 890 B | 1,518,152 B header + 652,194 B body; classifications are not directly interchangeable |

The boilerplate classifications intentionally differ in whether field values
are useful; they should not be used as a single ranking. Total interaction
cost is the better decision metric. The semantic-revision migration adds eight
bytes per node header and dependency-pin suffix. At 10k, its exact overhead is
**315,500 B**: 150,000 B for `context_rev` lines plus 165,500 B for
dependency-pin suffixes, or **14.5%** of the original 2,170,346 B V3 node
corpus. This small fixed cost prevents cosmetic edits from creating false stale
work; do not use the V3 evaluator's 298,078 B aggregate classification as the
revision overhead.

Field judgment from the fixtures:

- Keep `summary` and `next`: their fixture text is useful only when it lets an
  agent act after opening a selected candidate. Generic summaries do not earn
  their cost.
- Keep task `priority` and `updated`: they power active-P0 and recent queries;
  both require disciplined updates.
- Keep semantic `context_rev` plus pins only for context-bearing dependencies.
  Increment it only when a consumer should reread the node; this pays for a
  two-operation stale-dependency check without edit-history false positives.
  Do not pin navigation or casual links.
- Keep `disposition` sparse for abandoned, deprecated, or superseded work.
  Do not add empty lifecycle, owner, label, ID, type, or dependency-array
  fields without a measured query they eliminate.

## Operational cost at 10,000 nodes

| workflow | current KG | plans / GitHub-style / Jira-style | V3 |
|---|---|---|---|
| orient and act | index plus P0 search and node; no unique rank | README/plan query plus node; no unique rank | route index plus pointed node; advisory focus must validate |
| unfinished / blocked | full 0.92 MB ledger | full 2.33 / 3.39 / 4.49 MB corpus | directory traversal, authoritative; do not print the 8,636-path list |
| highest actionable P0 | node corpus search | corpus search | `rg` active nodes, 0.13 s locally; 71 active candidates |
| changed DEF-00020 | 2.79 MB backlink scan plus follow-up state reads | whole corpus direct-link scan | definition header + exact pinned backlink scan: 19 stale candidates, 0.12 s locally |
| area resume | 2.79 MB body scan | whole corpus scan | root-hub route, then bounded `Parent`/`Area` backlink scan; still no automatic unique choice |
| recent five | 0.92 MB staleable ledger | whole corpus timestamp scan | whole V3 corpus timestamp scan, 0.19 s locally |
| priority / block / resolve | 2 files and global index edit | 1 record/plan file | 1 node; status transition is a rename |

V3 takes one or two narrow operations for authoritative status, a known item,
and a pinned-definition staleness check. It deliberately does not promise this
for recency, reverse links, broad area resumption, or a uniquely ranked next
task. At 10k those are linear file scans of roughly 2.17 MB, locally fast but
not free in agent interaction cost.

## Recommended operating contract

```text
nodes/index-map.md           # short routes and tested commands only
nodes/proposed/ID-slug.md    # status is the directory
nodes/active/ID-slug.md
nodes/blocked/ID-slug.md
nodes/resolved/ID-slug.md
```

Each node has required `context_rev`, `updated`, and `summary`; task `priority` is
optional; `next` is required for active/proposed tasks and is the unblock
action for blocked tasks. Context-bearing links read `Depends on [[DEF-ID]] at
context_rev N.` The filename supplies ID/type; the directory supplies status. The
colocated route card must never copy node status, priority, revision, timestamp, or summary.
It may contain an advisory Focus pointer, but omit Focus when no active work
exists.

Admit only durable information that can change a future decision or action or
materially reduce future resumption cost. Independent resumability is necessary
but insufficient for a new node; an agent, worktree/write-set, handoff,
failed-check, routine-verification, incidental-cleanup, or mechanical-cleanup
boundary alone stays in the current node's `next`, result, evidence, or handoff.
Agents and nodes are not one-to-one. This includes useful knowledge,
architectural or operational decisions, executable tasks,
bugs, debt, blockers, and future features. Do not store transcripts, tool-call
logs, routine narration or status, copied source material, or observations with
no foreseeable decision or action value. Update an existing node for the same
outcome, question, component, decision, or defect; create one only at a current
independently resumable outcome, blocker, dependency, or verification boundary
with durable execution-memory value.

`DEF` nodes record invariants and `DEC` nodes record settled choices with concise
Decision, Rationale, and Consequences sections. Resolved status means formation
work is complete; resolved definitions and decisions remain current unless a
sparse `disposition` explicitly marks them deprecated or superseded.

Each relationship has one stored direction: `Parent` belongs on the child,
`Area` on the assigned node, `Depends on` on the consumer, `Superseded by` on
obsolete work, and `Indexes` on a deliberate route. The index routes to a
small set of `IDX` root hubs; every other node has exactly one primary
`Parent` or `Area` link that reaches a hub, so unfinished work cannot silently
be orphaned. Hubs derive membership with exact `Parent`/`Area` backlink
searches rather than copied catalogs. Child, parent-of, indexed-by, backlink,
and depended-on-by views are exact searches, not reciprocal stored edges. A
parent’s `next` can deliberately route to its current child frontier without
becoming a child catalog.

Decompose only at an independently resumable outcome, blocker, dependency, or
verification boundary with durable execution-memory value. A coordinating task owns a stated outcome and concise
completion criteria; its `next` selects one concrete action or direct child
frontier, never a child list. Resolve the parent from evidence that its own
criteria are met, after every child created for that outcome is resolved or
explicitly disposed; child completion alone is not a roll-up.

```sh
# Known item / unfinished / blocked / actionable P0
find nodes -type f -name 'TAS-101-*'
find nodes -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'
find nodes -type f -path '*/blocked/TAS-*.md'
find nodes -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +

# Changed definition: read DEF header for its current context_rev, then use that old pin
rg -n -F 'Depends on [[DEF-auth-protocol]] at context_rev 7' nodes

# Lifecycle, explicit inbound references, and recent five
rg -l '^disposition: superseded$' nodes
rg -l -F '[[TAS-101]]' nodes
rg -H '^updated:' nodes | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5

# Root hubs and derived primary memberships
rg -n '^\s*- Indexes \[\[IDX-' nodes/index-map.md
rg -n '^(Parent|Area) \[\[' nodes
```

The dependency search returns explicit direct edges only. Indirect impact
requires repeating it through returned nodes. Recent results are authoritative
only if every node write refreshes `updated`.

## Changes made from the evidence

- Replaced the global node catalog with a routing-only colocated index and authoritative
  status directories, removing routine index updates and stale copied state.
- Removed duplicated ID/type/status frontmatter; added local semantic
  `context_rev`, concise `summary`, task `priority`/`next`, sparse
  `disposition`, and context pins.
- Corrected the documented recency recipe and added timestamp-safe YAML graph
  validation.
- Resolved the evaluation graph node and removed the now-stale Focus pointer.

## Primary token benchmark

The primary benchmark is a generated, isolated repository workload. Each fresh
session receives an imprecise request to resume data-import hardening and must
inspect the fixture before returning a compact JSON answer. The correctness gate
requires the active coordinator's execution frontier, current rather than
superseded decision, every revision-stale dependent, and an actionable orphan.
The prompt does not contain the answer IDs. For graph runs, the generator copies
the repository's exact `SKILL.md` to
`.agents/skills/knowledge-execution-graph/SKILL.md`, records its SHA-256, and
explicitly requires `$knowledge-execution-graph`; zero-token generation checks
that copy and runs the copied graph checker while allowing only the named
intentional orphan and expected stale pins. The graph fixture therefore measures
the installed project skill rather than merely Markdown-shaped files.

The graph representation is tested at `small` (32 distractors) and `large`
(320). The conventional-plan control contains the same coordinator/frontier,
decision supersession, revision-pinning, orphan facts, and the same number of
historical distractors. It controls semantic answer content and distractor
volume; it does **not** control the graph-specific skill instruction, file
topology, or the representation's native retrieval workflow. Those are the
deliberate treatment differences, so this is evidence about this retrieval task,
not a universal token ranking.

Every graph fixture installs the same distributable files as the project Codex
installer: `SKILL.md`, `agents/openai.yaml`, and `scripts/graph-check.rb` under
`.agents/skills/knowledge-execution-graph/`; the zero-call check byte-compares
the copied instructions and metadata with this repository. Every live invocation uses `codex exec --json --ignore-user-config --ignore-rules
-C GENERATED_FIXTURE` with a fresh session and read-only sandbox. Authentication
is preserved by the CLI while unrelated user configuration/rules are excluded;
the explicit copied project skill remains in scope. An output JSON Schema and an
exact-value gate reject malformed or incorrect answers. The report records the
fixed fixture version, seed, generated fixture SHA-256, graph-skill SHA-256,
requested settings, representation, scale, per-sample totals, and medians.
Before accepting a live sample, it verifies safe `session_meta`/`turn_context`
telemetry fields for the actual CLI version, model, reasoning effort, and fixture
cwd. It reports input, cached input, uncached input, output, reasoning output,
and total tokens from the final cumulative `token_usage_record.turn_token_usage`
snapshot for each distinct `payload.turn_id`; session/thread totals and earlier
same-turn snapshots are never summed. Each live session has a 300-second
default timeout (bounded to 600 seconds) and runs are capped at three
repetitions. Model runs are stochastic, so a checked-in absent or trivial
baseline establishes no result.

A live sample is accepted only after its `--json` stream contains
`turn.completed`, its answer artifact exists and passes the exact-value gate,
and final cumulative telemetry is present. Telemetry emitted by an incomplete
stream is rejected and is never promoted to benchmark evidence. The generated
schema uses the CLI-compatible strict object form (required keys and
`additionalProperties: false`) without a draft-dialect declaration.
The recorder tolerates only one verified pre-stream CLI progress line, exactly
`Reading`; it strictly parses every subsequent event line as JSON.

The `cold-resume` case is an isolated graph-only small/large fixture. Its exact
gate requires the active task deliberately named by `# Focus` and that node's
exact `next` action, while resolved history, blocked work, proposed work, and
unselected active work are distractors. It is used only to compare one skill
route variant at a time; baseline and candidate must use its same fixture hash,
prompt, model, effort, CLI version, and recording configuration. Generate it
without live calls with `ruby scripts/token-benchmark.rb --check-fixture --case cold-resume`.

The final two-call cold-resume route screen was rejected, not adopted. Both
fresh sessions returned the exact gate answer, but the recorder rejected their
stdout before artifacts were written because a non-JSON `Reading` progress line
preceded the JSON stream. Recovered final per-turn telemetry was baseline
84,165 total (83,630 input, 38,400 cached, 45,230 uncached, 535 output, 124
reasoning) and candidate 106,538 total (105,931/91,904/14,027/607/102).
The candidate's only change was a concise Focus route rule and it was restored.
These are explicitly diagnostic, not checked-in benchmark samples: no further
call is authorized to repair the pair. The baseline/candidate use the same case,
seed, prompt, model `gpt-5.6-terra`, medium effort, CLI `0.154.0`, scale, and
read-only configuration. Their full fixture hashes differ because the fixture
hash includes the isolated installed skill copy: baseline
`f00c27f91051f0e8db98a3cd68410c120e89e1aacc17c13d6609565bf249d658` with
skill `a50cd53da62c7969a8903cf062e3867be8357e74ba771a572a28be9a1393ee5b`,
candidate `8f18b8c4f510f148c026857c27811baa155f3e0393dc52013f29c1c60259bf04`
with skill `e9b3117e4acb6c3f0b286332ef9620c16774e299cc00689bfb9a9de942096feb`.

`--check-fixture` also rejects graph fixtures with stale dependencies other
than the two intentionally revision-stale consumers, so its permissive checker
mode cannot mask an accidental stale pin. `make benchmark` makes zero model calls. Inspect the generated variants and the
sanitized telemetry schema without session content with:

```sh
ruby scripts/token-benchmark.rb --check-fixture
ruby scripts/token-benchmark.rb --inspect-session ~/.codex/sessions/...jsonl
```

## Historical implementation-cost accounting

Historical Codex sessions can account for the implementation cost of a named
task, but they are not matched, correctness-gated benchmark samples. Find
candidate session files without printing their contents, then import an exact
task-path match:

```sh
rg -l -F '/root/token_benchmark_realism' ~/.codex/sessions --glob '*.jsonl'
ruby scripts/token-benchmark.rb --session ~/.codex/sessions/...jsonl --task-path /root/token_benchmark_realism
```

The importer reads only safe session metadata (`agent_path`, CLI version,
model, and reasoning effort) plus cumulative `token_usage_record.turn_token_usage`
snapshots. It requires a nonempty turn ID for every accepted usage record,
rejects malformed or regressing snapshots, and sums only the final valid
snapshot of each distinct turn.
It derives those labels from telemetry; optional `--model` and
`--reasoning-effort` values are expectations that must match observed values.
It rejects missing or ambiguous provenance and reports
`historical-implementation-cost`, with per-session and aggregate totals—never
correctness, medians, or a benchmark score. Session text is neither emitted nor
stored by the command.

Record a reviewable graph baseline (three model sessions) only by explicit
opt-in; record the matched control separately (three more sessions):

```sh
ruby scripts/token-benchmark.rb --record --model MODEL --reasoning-effort low --representation graph --scale small --repetitions 3 --output benchmark/token-baseline.json
ruby scripts/token-benchmark.rb --record --model MODEL --reasoning-effort low --representation plan --scale small --repetitions 3 --output benchmark/token-plan-control.json
```

For a minimal initial baseline, use two fresh sessions per representation:

```sh
ruby scripts/token-benchmark.rb --record --model MODEL --reasoning-effort low --representation graph --scale small --repetitions 2 --output benchmark/token-graph-small-2.json
ruby scripts/token-benchmark.rb --record --model MODEL --reasoning-effort low --representation plan --scale small --repetitions 2 --output benchmark/token-plan-small-2.json
```

## Secondary filesystem diagnostic

`scripts/behavioral-benchmark.rb` builds disposable 100- and 1,000-node graph
fixtures using only Ruby's standard library. Each contains an index route to a
root hub, a current definition, a superseded and current routing decision,
pinned task dependencies, an active high-priority cold-resumption record, and
one deliberately disconnected actionable record. It performs four bounded
workflows: recover the active cold-resume P0 incident and its next action;
select the current decision structurally while excluding the superseded one;
find only dependencies pinned to the old definition revision; and discover the
unfinished disconnected record.

Run `make diagnostic-benchmark`. Output is compact TOON with node reads, bytes
scanned, matches, and deterministic work units (`reads + bytes`), followed by
four advisory per-scan milliseconds. These are diagnostics only, not model
token results. The checked baseline in
`benchmark/behavioral-baseline.txt` intentionally excludes timings, because
they vary by machine; `--verify` compares only deterministic work and expected
answers. No generated fixture is retained and the benchmark has no network or
third-party dependency. Add a scale deliberately with `--scales N,N`; update
the tracked baseline before using `--verify` for that scale.

## Verification

The historical evaluation fixtures stayed outside the repository. Current
reproducible evidence is checked with:

```sh
sh tests/skill.sh
sh tests/install.sh
make benchmark
make diagnostic-benchmark
make test
git diff --check
```

The final working-tree verification also checks every untracked text file for
trailing whitespace, runs the documented query smoke checks, validates all
wikilinks and dependency-pin syntax, and reports those exact results in the
change handoff.

## Status-storage comparison

`scripts/storage-comparison.rb` creates four disposable 100-node Git fixtures:
the adopted status directories, stationary prefix-sharded files with an
authoritative `status` field, stationary files with symlink status views, and
stationary files with one copied status index. `make storage-comparison` checks
the deterministic baseline below; it measures the initial active query, a
staged Git transition, concurrent transitions of two different nodes, and a
deliberately removed view entry.

| representation | staged transition / paths | active-query body reads | different-node merge conflicts | stale/broken view after injected omission | stable canonical editor path |
|---|---|---:|---:|---:|---:|
| directory authority | `R100` / 2 | 0 | 0 | 0 | no |
| stationary metadata | `M` / 1 | 100 | 0 | 0 | yes |
| symlink status view | `R100` / 2 | 0 | 0 | 1 | yes |
| copied status index | `M` / 1 | 1 | 1 | 1 | yes |

The stationary metadata layout buys a stable editor path, but moves status
authority into every node and turns the bounded directory query into a scan of
all canonical files. Symlinks preserve the fast view but add a second,
independently breakable representation; the local test confirms Git recognizes
the link move, not that the old view path remains valid. Symlink creation and
checkout semantics also vary by filesystem and Git configuration, which is an
unnecessary portability constraint for this file-only skill. The copied index
is fast only by adding a mandatory cache; its one-line concurrent updates
conflict in the fixture and an omitted entry silently hides a node.

Keep authoritative status directories. Git reports a clean rename for an
unchanged status transition, unrelated node transitions merge cleanly, status
queries inspect directory entries without reading bodies, and there is no
derived view to regenerate or validate. The known tradeoff is that an editor's
old path changes on a status transition; basename wikilinks and Git rename
tracking keep node identity stable.

## Remaining tradeoffs

No database, daemon, indexer, or persistent helper script was introduced.
That preserves portability and local authority, but leaves numerical ID races,
directory rename/edit conflicts on the same node, timestamp discipline, no
automatic global ranking, and linear scans for cross-cutting questions. These
are preferable here to a mutable global cache only while the scan costs and
agent interaction remain acceptable for the real repository.

An optional, read-only `scripts/graph-check.rb` is distributed with the skill
for grooming and CI. It uses only Ruby's standard library and retains no state;
it checks integrity but is not part of normal graph reads or mutations.

## Routine-mutation screen

`routine-mutation-status-v1` is the smallest writable graph fixture: it asks
the model to resolve one active task, make one semantic summary/result change,
advance `context_rev` from 3 to 4, refresh UTC `updated`, remove `next`, and
preserve its Area and pinned dependency. Its gate requires a completed turn and
exact answer artifact, the exact node move/content/revision, no other
fixture-file change, and a clean graph check. `--check-fixture --case
routine-mutation` is zero-live; recording remains explicit with `--record` and
uses a writable fixture sandbox only for this case. A deterministic fake-CLI
test exercises this full writable lifecycle, including final per-turn telemetry;
the filesystem gate runs before fixture cleanup and before telemetry recording.

The first two-call mutation screen is rejected without token evidence. Both
attempted fresh Terra/medium sessions (cumulative live count 6 to 8) emitted a
completed-turn telemetry snapshot, but neither yielded an accepted recorder
artifact and filesystem gate, so neither can be a benchmark sample. The
baseline diagnostic total was 155675 (154249 input, 138496 cached, 15753
uncached, 1426 output, 330 reasoning); the compact-rule candidate diagnostic
total was 178619 (176976/148480/28496/1643/448). These values are retained only
to document the failed recording path, not as a comparison. The fixture hashes
were respectively `74efe13fa451c93208c4b03331087c5bdea84daf460cd6defffe4ef04772a8ef`
with skill `a50cd53da62c7969a8903cf062e3867be8357e74ba771a572a28be9a1393ee5b`,
and `06dbab85bbf7f29fd1e11a8c3dac2fb805aba35caf6d48014b163b8b110697c4` with
skill `478bb802df43ee1d212f00db95b829a4aca2517e06eb620a9cf261709b085e78`.
The candidate wording was restored; do not repeat it. The zero-live writable
runner test subsequently fixed fixture revision setup and the shadowed
pre-session snapshot; the two failed invocations remain ineligible as benchmark
samples because neither passed the original full gate.
