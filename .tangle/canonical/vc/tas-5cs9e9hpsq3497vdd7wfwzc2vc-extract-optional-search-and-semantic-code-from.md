---
context_rev: 1
status: proposed
updated: 2026-09-16T00:15:58Z
summary: Extract optional search and semantic code from the core package.
next: Inventory the search and semantic import graph, packaging boundary, and core fallbacks.
---

Parent [[tas-4v7q7qyfyt4kv9sx08sayef4rs-compose-views-and-opt-into-optional-layers]].

# Context

ARCH.md section 6 places optional search outside the small core under `extras/search/`. The current package still colocates `clustering.py`, `provider.py`, `reduction.py`, and `semantic.py` with ordinary graph execution. The existing capability decision ensures optional behavior, but the graph did not require the corresponding physical source and distribution boundary.

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

The research extraction node owns benchmark runners such as `embedding_benchmark.py`; this node owns reusable optional search and semantic implementation. Gates my artifact enters: optional-dependency and package declarations in `pyproject.toml`, installer and scaffold coverage, the clustering/provider/reduction/semantic tests, default ruff/mypy/pytest discovery, and benchmark consumers of the optional layer.

# Outcome

Search, embedding-provider, reduction, clustering, and semantic-retrieval implementation lives outside the core `tangle` package behind an explicit optional installation and capability boundary; installing and running the core does not install or import it, and core answers are unchanged when it is absent.

# Done when

- An inventory records the optional search modules, their core-facing interface, their benchmark consumers, and the disposition of every related module currently under `src/tangle/`.
- Optional implementation is moved to the selected `extras/search` package boundary, with no core-to-extra import except through the explicit capability adapter.
- The default installation excludes optional implementation and dependencies; an installation with the search extra exposes the supported commands and behavior.
- Tests falsifiably prove core commands and answers work without the extra, mixed-capability behavior is explicit, and semantic state remains derived, disposable, and non-authoritative.
- Obsolete forwarding modules are removed unless a time-bounded compatibility requirement is recorded.
- `tangle check`, `make test`, and the implicated semantic and benchmark gates pass.

# Scoping

This is independently acceptable from research-runner extraction because it has a separate installation boundary, capability contract, fallback behavior, and rollback surface. Execute it in slices on this node unless evidence reveals another independently consumable outcome.
