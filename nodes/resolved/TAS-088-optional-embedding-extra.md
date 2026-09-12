---
context_rev: 1
priority: P1
updated: 2026-09-12T17:38:06Z
summary: Declare the embedding runtime and clustering libraries as an opt-in extra and an offline model cache, leaving the default install dependency-free.
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

# Result

`[project].dependencies` is still `[]`; the heavy libraries live only in
`[project.optional-dependencies] semantic`, resolved into `uv.lock` with
`uv add --optional semantic --no-sync` so the development environment stays a
plain install. Lower bounds: `numpy>=2.0`, `scikit-learn>=1.5`,
`sentence-transformers>=3.0`, `torch>=2.4` for the CPU inference path, plus the
recorded package choices `umap-learn>=0.5.6` for UMAP and `hdbscan>=0.8.38` for
HDBSCAN. `README.md` documents the install commands
(`uv sync --extra semantic`, `pip install 'braintree[semantic]'`), the extra's
contents, and the offline cache.

`semantic.extra()` is the capability probe: it reads `importlib.util.find_spec`
for each extra module and returns `None` when any is missing, so it never
imports torch or another heavy module and a plain install still answers every
command unchanged. `semantic.model_cache()` resolves the documented offline
weights directory from `BT_MODEL_CACHE`, else `HF_HOME`, else
`~/.cache/huggingface`, under `hub`; nothing downloads at query time.

Evidence: `tests/test_semantic.py` drives `--help`, `check nodes`, `frontier`,
and `similar` through the installed entry point in a fresh interpreter with no
provider and asserts none of the six heavy modules is in `sys.modules`;
stand-in modules on the path prove the probe locates the extra without
importing it; one missing module reports the extra absent; and the cache
resolves from `BT_MODEL_CACHE`, then `HF_HOME`. `braintree check nodes`,
`braintree index nodes`, and `make test` pass. Resolving this node advanced the
parent's `next` to [[TAS-089-embedding-model-selection]].
