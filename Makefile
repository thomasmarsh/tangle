.PHONY: test test-install test-benchmarks verify FORCE benchmark \
	diagnostic-benchmark storage-comparison verb-benchmark

# The fast Python suite and the remaining end-to-end shell screen are
# independent and process-spawn bound, so run them concurrently, and the
# Python suite itself runs under pytest-xdist (`-n auto`) because its tests are
# dominated by per-test tangle subprocess spawns. Benchmark verification is
# excluded here and runs with `make test-benchmarks`, which stays serial. The
# installer end-to-end screen spawns many real installs and is opt-in, so it
# runs with `make test-install`. Every job is waited on and any failure fails
# the target.
test:
	@set -eu; \
	uv run ruff check; \
	uv run mypy; \
	pids=""; \
	uv run pytest -q -n auto & pids="$$pids $$!"; \
	sh tests/worktree-parallel.sh & pids="$$pids $$!"; \
	status=0; \
	for pid in $$pids; do wait "$$pid" || status=1; done; \
	git diff --check; \
	exit $$status

# The installer screen installs into throwaway roots many times, so it is
# opt-in rather than part of the per-change gate.
test-install:
	sh tests/install.sh

test-benchmarks:
	uv run pytest -q -m benchmark

# Scoped verification for one affected surface, as an iteration gate: `make
# verify` lists the surfaces and `make verify-SURFACE` runs the shared lint,
# type, graph, and whitespace gates plus that surface's focused tests. It never
# replaces `make test`, which stays the final acceptance gate before handoff.
verify:
	@sh scripts/verify-surface.sh

# The surfaces stay defined in the one map inside the script, so the pattern
# target covers each of them; the always-out-of-date prerequisite keeps the
# recipe running even if a same-named file ever appears at the repository root.
verify-%: FORCE
	@sh scripts/verify-surface.sh '$*'

FORCE:

benchmark:
	uv run tangle benchmark token --protocol

diagnostic-benchmark:
	PYTHONPATH=research uv run python -m tangle_research.behavioral_benchmark --verify

storage-comparison:
	uv run tangle benchmark storage --verify

verb-benchmark:
	PYTHONPATH=research uv run python -m tangle_research.verb_benchmark --verify
