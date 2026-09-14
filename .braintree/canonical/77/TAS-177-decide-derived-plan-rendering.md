---
status: blocked
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Decide whether Braintree should render conventional long-form plans.
next: Answer the audience, format, history, and storage questions for plan rendering.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-171-pilot-incremental-plan-intake]].

Rendering is optional and one-way. Its purpose is to serve humans and LLM workflows that prefer a cohesive long plan without introducing another editable authority.

# Outcome

A settled decision either defines a derived plan view and its consumers or disposes the renderer branch.

# Done when

- The decision names the audiences and tasks that require a long-form view instead of existing exact graph queries.
- It defines included goals, narrative, current frontier, sequenced proposed work, decisions, dependencies, completed outcomes, and deferred or disposed branches.
- It chooses output format, ordering, history depth, token or size bounds, and customization boundary.
- It decides whether output is ephemeral, cached, or committed and defines invalidation by complete input hashes.
- Every rendering carries a generated marker and cannot be reconciled back into graph authority.
- If no renderer is justified, [[TAS-178-build-derived-plan-renderer]] is explicitly disposed.

# Blocked

Blocked by: project-owner choices about consumers and the desired conventional-plan experience.

Questions for the project owner:

1. Who needs the rendered plan: humans, generic LLMs, external tools, reviews, or all of them?
2. Is Markdown the only required format, or are JSON, TOON, HTML, or other projections needed?
3. Should the rendering be ephemeral, cached outside Git, or checked in as a generated artifact?
4. How much resolved history, rationale, speculative work, and disposed work should it include?
5. Should users choose sections and ordering, or should one deterministic form be canonical?
6. What size or token bounds must a massive rendered plan respect?
7. Is the existing graph query surface sufficient, making this branch unnecessary?

Unblocks when: the owner identifies the consumers and answers the format, storage, content, and bound questions.
