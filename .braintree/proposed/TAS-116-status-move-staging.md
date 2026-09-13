---
context_rev: 1
priority: P2
updated: 2026-09-13T02:14:00Z
summary: State that a node's status move and its body edit are staged in one commit, because `git mv` can stage the pre-edit blob.
next: Add the status-move staging rule to the contract and pin it.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-012` at `0.5.0+g7b95875` and its recurrence Tangle `FBK-013`, both
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
