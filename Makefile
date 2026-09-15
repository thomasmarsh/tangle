.PHONY: test test-benchmarks benchmark diagnostic-benchmark storage-comparison verb-benchmark

# The fast Python suite and the remaining end-to-end shell screens are
# independent and process-spawn bound, so run them concurrently. Benchmark
# verification is excluded here and runs with `make test-benchmarks`. Every job
# is waited on and any failure fails the target.
test:
	@set -eu; \
	uv run ruff check; \
	uv run mypy; \
	pids=""; \
	uv run pytest -q & pids="$$pids $$!"; \
	for suite in install worktree-parallel; do \
		sh "tests/$$suite.sh" & pids="$$pids $$!"; \
	done; \
	status=0; \
	for pid in $$pids; do wait "$$pid" || status=1; done; \
	git diff --check; \
	exit $$status

test-benchmarks:
	uv run pytest -q -m benchmark

benchmark:
	uv run tangle benchmark token --protocol

diagnostic-benchmark:
	uv run tangle benchmark behavioral --verify

storage-comparison:
	uv run tangle benchmark storage --verify

verb-benchmark:
	uv run tangle benchmark verbs --verify
