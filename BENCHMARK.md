# Benchmark: file-only knowledge execution graph

## Decision

Adopt V3: atomic Markdown nodes in authoritative status directories, a small
routing-only `nodes/index-map.md`, and local revision pins only on context-bearing
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
not a comparable canonical answer. See the independent verification report at
`/private/tmp/kgbench.kBlk1h/reports/verification.md`.

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
cost is the better decision metric. The exact V3 revision overhead is
**155,500 B** at 10k: 70,000 B for `rev` lines plus 85,500 B for dependency
pin suffixes, or **7.2%** of V3 node bytes. Do not use the V3 evaluator's
298,078 B aggregate classification as the revision overhead.

Field judgment from the fixtures:

- Keep `summary` and `next`: their fixture text is useful only when it lets an
  agent act after opening a selected candidate. Generic summaries do not earn
  their cost.
- Keep task `priority` and `updated`: they power active-P0 and recent queries;
  both require disciplined updates.
- Keep `rev` plus pins only for context-bearing dependencies. This pays for a
  two-operation stale-dependency check; do not pin navigation or casual links.
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
| area resume | 2.79 MB body scan | whole corpus scan | unfinished-dir scan, then selected node; still no automatic unique choice |
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

Each node has required `rev`, `updated`, and `summary`; task `priority` is
optional; `next` is required for active/proposed tasks and is the unblock
action for blocked tasks. Context-bearing links read `Depends on [[DEF-ID]] at
rev N.` The filename supplies ID/type; the directory supplies status. The
colocated route card must never copy node status, priority, revision, timestamp, or summary.
It may contain an advisory Focus pointer, but omit Focus when no active work
exists.

```sh
# Known item / unfinished / blocked / actionable P0
find nodes -type f -name 'TAS-101-*'
find nodes -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'
find nodes -type f -path '*/blocked/TAS-*.md'
find nodes -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +

# Changed definition: read DEF header for its current rev, then use that old pin
rg -n -F 'Depends on [[DEF-auth-protocol]] at rev 7' nodes

# Lifecycle, explicit inbound references, and recent five
rg -l '^disposition: superseded$' nodes
rg -l -F '[[TAS-101]]' nodes
rg -H '^updated:' nodes | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5
```

The dependency search returns explicit direct edges only. Indirect impact
requires repeating it through returned nodes. Recent results are authoritative
only if every node write refreshes `updated`.

## Changes made from the evidence

- Replaced the global node catalog with a routing-only colocated index and authoritative
  status directories, removing routine index updates and stale copied state.
- Removed duplicated ID/type/status frontmatter; added local `rev`, concise
  `summary`, task `priority`/`next`, sparse `disposition`, and context pins.
- Corrected the documented recency recipe and added timestamp-safe YAML graph
  validation.
- Resolved the evaluation graph node and removed the now-stale Focus pointer.

## Verification

The evaluation fixtures stayed outside the repository in
`/private/tmp/kgbench.kBlk1h`. Evidence was independently audited with:

```sh
ruby /private/tmp/kgbench.kBlk1h/audit.rb
ruby /private/tmp/kgbench.kBlk1h/merge_audit.rb
sh tests/skill.sh
sh tests/install.sh
make test
git diff --check
```

The final working-tree verification also checks every untracked text file for
trailing whitespace, runs the documented query smoke checks, validates all
wikilinks and dependency-pin syntax, and reports those exact results in the
change handoff.

## Remaining tradeoffs

No database, daemon, indexer, or persistent helper script was introduced.
That preserves portability and local authority, but leaves numerical ID races,
directory rename/edit conflicts on the same node, timestamp discipline, no
automatic global ranking, and linear scans for cross-cutting questions. These
are preferable here to a mutable global cache only while the scan costs and
agent interaction remain acceptable for the real repository.
