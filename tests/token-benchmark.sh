#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fixture="$repo_root/tests/fixtures/token-usage-session.jsonl"
no_provenance="$repo_root/tests/fixtures/token-usage-no-provenance.jsonl"
regression="$repo_root/tests/fixtures/token-usage-regression.jsonl"
no_turn_id="$repo_root/tests/fixtures/token-usage-no-turn-id.jsonl"
completed_stream="$repo_root/tests/fixtures/codex-stream-complete.jsonl"
reading_prefix_stream="$repo_root/tests/fixtures/codex-stream-reading-prefix-complete.jsonl"
reading_prefix_malformed_stream="$repo_root/tests/fixtures/codex-stream-reading-prefix-malformed.jsonl"
incomplete_stream="$repo_root/tests/fixtures/codex-stream-incomplete-with-telemetry.jsonl"
cold_answer="$repo_root/tests/fixtures/cold-resume-answer.json"

output=$("$repo_root/scripts/token-benchmark" --session "$fixture" --task-path /root/token-benchmark-fixture)
printf '%s\n' "$output" | grep -F 'historical_token_accounting{sessions,input_tokens,cached_input_tokens,uncached_input_tokens,output_tokens,reasoning_output_tokens,total_tokens}: 1,200,20,180,50,17,250' >/dev/null
printf '%s\n' "$output" | grep -F '"classification":"historical-implementation-cost"' >/dev/null
printf '%s\n' "$output" | grep -F '"task_path":"/root/token-benchmark-fixture"' >/dev/null
"$repo_root/scripts/token-benchmark" --protocol | grep -F 'token_benchmark{status,live_calls,baseline}: ready,0,absent' >/dev/null
"$repo_root/scripts/token-benchmark" --check-fixture | grep -F '"fixture_version":"graph-retrieval-v3"' >/dev/null
"$repo_root/scripts/token-benchmark" --check-fixture | grep -F '"representation":"graph","scale":"small"' >/dev/null
fixture_check=$("$repo_root/scripts/token-benchmark" --check-fixture)
printf '%s\n' "$fixture_check" | grep -F '"skill_sha256"' >/dev/null
printf '%s\n' "$fixture_check" | grep -F '"files":64' >/dev/null
cold_resume_check=$("$repo_root/scripts/token-benchmark" --check-fixture --case cold-resume)
printf '%s\n' "$cold_resume_check" | grep -F '"benchmark_case":"cold-resume"' >/dev/null
printf '%s\n' "$cold_resume_check" | grep -F '"fixture_version":"cold-resume-frontier-v1"' >/dev/null
printf '%s\n' "$cold_resume_check" | grep -F '"representation":"graph"' >/dev/null
mutation_check=$("$repo_root/scripts/token-benchmark" --check-fixture --case routine-mutation --scale small)
printf '%s\n' "$mutation_check" | grep -F '"benchmark_case":"routine-mutation"' >/dev/null
printf '%s\n' "$mutation_check" | grep -F '"fixture_version":"routine-mutation-status-v1"' >/dev/null
fake_sessions=$(mktemp -d)
extra_sessions=$(mktemp -d)
trap 'rm -rf "$fake_sessions" "$extra_sessions"' EXIT HUP INT TERM
mutation_record=$(BT_TOKEN_BENCHMARK_CODEX="$repo_root/tests/fixtures/fake-codex-mutation.py" BT_TOKEN_BENCHMARK_SESSIONS_DIR="$fake_sessions" "$repo_root/scripts/token-benchmark" --record --case routine-mutation --model fake-model --reasoning-effort medium --repetitions 1)
printf '%s\n' "$mutation_record" | grep -F 'token_benchmark{runs,input_tokens,cached_input_tokens,uncached_input_tokens,output_tokens,reasoning_output_tokens,total_tokens,correct}: 1,11,3,8,5,2,16,true' >/dev/null
if BT_FAKE_MUTATION_EXTRA_EDIT=1 BT_TOKEN_BENCHMARK_CODEX="$repo_root/tests/fixtures/fake-codex-mutation.py" BT_TOKEN_BENCHMARK_SESSIONS_DIR="$extra_sessions" "$repo_root/scripts/token-benchmark" --record --case routine-mutation --model fake-model --reasoning-effort medium --repetitions 1 >/dev/null 2>&1; then
  echo "mutation recorder accepted an unrelated fixture edit" >&2
  exit 1
fi
schema=$("$repo_root/scripts/token-benchmark" --check-output-schema --case cold-resume)
printf '%s\n' "$schema" | grep -F '"additionalProperties":false' >/dev/null
if printf '%s\n' "$schema" | grep -F '"$schema"' >/dev/null; then
  echo "unsupported output-schema dialect marker was retained" >&2
  exit 1
fi
composite_schema=$("$repo_root/scripts/token-benchmark" --check-output-schema --case composite)
printf '%s\n' "$composite_schema" | grep -F '"required":["frontier","current_decision","stale_dependents","orphan"]' >/dev/null
printf '%s\n' "$composite_schema" | grep -F '"properties":{"frontier"' >/dev/null
printf '%s\n' "$composite_schema" | grep -F '"current_decision":{"type":"string"}' >/dev/null
"$repo_root/scripts/token-benchmark" --check-recording "$completed_stream" --answer "$cold_answer" --case cold-resume | grep -F 'recording_check{status,live_calls}: valid,0' >/dev/null
"$repo_root/scripts/token-benchmark" --check-recording "$reading_prefix_stream" --answer "$cold_answer" --case cold-resume | grep -F 'recording_check{status,live_calls}: valid,0' >/dev/null
if "$repo_root/scripts/token-benchmark" --check-recording "$reading_prefix_malformed_stream" --answer "$cold_answer" --case cold-resume >/dev/null 2>&1; then
  echo "malformed JSON after the Reading prefix was accepted" >&2
  exit 1
fi
if "$repo_root/scripts/token-benchmark" --check-recording "$incomplete_stream" --answer "$cold_answer" --case cold-resume >/dev/null 2>&1; then
  echo "telemetry-only incomplete stream was accepted" >&2
  exit 1
fi
shape=$("$repo_root/scripts/token-benchmark" --inspect-session "$fixture")
printf '%s\n' "$shape" | grep -F '"turn_id,turn_token_usage"' >/dev/null
printf '%s\n' "$shape" | grep -F '"session_meta"' >/dev/null
printf '%s\n' "$shape" | grep -F '"turn_context"' >/dev/null
if "$repo_root/scripts/token-benchmark" --session "$repo_root/tests/fixtures/token-usage-invalid.jsonl" --model fixture-model --reasoning-effort low >/dev/null 2>&1; then
  echo "invalid token accounting was accepted" >&2
  exit 1
fi
if "$repo_root/scripts/token-benchmark" --session "$fixture" --model wrong-model >/dev/null 2>&1; then
  echo "unchecked caller-supplied model was accepted" >&2
  exit 1
fi
if "$repo_root/scripts/token-benchmark" --session "$fixture" --task-path /root/wrong-task >/dev/null 2>&1; then
  echo "unchecked caller-supplied task path was accepted" >&2
  exit 1
fi
if "$repo_root/scripts/token-benchmark" --session "$no_provenance" >/dev/null 2>&1; then
  echo "session without observed task provenance was accepted" >&2
  exit 1
fi
if "$repo_root/scripts/token-benchmark" --session "$regression" >/dev/null 2>&1; then
  echo "regressing cumulative token snapshot was accepted" >&2
  exit 1
fi
if "$repo_root/scripts/token-benchmark" --session "$no_turn_id" >/dev/null 2>&1; then
  echo "token usage without a turn ID was accepted" >&2
  exit 1
fi
