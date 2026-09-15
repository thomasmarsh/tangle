---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: A consuming project records a struggle or suggested improvement in one documented step that yields a valid feedback node.
---

# Context

Parent [[TAS-054-feedback-mechanism]].

Depends on [[TAS-052-install-revision-stamp]] at context_rev 2.

# Outcome

A user of an installed Tangle records a struggle or suggested improvement
through one documented step, and the result is a valid, routed feedback node
that names the Tangle revision in use.

# Done when

- `SKILL.md` documents a template or command that creates a valid feedback node
  with minimal user input.
- The recorded node carries the Tangle revision from the installed record
  when it is available and degrades explicitly when it is not.
- The path works from the installed skill in a consuming project, not only from
  this source repository.
- A test creates feedback through the documented path and confirms
  `graph-check` accepts the result.

# Result

`feedback-record` is the recording half of the feedback mechanism. Run from a
consuming project's vault root, it allocates the next `FBK` id from Markdown,
discovers a primary route to the vault's root hub from `index-map.md`, reads
the installed revision record, and writes
`nodes/proposed/FBK-<n>-<slug>.md` from the required `--attempted`,
`--friction`, and `--improvement` values. `--route` overrides the discovered
route, `--id`, `--summary`, and `--slug` override the allocated id and derived
fields, and `--nodes` selects a `nodes/` directory other than the current one.
The revision is the installed `installed-revision` record; without one the
command stamps `<version>+unknown`, so the node always names the Tangle
version and states the revision explicitly. A recorded node is a valid, routed
`FBK` node that passes `graph-check`.

Evidence:

- `src/tangle/feedback_record.py` implements the writer and
  `revision.feedback_revision()` resolves the record or the explicit
  `<version>+unknown` fallback; `pyproject.toml` declares the `feedback-record`
  console script and `scripts/feedback-record` keeps the in-repo entry point.
- `tests/test_feedback_record.py` covers auto-routing, explicit
  id/route/summary/slug, next-id allocation, revision stamping, the missing
  route and content errors, and a recorded node passing `graph-check`;
  `tests/test_revision.py` covers the degraded revision.
- `tests/test_skill.py` pins the recording contract; `tests/install.sh` runs
  the installed `feedback-record` in a consuming vault and validates the result
  with the installed `graph-check`.
- `make test` passes.
