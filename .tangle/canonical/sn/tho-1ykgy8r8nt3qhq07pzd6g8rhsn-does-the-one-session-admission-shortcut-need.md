---
context_rev: 1
status: proposed
updated: 2026-09-15T14:36:52Z
summary: Does the one-session admission shortcut need duration-independent refinement?
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Question

SKILL.md's admission section reads: "work planned to be committed and finished within one session needs no node, because Git already records it." ASTRA.md argues session duration does not determine future value -- a ten-minute decision may constrain months of work, and a commit message is a poor place to rediscover it -- and proposes replacing the shortcut with: keep unfinished executable state, decisions that constrain future work, and discoveries whose loss would cause meaningful repetition or error; prefer updating the existing owner; let Git carry routine implementation history.

Does this graph adopt that reframing, and if so, does the existing admission threshold sentence ("Admit a node only when its conclusion or executable state is likely to change a future decision or action") already subsume it, or does the one-session shortcut need to be struck or qualified so an agent does not read it as an independent license to skip admission for a fast but consequential decision?

# Context

Related: [[THO-029-pre-dispatch-boundary-evidence]] already rejected duration as pre-dispatch split evidence for a different question (whether several named outcomes justify splitting before dispatch). This question is about admission -- whether to create a node at all -- not decomposition boundary.
