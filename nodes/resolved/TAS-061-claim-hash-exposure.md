---
context_rev: 1
priority: P2
updated: 2026-09-12T14:10:07Z
summary: bt hash NODE prints the claim base hash, the SHA-256 of the node's raw UTF-8 bytes, so SKILL.md names the algorithm and no worker infers it.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R3 from Tangle `THO-005-braintree-friction-kitty-spike` F1:
`SKILL.md` requires hashing the starting node for `bt claim`, but names no
algorithm, and no `bt` read command exposes a content hash, so a worker must
read the Python or guess.

# Outcome

The skill names the exact hash (SHA-256 hex of the raw UTF-8 file bytes,
including frontmatter), and `bt` exposes the value the claim compares against.

# Done when

- `SKILL.md` documents the base-hash algorithm in the hybrid-sidecar section.
- `bt hash NODE` (or a hash field in `bt search`/`bt status`) returns the same value the sidecar records.
- A regression test pins the documented algorithm to the sidecar's `sha256(text)`.
- `make test` passes.

# Result

Took the `bt hash` branch. `sidecar.content_hash` is the single canonical
algorithm: the SHA-256 hex digest of the bytes it is given, which the index
stores and `bt claim` records. `index.node_hash` resolves a bare ID or full
node name and returns that digest for the file's raw bytes, frontmatter
included, reading Markdown alone so it needs no sidecar. `bt hash NODE` prints
`node` and `content_hash` and fails with `unknown node` and exit `1` otherwise.
`index._read_index_rows` now feeds the same bytes it decodes into
`content_hash`, so the stored `content_hash` column and `bt hash` cannot
diverge.

Evidence:

- `SKILL.md` hybrid-sidecar section defines the base hash as the SHA-256 hex of
  the node file's raw UTF-8 bytes, frontmatter included, and says to get it
  from `bt hash`; the parallel-worktree section points the worker at `bt hash`.
- `bt hash TAS-061` matches `shasum -a 256` on the file and the `base_hash`
  recorded by this worker's `bt claim`.
- `test_hash_matches_raw_sha256_algorithm` pins `bt hash` output to
  `hashlib.sha256(node_file.read_bytes()).hexdigest()` and covers full-name
  resolution and the unknown-node error.
- `tests/bt-index.sh` cross-checks `bt hash` against `shasum` in the shell suite.
- `test_skill_frontmatter_and_hybrid_contract`, `test_skill_admission_and_parallel_contract`,
  and `test_bt_help_lists_every_command` assert the documented contract and command.
- `make test` passes.
