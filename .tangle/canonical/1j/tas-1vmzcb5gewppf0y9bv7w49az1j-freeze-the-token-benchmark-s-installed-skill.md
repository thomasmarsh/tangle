---
context_rev: 1
status: proposed
updated: 2026-09-15T20:42:41Z
summary: Freeze the token benchmark's installed-skill fixture inputs with provenance.
next: Extract the inputs token_benchmark._installed_skill_files reads into a frozen install snapshot with a per-file provenance manifest.
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
- Rebuilding the install fixture from the frozen snapshot reproduces the recorded `fixture_sha256` and `skill_sha256` of every committed token and staged sample that names one.
- `staged_benchmark` no longer treats a live-source dependency as an uncompared difference, or states the frozen snapshot it now depends on.
- `make test-benchmarks` passes.
