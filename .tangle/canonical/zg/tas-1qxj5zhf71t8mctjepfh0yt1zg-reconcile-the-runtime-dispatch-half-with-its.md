---
context_rev: 1
status: proposed
updated: 2026-09-15T20:42:41Z
summary: Reconcile the runtime-dispatch half with its existing owner.
next: Confirm the benchmark-isolation owner covers this node's dispatch requirement and record the delegation marker in the parent.
---

Parent [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]].

# Context

Gated on [[tas-3h6n5kky4qzdryvkwe1rxg1hx6-isolate-benchmark-and-memory-evaluation]].

This is the reconciliation half of [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]]. That node separates ARCH.md section 7.1 into two moves. The runtime-dispatch move, keeping ordinary startup from importing benchmark and memory-evaluation modules, is already owned by the gated target, which makes `main.py`'s benchmark and `memory_*` imports lazy and proves it with a negative assertion. The fixture move is owned by this node's two sibling children.

The parent's `# Done when` accepts either the dispatch modules being loaded lazily or that half being resolved through its existing owner and cited in the parent. The parent already cites the owner; what remains is to confirm the owner's scope covers every eager import the parent cares about and to leave one durable marker of the delegation so no worker re-implements dispatch isolation here.

# Outcome

The runtime-dispatch requirement is recorded as delegated to its existing owner, the delegation is asserted against the owner's evidence, and no duplicate isolation work remains under this parent.

# Done when

- The gated target's `# Done when` is confirmed to cover every eager benchmark and `memory_*` import the parent's `# Context` names, or the gap is reported and the parent's scope is corrected.
- The parent's `# Context` records the delegation marker, and clearing it once the target resolves is the parent's integration step.
- `tangle check` passes.
