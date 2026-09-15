---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Document that allocate burns an id and expose outstanding reservations so an unused id is distinguishable from a missing node.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Hekate `FBK-018` finding 2 and Hekate `FBK-025` finding 2 at
`0.6.0+g3bacaf5`. Probe in `/tmp/tangle-r7`: `tangle status` prints only
`reservations[1]{prefix,next}` (`TAS,4`), so an id reserved and never written is
invisible; a real groom reported `tangle allocate TAS` returning `TAS-057`
after `TAS-052` with `TAS-053`-`TAS-056` neither nodes nor listed reservations.
The contract never states that an allocation the caller discards is burned
permanently.

# Outcome

The contract states that `tangle allocate` permanently burns an id when the
caller discards it, and a read-only answer lets a groomer tell a
reserved-but-unwritten id from a missing node; an unused allocation can be
released or reclaimed under a stated rule.

# Done when

- Documentation states the burn-and-discard semantics of `tangle allocate`.
- A read-only command or output field lists outstanding reservations or
  otherwise distinguishes burned ids from missing nodes.
- Releasing or reclaiming an unused allocation is either supported with a rule
  or explicitly disposed with rationale.
- Tests cover the visibility answer.
- `make test` passes.

# Result

`tangle allocate` now has its burn-and-discard semantics stated and a
read-only answer that names the ids it burned. `references/coordination.md`'s
parallel-worktree allocate bullet states that the counter only advances, so an
allocation the caller discards is never returned and never reused, that
`tangle reservations` lists each prefix's burned ids — reserved with no node
on disk — so a gap in the vault is a discarded allocation, not a missing node,
and that there is no release or reclaim because a reused id could collide with a
node an in-flight worktree already wrote under it while the sidecar cannot
distinguish a discarded allocation from a pending one. `SKILL.md`'s mutation
rules carry the same core rule inside the 16,000-byte `test_core_stays_concise`
bound (14,151 -> 14,319 bytes), and `src/tangle/help.py` states the burn on
`tangle allocate`'s help.

The read-only answer is a new `tangle reservations` verb, routed in
`src/tangle/main.py` and implemented in the new
`src/tangle/reservations.py`. It prints
`reservations[N]{prefix,next,burned}` rows, where `burned` is the compact set of
ids below `next` with no node file on disk (for example `"TAS","5","1-3"`), so a
groomer can tell a reserved-but-unwritten id from a missing node; with no
allocations it prints `reservations: 0 prefixes` and exits `0`.

Option A — extending `tangle status` in `src/tangle/cli.py` with the same
column — was rejected because `src/tangle/cli.py` is one of the seven
`src/tangle/*.py` paths embedded as observable prompt content in
`benchmark/memory-authority-cases.json`, so any byte change to it fails
`tests/test_memory_authority.py::test_verify_reports_missing_artifact_or_passes`
(`authority artifact differs from a re-derivation`) in the default `make test`.
Offline `tangle benchmark authority record --input` cannot rebase the frozen
live measurement: the new prompt digests differ, so it regenerates
`status: "incomplete"`, `decision: "untested"`, and 12 incomplete reasons,
degrading the committed `keep-existing-evidence` result, and a faithful
re-record needs a live paid run, out of scope for this slice. The new verb
reaches the same read-only answer without touching any observable path, so the
committed authority artifact stays valid; regeneration ownership is
[[TAS-144-derived-artifact-regeneration-ownership]].

Releasing or reclaiming an unused allocation is explicitly disposed: the
contract states there is no release or reclaim, because a reused id could
collide with a node an in-flight worktree already wrote under it and the sidecar
cannot tell a discarded allocation from a pending one, so the burn is permanent.

Tests: `tests/test_tangle_foundation.py` adds
`test_reservations_lists_burned_ids_apart_from_missing_nodes` (four allocations,
three discarded and one written, so the listing shows `"TAS","5","1-3"` —
burned 001-003, the node 004, and next 005) and
`test_reservations_takes_no_arguments_and_reports_none_when_uninitialized`
(`reservations: 0 prefixes` and exit `0` before any allocation, and a stray
argument exits `2`). `tests/test_skill.py` pins the contract in
`_ALLOCATION_BURN_RULE` (coordination) and `_ALLOCATION_BURN_CORE_RULE` (core),
and its falsification probe `_ALLOCATION_BURN_SIGNAL_ONLY` feeds the pre-change
allocate bullet — which already named the reservation but stated no burn,
visibility, or reclaim rule — through the same `_assert_contains` guard in
`test_allocation_burn_guard_rejects_the_reservation_signal_alone`, so the test
fails when the guard stops detecting the rule rather than passing vacuously.

Evidence: `uv run pytest -q tests/test_tangle_foundation.py` -> 24 passed;
`uv run pytest -q tests/test_skill.py` -> 78 passed;
`uv run pytest -q tests/test_memory_authority.py` -> 22 passed;
`uv run ruff check` -> all checks passed; `uv run mypy` -> no issues in 73
source files; `tangle check` -> `graph check: passed (196 nodes)`;
`make test` -> 669 passed, 3 skipped, 79 deselected. `git status --porcelain` on
`benchmark/` and the seven observable `src/tangle/` paths (`cli.py`,
`sidecar.py`, `toon.py`, `vault.py`, `revision.py`, `quality_benchmark.py`,
`staged_benchmark.py`) is empty, confirming the authority artifact and every
observable prompt file are untouched. No node pins this node and it pins no
context-bearing dependency, so `context_rev` stays `1`. Parent
[[TAS-137-usage-feedback-hardening-round-seven]] named this node in the write
set, so this change advanced its `next` to
[[TAS-141-next-and-pin-search-diagnostics]] with the parent's `updated`
refreshed and its `context_rev` unchanged.
