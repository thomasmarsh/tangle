---
context_rev: 1
priority: P3
updated: 2026-09-12T12:40:14Z
summary: Disambiguate the bt stale zero result and make the status-directory contract explicit and consistent.
next: Reword the bt stale zero line and decide how proposed, active, and blocked directories are created and validated.
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
