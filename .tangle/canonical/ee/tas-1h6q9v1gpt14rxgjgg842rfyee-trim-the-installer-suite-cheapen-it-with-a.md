---
context_rev: 1
status: resolved
priority: P2
updated: 2026-09-15T16:29:39Z
summary: Trim the installer suite, cheapen it with a shared uv cache, and make it opt-in.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

tests/install.sh is the only coverage of scripts/install.sh and
install-claude.sh; no pytest test invokes either. Over-specified clusters to
remove: help-text golden locks (approx 341-356), mtime equality pairs (approx
183-184 and 240-242), redundant run_installed calls (approx 222 and 235), and
two of three installed-topic help renders (approx 110-120). Cost drivers: three
redirected-HOME installs each pay a cold uv cache rebuild (~16-18s total, fix
with an exported shared UV_CACHE_DIR), ~32 real install_target calls (~16-22s,
inherent), four run_installed (~9-10s), seven check_launcher (~5.5s). Keep every
structural guarantee: copied-tree byte identity, generated launcher, no-repoint
invariant, one program per root, idempotent no-op, upgrade restamp, --semantic,
selector.

# Outcome

tests/install.sh retains only load-bearing installer guarantees, runs
materially faster, and is opt-in via make test-install so make test is no longer
floored by it.

# Done when

- The over-specified clusters are removed.
- UV_CACHE_DIR is shared across the redirected-HOME installs.
- make test no longer runs tests/install.sh.
- make test-install runs the trimmed suite green.
- Before/after sh tests/install.sh timings are recorded.
- make test is green.

# Result

Trimmed `tests/install.sh` to its load-bearing assertions and moved it off the
default gate.

Removed over-specified locks: the help-text golden locks in both installer help
checks became usage-line and flag-token assertions; the mtime equality
assertions at the no-op, changed-revision, and no-repoint sites were dropped
while their byte-equality assertions remain; the redundant
`run_installed "$program_dir"` calls after `--pi` and `--claude` were dropped;
and the installed-topic help check renders one topic (`coordination`) instead of
three, the other two being covered by pytest.

Cheapened: `export UV_CACHE_DIR="${UV_CACHE_DIR:-$test_root/uv-cache}"` so the
three throwaway-home installs share one cache instead of paying three cold uv
cache rebuilds. The unwritable-cache launcher probe still sets its own
`UV_CACHE_DIR` inline and is unaffected.

Gate: `make test` no longer runs `tests/install.sh`; the new `test-install`
target runs it and `README.md` documents `make test-install`.

Evidence: `sh tests/install.sh` before about 60.3s (profiler single run;
67.1s under the original `make test`), after 48.8s wall on this host;
`make test` green at 794 passed, 3 skipped, pytest phase 37.93s, with no
installer screen in its log; `make test-install` exits 0 with
`install tests: passed`. Retained guarantees: copied-tree byte identity and the
`program_files` set, generated launcher, no-repoint invariant, one program per
root, idempotent no-op, upgrade restamp, `--semantic` bytes, and the selector
paths.

Tradeoff: installer regressions are no longer caught by the default gate and
are only covered by the opt-in `make test-install`.
