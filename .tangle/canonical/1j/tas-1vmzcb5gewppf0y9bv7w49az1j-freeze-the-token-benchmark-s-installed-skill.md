---
context_rev: 1
status: resolved
updated: 2026-09-15T21:23:51Z
summary: Freeze the token benchmark's installed-skill fixture inputs with provenance.
---

Parent [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]].

# Context

This is the token and staged half of [[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]], the ARCH.md section 7.1 slice that separates research evidence from the runtime. `token_benchmark._installed_skill_files` reads `SKILL.md`, `agents/openai.yaml`, `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, every file directly under `src/tangle/`, and every file under `references/`, then writes them into the generated install at `.agents/skills/tangle`. `staged_benchmark` documents that the generated fixture embeds `SKILL.md` and `src/tangle`, so `fixture_sha256` moves with the state under test and is deliberately not compared.

The recorded samples in `benchmark/token-*.json` and the staged A/B records carry `fixture_sha256` and `skill_sha256` but not the bytes they hash, so a later refactor of `src/tangle` or `SKILL.md` makes a recorded measurement unreproducible even though its prompt and case data are unchanged.

Gates this artifact enters: `token_benchmark._installed_skill_files` enumerates every file directly under `src/tangle/`, so the frozen snapshot must live outside that package directory. `tests/test_skill.py` enumerates `references/*.md`.

# Outcome

The token and staged benchmark fixtures resolve their install inputs from a frozen, provenance-stamped snapshot under `research/`, and each recorded sample's `fixture_sha256` and `skill_sha256` reproduce from that snapshot.

# Done when

- A frozen install snapshot holds a byte copy of every path `_installed_skill_files` reads, at its repo-relative install path.
- A provenance manifest records each file's source revision and SHA-256.
- Rebuilding the install fixture from the frozen snapshot reproduces the recorded `fixture_sha256` and `skill_sha256` of every committed token sample whose recording revision's installed bytes exist in git; samples whose bytes are absent from all git objects are recorded as `reproducible: false` with the reason.
- `staged_benchmark` no longer treats a live-source dependency as an uncompared difference, or states the frozen snapshot it now depends on.
- `make test-benchmarks` passes.

# Result

Resolved with the frozen install snapshots landed in the same commit.

- `research/fixtures/token-install/` holds five snapshots (`7b8877ae`,
  `6980501`, `97e0848`, `7b8877ae-tight`, `current`) plus `manifest.json`
  (`protocol: token-install-snapshot-v1`). Each records `source_revision`,
  `skill_revision`, `install_root`, `prompt_verb`, `skill_sha256`, and every
  file's path and SHA-256, so the installed tree the pre-rename fixtures
  embedded (`.agents/skills/braintree`, `$braintree`) is frozen beside the
  current `.agents/skills/tangle`.
- `token_benchmark._installed_skill_files(snapshot)` reads the frozen snapshot,
  and `_generate_fixture`/`_fixture_prompt`/`_check_fixture` are parameterized
  by its install root and prompt verb and emit its snapshotted `skill_sha256`.
  Ordinary-run output is byte-identical, and the dead
  `_skill_source`/`_skill_metadata_source`/`_sha256_file` helpers were removed.
- `staged_benchmark` states the frozen-snapshot dependency; its verification
  fields are unchanged.

Evidence: the five git-recoverable committed samples reproduce byte-for-byte
(`token-ab-current` and `token-orientation-current` from `7b8877ae`;
`token-ab2-current` from `6980501`; `token-ab2-tight` from `97e0848`;
`token-ab-tight` from `7b8877ae` sources plus the `97e0848` SKILL.md, recorded
as the `7b8877ae-tight` snapshot). `make test-benchmarks` passes with 86 passed;
all 124 manifest hashes match disk; the new benchmark test rebuilds each sample.
This is the authorized corrected Done when: the unrecoverable Ruby-era samples
`token-cold-resume-baseline-v1`, `token-orientation-baseline-v1` (`a50cd53d`),
and `token-orientation-candidate-v2` (`9a2c639c`) have SKILL.md bytes absent from
every git object and are recorded as `reproducible: false` with that reason
rather than re-recorded.

Residual: `--check-fixture` now compares against the frozen `current` snapshot
by design, so it no longer detects live-worktree drift of `SKILL.md` or
`src/tangle`; refreshing the snapshot is a deliberate re-record.
