---
context_rev: 1
status: proposed
updated: 2026-09-15T17:45:53Z
summary: Route the default resumption path through packet and shorten the skill.
next: Name tangle packet [NODE] as the default entry point in SKILL.md and README, then move displaced detail into the references.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

ASTRA.md sections 1 and 2 ask for a small operating loop and a packet-first
resumption path. The packet code work (tas-32btrf71jvz66am5pempkhqapy) makes the
command assemble the ready node manifest and answer a scoped node, but SKILL.md
still teaches the frontier-candidate route and never names packet, README never
mentions packet, and SKILL.md is 2,292 words / 15,511 bytes against the 16,000-byte
cap.

Gates this artifact enters: tests/test_skill.py (the SKILL.md byte cap, routing
literals, invariant literals, and rule-area headings), README assertions, and the
live-vault tests; make test is the final gate.

# Outcome

A fresh worker documented entry point is tangle packet [NODE], which returns the
intended action and required reads without reconstructing the route, and SKILL.md is
materially shorter while every locked invariant, routing rule, and topical reference
route still holds.

# Done when

- SKILL.md read/execute loop and README everyday-use section name tangle packet [NODE]
  as the default entry point, with frontier the fallback when several initiatives are
  active.
- SKILL.md is materially reduced toward the ASTRA section 1 operating-loop constraint;
  it stays under tests/test_skill.py::_CORE_SIZE_BOUND and every _CORE_INVARIANTS,
  _CORE_ROUTING, and _CORE_RULE_AREAS literal still passes.
- Displaced detail moves into the topical references (coordination, dependencies,
  authoring) rather than being deleted.
- tangle check and make test pass.
