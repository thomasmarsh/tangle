# AGENTS.md

Instructions for agents working in the Braintree repository.

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
  `braintree`, `check`, `index`, `installer`, `obsidian`, `benchmark`, or
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
feat(braintree): add atomic ID reservation
fix(check): reject unpinned context dependencies
docs(skill): clarify frontier discovery
refactor(index): rebuild edges without a sidecar round-trip
```

## This project uses its own Braintree skill

This repository is the source of truth for the Braintree skill. Agents MUST
plan, track, and execute work through it rather than keeping planning in chat
or ad hoc notes.

1. Read [`SKILL.md`](SKILL.md) before starting, and follow its contracts for
   the vault, node admission, indexes, reachability, dependency revisions, and
   mutation rules.
2. Treat `nodes/` as the authoritative vault. Markdown is the durable,
   human-visible authority; the SQLite sidecar is derived, disposable local
   coordination state. Never edit the sidecar database directly.
3. Work from the graph: orient through `nodes/index-map.md`, derive the
   frontier from hub membership and each coordinating node's `next`, and
   prefer advancing an existing node over creating a new one. Admit a new node
   only when its outcome is likely to change a future decision or action.
4. Keep node content and its status directory move coherent, update `updated`
   on every mutation, and increment `context_rev` only for a consumer-relevant
   semantic change.
5. Validate graph mutations before finishing:

   ```sh
   braintree check nodes
   braintree index nodes   # optional hybrid sidecar index
   ```

   A commit that deliberately stages a semantic `context_rev` bump without yet
   reconciling its pinned consumers runs the sanctioned staged-staleness gate
   instead: `braintree check --allow-stale nodes`. It still requires every
   context edge to be pinned and relaxes only the revision equality. Reconcile
   each consumer before it executes and before finishing, so the plain gate
   passes and a shipped vault has no staged staleness.

6. When the skill is installed into another project, use the documented
   installer (`./scripts/install.sh --codex|--claude|--pi --project <root>` or
   `./scripts/install-claude.sh --project <root>`) and the installed
   `braintree` command from that project root.

Changes to `SKILL.md` change the skill contract and are covered by
`tests/test_skill.py`; keep those contract strings and the live vault valid.

## Before finishing

Run the full offline suite and keep the tree clean:

```sh
make test
```
