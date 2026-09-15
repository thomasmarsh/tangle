---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Let the installer opt into the optional semantic extra so installed clustering works.
---

Parent [[TAS-068-direct-answer-surface]].

# Context

The installed launcher runs the skill with a frozen dependency set that omits the
optional semantic extra, so `tangle clusters` reports the capability absent
even after the extra is synced by hand. The extra is documented as optional and
must stay out of a plain install.

# Outcome

`scripts/install.sh` accepts an explicit `--semantic` opt-in that generates a
launcher requesting the extra, and a plain install is unchanged and stays
dependency-free.

# Done when

`--semantic` is parsed and documented in the installer help, the generated
launcher requests the extra only for that opt-in, the README documents it
without leaking implementation detail, and `make test` passes.

# Result

`scripts/install.sh` (and the Claude wrapper that delegates to it) accepts an
explicit `--semantic` opt-in. The generated launcher then requests the optional
extra, while a plain install keeps the exact previous launcher bytes and the
dependency-free frozen set. The installer prints the `TANGLE_SEMANTIC_PROVIDER` line
that enables the layer, so the extra and the provider stay separate switches.
Help, README, and `tests/install.sh` cover the opt-in, the plain exclusion, the
provider hint, and idempotence. `sh tests/install.sh`, `tangle check nodes`,
and `make test` (438 passed) all passed.
