---
context_rev: 1
status: resolved
updated: 2026-09-15T02:47:49Z
summary: Model workflow migrations as explicit milestones.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

Cross-cutting compatibility migrations expose ordered reader, writer, dry-run, apply/recovery, and benchmark milestones.

# Done when

- The convention prevents a broad task from leaving its next implementation slice ambiguous.
- It distinguishes independently acceptable milestones from ordinary implementation steps.
- A representative migration is decomposed and validated with the convention.

# Result

Added the milestone convention to the authoring reference and a one-sentence
core restatement in `SKILL.md`, pinned by `tests/test_skill.py` with a
falsification probe. The convention holds that a cross-cutting compatibility
migration — old and new readers and writers working simultaneously — exposes an
ordered set of independently acceptable milestones, and a broad migration task
must name them so its `next` never leaves the first implementation slice
ambiguous.

Validated the convention against
[[TAS-203-stable-lowercase-node-project-identity]] as the representative
migration without reopening the resolved node. Its recorded slices map onto
the milestone order: the identity foundation plus the compatibility-reader
slice form the reader-compatibility milestone (legacy uppercase numeric
readers and new lowercase canonical readers resolve together); the
stationary-writer slice is the writer milestone (capture, feedback capture,
and decomposition write the canonical layout while legacy readers stay green);
the explicit compatibility-migration/apply slice is the dry-run planning plus
apply/recovery milestone (plan by default, whole-vault rejection before any
write, and byte-for-byte journal restore on a failed apply); and the
storage-comparison benchmark slice is the benchmark-evidence milestone. Each
slice carried its own acceptance and verification, left the prior surface
green, and was accepted, resumed, and consumed on its own, so the convention
describes that migration faithfully.
