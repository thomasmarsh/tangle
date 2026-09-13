# Dependencies reference

Load this before pinning or gating a dependency, bumping `context_rev`, making a
staged-staleness commit, or reversing or superseding an outcome. It is the
canonical Markdown source that `braintree help dependencies` prints, and it is
installed beside `SKILL.md` at the same revision as the `braintree` command.

## Pins, gates, and staleness

Pin context-bearing dependencies only: `Depends on [[DEF-auth-protocol]] at
context_rev 7.` The pin must terminate its line; trailing text after
`at context_rev N.` is invalid. Do not pin navigation links. A node is `Stale`
when a dependency is missing, its current `context_rev` differs from the pin, or
the link lacks a pin; do not add `stale` to status or frontmatter. A semantic
change leaves dependents' pins unchanged so one exact backlink search finds the
reconciliation work.

Confirm each pinned dependency is `resolved` before executing; resolution does
not change `context_rev`, so completion is detected from the status directory. A
dependency whose target is not yet `resolved` has no consumable context to pin:
record it as a gate instead of a context edge, `Gated on
[[DEF-auth-protocol]].` in `# Context`, leaving the node `proposed` until it can
execute, and never pin the gate. Find every gate on a target with the
line-anchored `rg -n '^Gated on \[\[DEF-auth-protocol\]\]\.' .braintree`, and every
pin with `rg -n '^Depends on \[\[[^]]+\]\] at context_rev [0-9]+\.' .braintree`.
The `^` anchor matches an authored pin or gate line, not the command text where a
node or this reference quotes it, so a zero-consumer reading needs no inspection;
an unanchored `-F` search for the command text self-matches the quote and forces
one. Replace the gate with the pinned `Depends on` edge once the target resolves.

`braintree check` reports a pinned dependency whose target is `proposed`,
`active`, or `blocked`, and `--allow-stale` does not relax that check because it
only relaxes the revision equality. A pinned edge to a target that is not
resolved and an unpinned context edge both name the gate form in their
diagnostic.

## The bump commit shape

Commit the semantic `context_rev` bump with the bumped node alone, leaving
pinned consumers stale on purpose so the exact backlink search finds them. That
commit runs the sanctioned staged-staleness gate
`braintree check --allow-stale`, which still rejects a missing or malformed
pin and relaxes only the revision equality; plain `braintree check`
remains the normal gate everywhere else.

Reconciliation is separate work owned by each consumer: reread the dependency,
update assumptions, reset the pin to the current `context_rev`, and pass the
plain gate before that consumer executes. `--allow-stale` is sanctioned only for
a deliberate staged-staleness commit: never use it to silence a pin you can
reconcile now, and never leave a consumer stale across its own execution.

## Reversal and supersession

Reversing a partly implemented outcome is an in-place update while the same node
and scope still own it: rewrite the outcome in the same node, and bump
`context_rev` because a pinned consumer must reread the changed direction.

Supersede only when the outcome moves to a different node: move to `resolved`,
set `disposition: superseded`, record the replacement as `Superseded by [[...]]`
in the body, and search remaining backlinks. Deprecation follows the same
resolved-node shape with `disposition: deprecated` and a note on why the outcome
is retired.

A reversal records the commit that named the reversed direction — short SHA and
subject — in the node's body, with whether that commit's change was kept,
reverted, or replaced. Record the reversal in the node and a new commit; never
rewrite, amend, or force-push the earlier commit.
