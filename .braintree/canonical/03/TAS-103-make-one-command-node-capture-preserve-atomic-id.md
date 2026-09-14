---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Make one-command node capture preserve atomic ID allocation under parallel callers.
---

Area [[IDX-001-execution-graph]].

# Context

`braintree node record` and `braintree feedback record` derive the next ID from Markdown and use an exclusive create on the full filename. Two parallel callers with different slugs can therefore create distinct files with the same numeric ID. This bypasses the sidecar allocation rule established by [[TAS-023-parallel-id-allocation]].

# Outcome

The one-command record paths either reserve their automatically chosen IDs atomically or require and clearly document an ID preallocated with `braintree allocate` whenever concurrent creation is possible.

# Done when

- A concurrent different-slug regression test cannot create duplicate numeric IDs.
- `node record` and `feedback record` share one stated allocation contract.
- The portable no-sidecar path remains explicit if atomic allocation is unavailable.
- `make test` passes.

# Result

`braintree node record` and `braintree feedback record` now reserve the
automatically chosen id atomically before writing the node file, through one
shared primitive, `node_record.reserve_number`. The old path computed
`next_number` from Markdown and only non-clobbered the full filename with
`O_EXCL`, so two parallel callers with different slugs both kept the same number
and wrote `TAS-103-a.md` and `TAS-103-b.md`.

The shared contract: `reserve_number` takes the number only if it is not
already on disk or reserved. When the project's sidecar exists and the target
`nodes/` directory is inside the project's own worktree, it reserves through the
same atomic sidecar counter `braintree allocate PREFIX` uses, so the reservation
spans worktrees. Otherwise it falls back to a portable vault-local
`O_CREAT|O_EXCL` marker under `nodes/.braintree/reservations/`, which is
collision-safe for callers sharing that vault but does not span worktrees. The
sidecar scoping keeps an unrelated vault (for example the temp vault the install
screen records into) on its own numbering instead of a shared counter. A marker
is never released, so a failed writer wastes a number rather than allowing a
duplicate identity; the hidden directory is outside the checker's
status-directory scan. Both commands catch an allocation failure and report it
instead of silently falling through.

Evidence: a new concurrent regression test starts eight differently-slugged
`TAS` captures together behind a barrier and proves all succeed with distinct
numeric ids; sidecar tests prove the counter path advances the sidecar and
leaves no vault-local marker, that an external vault uses the fallback even when
the project sidecar is ahead, and that four concurrent records sharing an
initialized sidecar keep distinct ids. `make test` (ruff, mypy, pytest,
`install.sh`, `worktree-parallel.sh`) passes.
