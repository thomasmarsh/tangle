---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: SKILL.md and graph-check define the FBK feedback convention carrying tangle_revision and Attempted/Friction/Improvement content.
---

# Context

Parent [[TAS-054-feedback-mechanism]].

# Outcome

`SKILL.md` and `graph-check` agree on one way to mark a node as Tangle
feedback, so a script can find feedback in any vault without reading node bodies
or consulting a sidecar.

# Done when

- The convention fixes a discoverable marker or node type, the required content
  (what was attempted, the friction observed, and the suggested improvement),
  and the primary route that keeps a feedback node reachable.
- `graph-check` validates the convention and reports a clear error for a
  malformed feedback node.
- The convention carries the Tangle revision the feedback is about when one
  is recorded.
- `tests/test_skill.py` pins the contract strings and a validator test exercises
  a valid and an invalid feedback node.
- Discovery works from Markdown alone, with no sidecar, network, or write to the
  scanned vault.

# Result

The `FBK` type is the one feedback marker: `find nodes -name 'FBK-*.md'`
discovers feedback from Markdown alone, with no sidecar, network, or write.
`SKILL.md` gains a `## Feedback nodes` section defining the `FBK-<n>-<slug>.md`
name, one primary `Parent`/`Area` route, the `tangle_revision:` frontmatter
(`<version>+<revision>` or `unknown`), and the required `# Feedback` section with
`Attempted:`, `Friction:`, and `Improvement:` lines. `graph-check` treats `FBK`
as a knowledge type and rejects a feedback node that omits or malforms
`tangle_revision` or lacks the required `# Feedback` content.

Evidence:

- `src/tangle/graph_check.py` adds `_check_feedback` and the `FBK` knowledge
  type; error strings name the missing revision, the malformed value, the
  missing section, and the missing label.
- `tests/test_graph_check.py` exercises a valid node, the `unknown` revision, a
  missing revision, a malformed revision, missing content, and a missing
  section; `tests/test_skill.py` pins the `SKILL.md` contract strings.
- `tests/graph-check.sh` mirrors the valid and invalid cases.
- `make test` passes.
