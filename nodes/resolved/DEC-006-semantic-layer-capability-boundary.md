---
context_rev: 1
updated: 2026-09-12T15:09:27Z
summary: If semantic retrieval is added, it is optional, derived, rebuildable, and never authoritative; core answers are identical without it.
---

# Decision

Parent [[TAS-068-direct-answer-surface]].

Any semantic retrieval, ranking, or near-duplicate feature is optional,
derived, rebuildable, and never authoritative. It lives behind a capability
boundary: the command is probed, its state lives in the disposable sidecar keyed
by content hash, and every core answer is identical when the capability is
absent. No model is a required dependency, and no semantic result overrides
Markdown.

# Rationale

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

The distribution contract keeps Braintree portable, offline, and free of
required runtime dependencies. A bundled model or inference runtime would break
that, and a required semantic index would make a derived cache load-bearing. The
existing sidecar already demonstrates the acceptable shape: optional, external,
rebuildable, and degrading to Markdown alone.

# Consequences

- The lexical baseline remains the default and the correctness reference.
- [[TAS-079-optional-semantic-retrieval]] must pass the same gates with and
  without a provider.
- A provider is never networked by default and never required.
- The capability is kept only if a token and round-trip comparison shows value,
  per [[TAS-078-round-trip-telemetry-and-gates]].
