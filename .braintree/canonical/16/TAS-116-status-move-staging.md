---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State that a node's status move and its body edit are staged in one commit, because `git mv` can stage the pre-edit blob.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Hekate `FBK-012` at `0.5.0+g7b95875` and its recurrence Hekate `FBK-013`, both
verified in [[THO-017-round-six-usage-feedback-analysis]]. Resolving a node by
editing the body, then `git mv`-ing it `nodes/active/` to `nodes/resolved/`,
then committing recorded the rename with the OLD body:
`git show HEAD:nodes/resolved/TAS-037-*.md | grep -c '^# Resolution'` printed
`0` while the worktree printed `1`, and `git status --short` showed
` M nodes/resolved/TAS-037-*.md`. The second instance ran across a two-commit
claim/resolution split, so the status move landed carrying the pre-edit blob in
the first commit. Neither `SKILL.md` nor `references/` mentions `git mv`, `git
add`, or staging; the status rule says only "Change status by moving the
unchanged filename between those directories". `FBK-013` is merged here because
it is the same finding and needs no separate acceptance.

# Outcome

The contract states that a status move and the node's body edit belong in the
same commit, and names the `git mv` trap, so a resolving or claim commit never
records a status change with a stale body.

# Done when

- `SKILL.md` states, next to "move the unchanged filename between status directories", that the status move and the `# Result`/`# Resolution` body edit belong in the same commit.
- `SKILL.md` states that `git mv` may stage the pre-edit blob, so the destination must be `git add`-ed after the move, and that the move should be the last step before committing that node.
- A contract test in `tests/test_skill.py` pins the stated rule.
- `make test` passes.

# Result

`SKILL.md`'s status rule now states the staging rule in one sentence: stage the
status move and the node's `# Result`/`# Resolution` body edit in the same
commit, because `git mv` can stage the pre-edit blob, so `git add` the
destination after the move and make the move the last step before committing
that node. `references/coordination.md` needed no change: it already requires
the content update and the status move in one coherent commit, and the always-
loaded core is the right home for the `git mv` hazard.

Evidence: `tests/test_skill.py` pins the rule with `_STATUS_MOVE_STAGING_RULE`;
removing the sentence from `SKILL.md` fails
`test_status_move_is_staged_with_its_body_edit`. This resolution commit itself
demonstrates the rule: `git show HEAD:.braintree/resolved/TAS-116-status-move-staging.md`
carries the `# Result` body edit, so the move never records a stale blob.
`make test` and `braintree check` pass.
