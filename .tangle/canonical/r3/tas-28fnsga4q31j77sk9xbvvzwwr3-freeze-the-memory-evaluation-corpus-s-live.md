---
context_rev: 1
status: resolved
updated: 2026-09-15T21:14:16Z
summary: Freeze the memory-evaluation corpus's live observable inputs with provenance.
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
- `tangle benchmark authority verify`, `tangle benchmark corpus verify`, and `memory_causal.verify()` pass against the frozen fixtures with no live checkout read.
- `make test` passes.

# Result

Resolved with the frozen-fixture slice landed in the same commit.

- `research/fixtures/memory-eval/` holds `checkout/` (34 byte copies at their
  repo-relative paths) and `provenance.json` (`source_revision`
  `ce07e35dec95`; per-file path, revision, and SHA-256; the 41
  `.tangle/<status>/<name>.md` references recorded as live-vault, by-name
  resolution).
- `src/tangle/memory_corpus.py` owns the single frozen resolver
  `_resolve_observable_path`: `.tangle/<status>/<name>` resolves live through
  `store.find_by_name` (so `path_exists` and `leakage` audit those two
  observables instead of skipping them), and every other path resolves to the
  frozen copy. `memory_pilot._resolve_observable`,
  `memory_authority._path_exists`/`leakage`, and `memory_causal` reuse it, and
  `resolved_path` is unchanged, so the `prompt_digest`/`fixture_digest`
  formulas stay byte-identical.
- `[tool.ruff] extend-exclude = ["research/fixtures"]` keeps the frozen bytes
  out of lint scope.

Evidence: `tangle benchmark corpus verify` and `tangle benchmark authority
verify` report `verification: passed`; `memory_causal.verify()` returns `[]`;
the focused memory suites pass (126, then 90 after the leak-audit fix); `make
test` is green with 850 passed and 3 skipped; all 34 provenance SHA-256 values
match disk.

Authorized factual correction: the committed measurements do **not** re-derive
from the frozen fixtures. The decisive probe compared every committed per-sample
`prompt_digest` against the re-derived plan: authority 0/144 and causal 0/540
match, and `memory_authority.verify`, `result_problems`, and
`memory_causal.verify()` do not detect the drift. The frozen copies are
byte-identical to `ce07e35` and the same mismatch exists at HEAD, so it is real
prompt/harness drift and not an effect of the freeze. Reproducing those
historical measurements would require the historical bytes and prompt revision,
which do not reproduce. With coordinator authorization the reproduction bullet
is narrowed to "verification passes and re-derivation reads no live source",
and the committed artifacts stay retained as historical evidence.

Residuals: `.tangle` observables still resolve live, so vault edits remain a
digest input (documented in `provenance.json`); `memory_causal.verify()` checks
only module literals; the manifest records but does not enforce each hash; and
`source_revision` is the freeze revision, not the historical measurement
revision.
