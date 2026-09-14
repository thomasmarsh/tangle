---
status: resolved
context_rev: 1
priority: P3
updated: 2026-09-14T23:40:13Z
summary: bt stale names stale pins in its zero result and SKILL.md states that status directories are created on demand.
---

# Context

Parent [[TAS-044-usage-feedback-hardening]].

Feedback finding F8 (low): `bt stale` prints `stale: 0 dependency pins`, which
reads as either zero stale pins or zero pins total; `SKILL.md` lists a
`blocked/` status directory that no command creates or validates; and the
node-count agreement between `graph-check` and `bt reindex` is a note, not a
defect.

# Outcome

The `bt stale` zero result cannot be misread, the vault's status-directory set
is created or validated consistently with `SKILL.md`, and the node-count note is
dispositioned.

# Done when

- The zero result names stale pins explicitly, with a test that pins the
  message.
- Either the tooling creates and validates every documented status directory,
  or the documentation states that directories appear on demand.
- `make test` passes.

# Result

`bt stale` now prints `stale: 0 stale dependency pins`, so a zero result cannot
be read as zero pins total. `SKILL.md` states that the four status-directory
names are fixed but each directory is created on demand and no empty directory
is required, so the tooling need not create `blocked/`. The node-count agreement
between `graph-check` and `bt reindex` was confirmed to be expected behavior and
is not a defect.

Evidence:

- `test_stale_without_stale_pins_names_them` pins the exact zero message.
- `SKILL.md` vault-contract section states the on-demand directory rule.
- `make test` passes.
