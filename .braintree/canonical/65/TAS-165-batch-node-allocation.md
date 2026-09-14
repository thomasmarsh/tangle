---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Let braintree allocate atomically reserve a caller-requested count of consecutive ids in one call.
---

# Context

Area [[IDX-001-execution-graph]].

`braintree allocate PREFIX` reserves exactly one id per invocation, so a caller
that needs several ids — a coordinator preallocating for parallel workers, or a
scenario minting a small batch of nodes — must either invoke it once per id or
fall back to a hand-picked range and reconcile it afterwards. [[TAS-023-parallel-id-allocation]]
established the atomic reservation primitive, [[TAS-103-make-one-command-node-capture-preserve-atomic-id]]
reused it for the record paths, and [[TAS-140-allocation-lifecycle-visibility]]
documented the burn-and-discard rule; none of them lets one call reserve more
than one id.

# Outcome

`braintree allocate PREFIX` accepts an optional positive count and atomically
reserves that many consecutive ids, reporting the reserved ids under the same
burn-and-discard rule as a single allocation, while the one-count invocation
keeps its current output.

# Done when

- `braintree allocate PREFIX [COUNT]` reserves `COUNT` consecutive ids in one
  atomic call, and the count defaults to one.
- The reserved ids are reported in a stable, parseable form.
- A non-positive or malformed count is a usage error (exit 2) that reserves
  nothing.
- Concurrency and burn semantics stay identical to the single-id path.
- `braintree allocate --help`, `references/coordination.md`, and the command
  index describe the count operand.
- `make test` and `braintree check` pass.

# Result

`braintree allocate PREFIX [COUNT]` reserves `COUNT` consecutive ids in one
atomic call and the one-count invocation keeps its exact output. The batch is
selected inside one `BEGIN IMMEDIATE` transaction in the new
`src/braintree/allocation.py`, which owns the verb's operand grammar, its
usage-error text, and its two output shapes; `COUNT` defaults to one, and
`count == 1` and `count > 1` share that one reservation path. `count == 1`
prints `id: "TAS-001"` unchanged; a larger count prints `ids[N]{id}:` with one
`  "TAS-001"` row per reserved id, so the reserved ids are parseable without a
second sidecar read. A non-positive or malformed `COUNT`, a missing `PREFIX`, and
a fourth operand each exit `2` before the sidecar is opened, so a rejected call
reserves nothing. Burn and concurrency semantics are unchanged: a batch advances
`next_value` for every candidate it consumed, a candidate already on disk is
skipped and still burned, and `braintree reservations` reports the unwritten ids
of `braintree allocate TAS 3` as `"TAS","4","1-3"`. `src/braintree/help.py` names
the `COUNT` operand, `src/braintree/main.py`'s command index reads
`allocate PREFIX [COUNT]`, and `references/coordination.md`'s parallel-worktree
bullet states that one call reserves a batch of `COUNT` consecutive ids in a
single transaction. `SKILL.md`'s mutation rule carries the same operand inside
the 16,000-byte `test_core_stays_concise` bound (15,681 -> 15,739 bytes).

The verb is routed from `src/braintree/main.py` to the new module because
`src/braintree/cli.py` and `src/braintree/sidecar.py` are two of the seven
`src/braintree/*.py` paths embedded as observable prompt content in
`benchmark/memory-authority-cases.json`, so any byte change to either one fails
`tests/test_memory_authority.py::test_verify_reports_missing_artifact_or_passes`
(`authority artifact differs from a re-derivation`) in the default `make test`.
This is the conflict [[TAS-140-allocation-lifecycle-visibility]] settled the same
way — reach the answer through a new module and leave every observable path
byte-identical — and this slice follows that resolution:
`git diff --exit-code 72e7968 -- src/braintree/cli.py src/braintree/sidecar.py`
exits `0`. The observable re-record is explicitly avoided, not dropped:
[[TAS-144-derived-artifact-regeneration-ownership]] keeps regeneration ownership,
and offline `braintree benchmark authority record --input` cannot rebase the
frozen live measurement (the new prompt digests regenerate `status:
"incomplete"`, `decision: "untested"`, and the incomplete reasons), so a faithful
re-record needs a live paid run and is out of this slice.

Two costs are recorded rather than hidden. First, the candidate-selection and
counter-advance loop now has a second spelling in `src/braintree/allocation.py`,
because the frozen `src/braintree/sidecar.py` cannot gain `allocate_many`; the
capture path in `src/braintree/node_record.py` keeps the frozen module's
single-id `sidecar.allocate`, and the new module reuses
`sidecar.open_connection` and `sidecar._run_transaction`, so the busy-retry
transaction wrapper keeps one spelling. Second, `braintree.cli`'s own command
index still reads `allocate PREFIX`, because that file is frozen; the installed
index a caller sees is `src/braintree/main.py`'s, which reads
`allocate PREFIX [COUNT]`.

Tests: `tests/test_bt_foundation.py` adds
`test_allocate_reserves_a_count_of_consecutive_ids` (one call returns the three
exact `ids[3]{id}:` rows and the counter continues past the batch),
`test_allocate_count_of_one_keeps_the_single_id_output` (bare and explicit `1`
both print the unchanged `id:` line),
`test_allocate_count_skips_on_disk_identities_and_stays_consecutive` (with
`TAS-002` on disk and an empty sidecar, `COUNT` 2 returns `TAS-001` and
`TAS-003`), `test_allocate_batch_burns_the_reserved_ids_it_never_wrote`
(`reservations` reports `"TAS","4","1-3"`), and
`test_allocate_rejects_a_bad_count_or_extra_operand_without_reserving` (`0`,
`x`, a missing `PREFIX`, and a fourth operand each exit `2` with no counter
advance), plus `test_allocate_help_and_command_index_name_the_count_operand`
(`braintree allocate --help` prints `usage: "braintree allocate PREFIX [COUNT]"`
and the installed index prints `"allocate PREFIX [COUNT]"`).
`tests/test_bt_verification.py` extends the cross-process allocation screen with
`test_concurrent_batch_allocation_is_unique_and_dense`: four concurrent
`allocate CON 3` calls return four disjoint three-id blocks, each internally
consecutive, covering `CON-001` through `CON-012`, which only a per-call atomic
transaction can produce.

Evidence: `uv run pytest -q tests/test_bt_foundation.py
tests/test_bt_verification.py` -> 37 passed; `make test` -> 738 passed, 3
skipped, 79 deselected, with `uv run ruff check` -> all checks passed and
`uv run mypy` -> no issues in 76 source files; `braintree check` ->
`graph check: passed (222 nodes)`; `git diff --exit-code 72e7968 --
src/braintree/cli.py src/braintree/sidecar.py` -> exit `0`. No node pins this node, it pins no
context-bearing dependency, and it is not a coordinating parent, so
`context_rev` stays `1` and no other node is edited.
