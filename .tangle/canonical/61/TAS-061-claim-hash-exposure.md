---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: tangle hash NODE prints the claim base hash, the SHA-256 of the node's raw UTF-8 bytes, so SKILL.md names the algorithm and no worker infers it.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R3 from Hekate `THO-005-braintree-friction-kitty-spike` F1:
`SKILL.md` requires hashing the starting node for `tangle claim`, but names no
algorithm, and no `tangle` read command exposes a content hash, so a worker must
read the Python or guess.

# Outcome

The skill names the exact hash (SHA-256 hex of the raw UTF-8 file bytes,
including frontmatter), and `tangle` exposes the value the claim compares against.

# Done when

- `SKILL.md` documents the base-hash algorithm in the hybrid-sidecar section.
- `tangle hash NODE` (or a hash field in `tangle search`/`tangle status`) returns the same value the sidecar records.
- A regression test pins the documented algorithm to the sidecar's `sha256(text)`.
- `make test` passes.

# Result

Took the `tangle hash` branch. `sidecar.content_hash` is the single canonical
algorithm: the SHA-256 hex digest of the bytes it is given, which the index
stores and `tangle claim` records. `index.node_hash` resolves a bare ID or full
node name and returns that digest for the file's raw bytes, frontmatter
included, reading Markdown alone so it needs no sidecar. `tangle hash NODE` prints
`node` and `content_hash` and fails with `unknown node` and exit `1` otherwise.
`index._read_index_rows` now feeds the same bytes it decodes into
`content_hash`, so the stored `content_hash` column and `tangle hash` cannot
diverge.

Evidence:

- `SKILL.md` hybrid-sidecar section defines the base hash as the SHA-256 hex of
  the node file's raw UTF-8 bytes, frontmatter included, and says to get it
  from `tangle hash`; the parallel-worktree section points the worker at `tangle hash`.
- `tangle hash TAS-061` matches `shasum -a 256` on the file and the `base_hash`
  recorded by this worker's `tangle claim`.
- `test_hash_matches_raw_sha256_algorithm` pins `tangle hash` output to
  `hashlib.sha256(node_file.read_bytes()).hexdigest()` and covers full-name
  resolution and the unknown-node error.
- `tests/tangle-index.sh` cross-checks `tangle hash` against `shasum` in the shell suite.
- `test_skill_frontmatter_and_hybrid_contract`, `test_skill_admission_and_parallel_contract`,
  and `test_tangle_help_lists_every_command` assert the documented contract and command.
- `make test` passes.
