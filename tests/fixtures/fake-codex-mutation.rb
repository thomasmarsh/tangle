#!/usr/bin/env ruby
# frozen_string_literal: true

require "fileutils"
require "json"

if ARGV == ["--version"]
  puts "codex-cli fake-mutation-1"
  exit
end

root = ARGV[ARGV.index("-C") + 1]
model = ARGV[ARGV.index("--model") + 1]
effort = ARGV[ARGV.index("-c") + 1].delete_prefix("model_reasoning_effort=")
answer = ARGV[ARGV.index("--output-last-message") + 1]
active = File.join(root, "nodes/active/TAS-201-validate-schema.md")
resolved = File.join(root, "nodes/resolved/TAS-201-validate-schema.md")
text = File.binread(active)
text.sub!("context_rev: 3", "context_rev: 4")
text.sub!("updated: 2026-01-01T00:00:00Z", "updated: 2026-01-02T00:00:00Z")
text.sub!("summary: Validate the signed schema contract.", "summary: Schema validation is complete.")
text.sub!(/^next: .*\n/, "")
text << "\n# Result\n\nValidated the signed schema contract.\n"
File.binwrite(active, text)
File.rename(active, resolved)
File.binwrite(answer, "Routine mutation complete.\n")
File.binwrite(File.join(root, "unexpected.txt"), "unexpected\n") if ENV["KG_FAKE_MUTATION_EXTRA_EDIT"]

sessions = ENV.fetch("KG_TOKEN_BENCHMARK_SESSIONS_DIR")
path = File.join(sessions, "fake", "mutation.jsonl")
FileUtils.mkdir_p(File.dirname(path))
File.binwrite(path, [
  { type: "session_meta", payload: { cli_version: "fake-mutation-1", cwd: root, agent_path: "/fake/mutation" } },
  { type: "turn_context", payload: { cwd: root, model: model, effort: effort } },
  { type: "token_usage_record", payload: { turn_id: "fake-turn", turn_token_usage: { input_tokens: 11, cached_input_tokens: 3, output_tokens: 5, reasoning_output_tokens: 2, total_tokens: 16 } } },
  { type: "turn.completed", turn_id: "fake-turn" }
].map { |event| JSON.generate(event) }.join("\n") + "\n")
puts({ type: "turn.completed", turn_id: "fake-turn" }.to_json)
