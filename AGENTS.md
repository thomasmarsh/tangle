# AGENTS.md

Instructions for agents working in the Tangle repository.

This file is the always-loaded hard store. It carries only the invariants that
must hold before [`SKILL.md`](SKILL.md) is loaded, and it routes every other
rule to the surface that already owns it: [`SKILL.md`](SKILL.md) and the
references it names own the Tangle contract, and [`README.md`](README.md)
owns installation. Promote a vault decision into this file only through a
settled `DEC` node that names the promoted rule in its consequences; the
promotion and condensation contract is [[THO-020-agents-md-braintree-bridge]].

## Conventional commits are mandatory

Every commit in this repository MUST use the
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

- Use one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
  `build`, `ci`, `chore`, `revert`.
- Use a scope when it clarifies the area, for example `graph`, `skill`,
  `tangle`, `check`, `index`, `installer`, `obsidian`, `benchmark`, or
  `token-benchmark`.
- Write the description in the imperative mood, lowercase, with no trailing
  period, and keep the header at or under 72 characters.
- Separate the header from the body with one blank line. Explain what changed
  and why in the body when the subject is not self-explanatory.
- Mark breaking changes with `!` after the type/scope and a `BREAKING CHANGE:`
  footer.
- Keep each commit to one logical change. When a graph node changes, keep its
  content update and its status move coherent in the same commit.
- A mechanical change with no independently resumable outcome (a one-line
  build, lint, formatting, or install fix) is not a graph node. Keep it in the
  enclosing node's `next` or result; when it needs its own commit, add a
  `Refs:` footer naming that node instead of admitting a leaf.
- Do not add tool, model, or co-author attribution trailers.

Examples:

```text
feat(tangle): add atomic ID reservation
fix(check): reject unpinned context dependencies
docs(skill): clarify frontier discovery
refactor(index): rebuild edges without a sidecar round-trip
```

## This project uses its own Tangle skill

This repository is the source of truth for the Tangle skill. Agents MUST
plan, track, and execute work through it for work whose conclusion must outlive
the session; work that is finished and committed within one session needs no
node because Git already records it. [`SKILL.md`](SKILL.md) owns the full
admission boundary. Do not keep cross-session planning in chat or ad hoc notes.

1. Read [`SKILL.md`](SKILL.md) before starting and follow it for the vault,
   node admission, indexes, reachability, dependency revisions, and mutation
   rules. The resolved node that settled a rule owns its rationale and
   evidence, so this file does not restate that rule.
2. Run `tangle check` before committing or handing off graph mutations. Use
   `tangle check --allow-stale` only for a deliberately staged `context_rev`
   bump, exactly as `SKILL.md` and `tangle help dependencies` state.
3. Install into another project with the documented installer and the installed
   `tangle` command from that project root; [`README.md`](README.md) names
   the explicit flags an automated run must pass.
4. Changes to `SKILL.md` change the skill contract and are covered by
   `tests/test_skill.py`; keep those contract strings and the live vault valid.

## Bounded task intake

- Work finished and committed in the current session needs no Tangle node or
  workflow ceremony; Git is its durable record.
- For “implement the next task,” start with the current frontier node's `next`
  action and deliver the smallest coherent slice. Do not infer authorization to
  investigate or implement every item in its broader outcome or `Done when`.
- Expand orientation only when a direct dependency, a failing verification, or
  code evidence requires it. If the broader task remains active, record the
  completed slice and leave a concrete `next` rather than spending the session
  on speculative architecture tracing.

## Before finishing

Run the fast offline suite and keep the tree clean:

```sh
make test
```

Benchmark verification is opt-in so the default suite stays fast. Run it too
when a change touches a benchmark harness or a committed benchmark baseline:

```sh
make test-benchmarks
```
