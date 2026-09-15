---
context_rev: 1
status: proposed
updated: 2026-09-15T20:42:41Z
summary: Freeze the memory-evaluation corpus's live observable inputs with provenance.
next: Inventory every live checkout path the memory corpora observe, copy each under a frozen research/ fixture root, and record source revision and SHA-256.
---

Parent [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]].

# Context

This is the memory-evaluation half of [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]], the ARCH.md section 7.1 slice that separates research evidence from the runtime. `memory_pilot._resolve_observable` reads every `query.observable_paths` and episode `evidence` path from the live checkout, and `memory_authority`, `memory_causal`, and `memory_corpus` all reuse that resolver, so the committed `benchmark/memory-*-result.json` evidence is bound to the current source layout rather than to the revision it measured.

The live checkout inputs named by `benchmark/memory-authority-cases.json` and `benchmark/memory-corpus/*.json` are `SKILL.md`, `AGENTS.md`, `pyproject.toml`, `references/*.md`, `research/agent-memory-*.md`, `src/tangle/*.py`, and `tests/test_*.py`. The corpora also name `.tangle/<status>/<node>.md` references, which the resolver reads through the live store.

Gates this artifact enters: `memory_corpus.load_documents` enumerates every `benchmark/memory-corpus/*.json` and rejects an unexpected file, so the provenance manifest must not be a `.json` under that directory. `token_benchmark._installed_skill_files` enumerates every file directly under `src/tangle/`, so the frozen copies must not be placed there. `tests/test_skill.py` enumerates `references/*.md`.

# Outcome

Every live checkout input the memory-evaluation corpora observe is copied into a frozen fixture root under `research/` with recorded provenance, the resolver reads the frozen copy, and the committed measurements re-derive without reading live source.

# Done when

- A frozen fixture root holds a byte copy of every live checkout path named by the authority cases and the memory-corpus envelopes, at its repo-relative path.
- A provenance manifest records each copied file's source revision and SHA-256, and states how the `.tangle/<status>` node references are resolved.
- `memory_pilot._resolve_observable` and each consumer read the frozen copy for checkout paths while the corpus validators still pass.
- `tangle benchmark authority verify` and the memory-causal and memory-corpus verification reproduce the committed results against the frozen fixtures with no live checkout read.
- `make test` passes.
