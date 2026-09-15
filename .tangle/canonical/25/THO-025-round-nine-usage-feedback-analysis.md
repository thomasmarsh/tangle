---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-nine Hekate feedback confirms one independently resumable packaging defect: the installed launcher needs a writable user-home uv cache even for read-only commands.
---

Area [[IDX-001-execution-graph]].

# Question

`tangle feedback scan /Users/thomasmarsh/git/hekate` reports one proposed
feedback node recorded after the round analyzed in
[[THO-022-round-eight-usage-feedback-analysis]]: Hekate `FBK-030`, recorded at
`0.6.0+g169bad5`. Which findings still hold against this implementation at that
revision, and what self-improvement work do they require?

# Context

Hekate `FBK-030` is a single finding. The consuming session ran the mandatory
`tangle help authoring` from a sandbox, and the first invocation failed before
printing help with `Failed to initialize cache at /Users/thomasmarsh/.cache/uv`
(`Operation not permitted`), so a read-only query required write access outside
the repository and had to be rerun with elevated sandbox permission.

Reproduced at the current revision: the installed `<root>/.local/bin/tangle`
is the generated shim `exec uv run --project "$program_dir" --frozen tangle
"$@"`, and `uv run` initializes its cache before dispatching. With `UV_CACHE_DIR`
pointed at an unwritable directory, `tangle help authoring` exits before
rendering even though `<program_dir>/.venv` already exists and is synced:
`error: Failed to initialize cache at ...: Permission denied (os error 13)`.
`scripts/install.sh` copies the program tree and generates the shim but never
materializes the environment, so the first invocation needs a writable
`~/.cache/uv` both to build and to run the program. Running
`<program_dir>/.venv/bin/tangle` directly with a read-only `HOME` renders
`help authoring` successfully, so the prepared environment itself needs no
cache.

`SKILL.md` and `references/` never mention the cache and must not: the
implementation-leak contract in `tests/test_skill.py` forbids `uv` and `.venv`
in documented surfaces. The fix therefore belongs in the installer and the
generated launcher, not in documentation of an unavoidable dependency.

# Conclusion

| Feedback | Scan revision | Verdict | Evidence |
|----------|---------------|---------|----------|
| Hekate `FBK-030` | `0.6.0+g169bad5` | open, admitted | The generated launcher uses `uv run`, which initializes a writable cache for every command, including read-only `help`/`check`/query; reproduced with an unwritable `UV_CACHE_DIR` against an already-synced program, while direct execution of the program's own entry point succeeds with a read-only `HOME`. |

# Decision

Create the single remediation task
[[TAS-166-installed-launcher-without-a-uv-cache]]: materialize the shared
program's environment at install time and make the generated launcher run that
environment directly, keeping `uv run` only as the fallback for a program whose
environment is absent. One finding needs no coordinating parent, so the task is
this node's direct child.
