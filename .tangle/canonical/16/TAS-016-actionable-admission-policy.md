---
status: resolved
context_rev: 2
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Established actionable-only admission and low-friction update-or-create rules.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Outcome

The graph retains information that supports future action without becoming a transcript or an everything log.

# Done when

The contract names actionable admission criteria, explicit exclusions, and a low-friction way to record useful knowledge, decisions, bugs, debt, and future features.

# Result

The skill admits durable knowledge, architectural or operational decisions, executable tasks, bugs, debt, blockers, and future features only when they change a future decision or action. It rejects transcripts, tool-call logs, routine narration or status, duplicate source material, and inert observations. The same-thread update rule and just-in-time split boundary are documented and contract-tested.
