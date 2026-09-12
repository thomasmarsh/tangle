---
context_rev: 1
priority: P1
updated: 2026-09-12T17:22:00Z
summary: Declare the embedding runtime and clustering libraries as an opt-in extra and an offline model cache, leaving the default install dependency-free.
next: Declare the optional extra and document the offline model cache.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

`pyproject.toml` currently has `dependencies = []`, and
[[DEF-001-distribution-contract]] keeps installation portable, offline, and
free of required runtime dependencies. A native embedding provider needs
inference and clustering libraries and pre-fetched model weights, so those must
stay opt-in rather than become default dependencies.

# Outcome

An optional extra installs the inference runtime, the manifold and clustering
libraries, and a documented local model cache, while a plain install of the
package is byte-for-byte unchanged and still imports no third-party module.

# Done when

- `pyproject.toml` declares the extra without adding anything to
  `dependencies`, and the extra is documented with its install command.
- The runtime and clustering libraries are named with pinned lower bounds, and
  the chosen package for HDBSCAN and UMAP is recorded.
- Model weights live in a documented local cache that inference reads offline;
  no command downloads at query time.
- A test proves the default install imports and runs without the extra, and the
  capability probe reports the capability absent when the extra is missing.
- `make test` passes.
