---
context_rev: 1
status: proposed
updated: 2026-09-14T22:58:32Z
summary: Model workflow migrations as explicit milestones.
next: Define milestone and roll-up conventions for compatibility migrations.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

Cross-cutting compatibility migrations expose ordered reader, writer, dry-run, apply/recovery, and benchmark milestones.

# Done when

- The convention prevents a broad task from leaving its next implementation slice ambiguous.
- It distinguishes independently acceptable milestones from ordinary implementation steps.
- A representative migration is decomposed and validated with the convention.
