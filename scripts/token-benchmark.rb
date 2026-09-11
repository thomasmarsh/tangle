#!/usr/bin/env ruby
# frozen_string_literal: true

# Opt-in Codex token benchmark. The measured work is a fresh generated
# repository, never this checkout. Only usage telemetry is read from sessions.
require "digest"
require "fileutils"
require "json"
require "open3"
require "optparse"
require "tmpdir"
require "timeout"
require "time"

FIELDS = %w[input_tokens cached_input_tokens output_tokens reasoning_output_tokens total_tokens].freeze
MAX_REPETITIONS = 3
FIXTURE_VERSION = "graph-retrieval-v3"
FIXTURE_SEED = "tas-020-2026-09-10"
SCALES = { "small" => 32, "large" => 320 }.freeze
REPRESENTATIONS = %w[graph plan].freeze
CASES = {
  "composite" => {
    expected: { "frontier" => "TAS-041", "current_decision" => "DEC-031", "stale_dependents" => %w[TAS-052 TAS-053], "orphan" => "TAS-060" },
    fixture_version: "graph-retrieval-v3"
  },
  "cold-resume" => {
    expected: { "frontier" => "TAS-101", "next" => "Apply the reversible schema migration." },
    fixture_version: "cold-resume-frontier-v1"
  },
  "routine-mutation" => {
    expected: {},
    fixture_version: "routine-mutation-status-v1"
  }
}.freeze
MUTATION_ANSWER = "Routine mutation complete.".freeze

def write(path, text)
  FileUtils.mkdir_p(File.dirname(path))
  File.binwrite(path, text)
end

def node(summary:, extra: "", next_action: nil, area: "IDX-001-import")
  header = ["---", "context_rev: 1", "updated: 2026-01-01T00:00:00Z", "summary: #{summary}"]
  header << "next: #{next_action}" if next_action
  header << "---"
  primary_route = area && "Area [[#{area}]]."
  ([header.join("\n"), "", primary_route, "", extra].compact.reject(&:empty?).join("\n") + "\n")
end

def skill_source
  File.expand_path("../SKILL.md", __dir__)
end

def skill_metadata_source
  File.expand_path("../agents/openai.yaml", __dir__)
end

def output_schema(expected)
  properties = {
    "frontier" => { "type" => "string" },
    "current_decision" => { "type" => "string" },
    "stale_dependents" => { "type" => "array", "items" => { "type" => "string" } },
    "orphan" => { "type" => "string" },
    "next" => { "type" => "string" }
  }.slice(*expected.keys)
  {
    "type" => "object",
    "additionalProperties" => false,
    "required" => expected.keys,
    "properties" => properties
  }
end

def completed_answer!(stream, answer_path, expected)
  lines = stream.each_line.to_a
  # Codex CLI 0.154.0 emitted this exact progress line before its --json
  # stream in the final cold-resume invocations. It is the sole tolerated
  # non-event line; every remaining line is parsed strictly below.
  lines.shift if lines.first&.chomp == "Reading"
  completed = lines.any? do |line|
    event = JSON.parse(line)
    event["type"] == "turn.completed"
  end
  raise ArgumentError, "live Codex stream ended without turn.completed" unless completed
  raise ArgumentError, "live Codex stream completed without an answer artifact" unless File.file?(answer_path)
  answer = JSON.parse(File.binread(answer_path))
  raise ArgumentError, "fixture correctness gate failed" unless answer == expected
end

def completed_mutation!(stream, answer_path, root, before)
  lines = stream.each_line.to_a
  lines.shift if lines.first&.chomp == "Reading"
  completed = lines.any? { |line| JSON.parse(line)["type"] == "turn.completed" }
  raise ArgumentError, "live Codex stream ended without turn.completed" unless completed
  raise ArgumentError, "live Codex stream completed without an exact answer artifact" unless File.file?(answer_path) && File.binread(answer_path).strip == MUTATION_ANSWER

  after = fixture_files(root).reject { |path| path == answer_path }.to_h { |path| [path.delete_prefix(root + "/"), File.binread(path)] }
  expected_paths = before.keys - ["nodes/active/TAS-201-validate-schema.md"] + ["nodes/resolved/TAS-201-validate-schema.md"]
  raise ArgumentError, "mutation changed an unexpected fixture path" unless after.keys.sort == expected_paths.sort
  (before.keys - ["nodes/active/TAS-201-validate-schema.md"]).each do |path|
    raise ArgumentError, "mutation changed unrelated fixture content: #{path}" unless after.fetch(path) == before.fetch(path)
  end
  node = after.fetch("nodes/resolved/TAS-201-validate-schema.md")
  raise ArgumentError, "mutation did not set the required semantic revision" unless node.match?(/^context_rev: 4$/)
  updated = node[/^updated: ([^\n]+)$/, 1]
  raise ArgumentError, "mutation timestamp is not a newer UTC ISO-8601 value" unless updated&.match?(/\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\z/) && Time.parse(updated) > Time.parse("2026-01-01T00:00:00Z")
  raise ArgumentError, "mutation did not apply the requested summary" unless node.match?(/^summary: Schema validation is complete\.$/)
  raise ArgumentError, "resolved mutation retained next" if node.match?(/^next:/)
  raise ArgumentError, "mutation did not preserve its area link" unless node.include?("Area [[IDX-001-import]].")
  raise ArgumentError, "mutation did not preserve its dependency pin" unless node.include?("Depends on [[DEF-020-import-contract]] at context_rev 4.")
  raise ArgumentError, "mutation did not record exact completion evidence" unless node.include?("# Result\n\nValidated the signed schema contract.\n")
  graph_check = File.join(root, ".agents/skills/knowledge-execution-graph/scripts/graph-check.rb")
  raise ArgumentError, "mutated graph is invalid" unless system("ruby", graph_check, File.join(root, "nodes"), out: File::NULL, err: File::NULL)
end

def fixture_prompt(representation, benchmark_case)
  if benchmark_case == "routine-mutation"
    return <<~PROMPT
      Complete one routine Markdown execution-graph mutation. First explicitly invoke $knowledge-execution-graph and follow .agents/skills/knowledge-execution-graph/SKILL.md.

      The signed-schema validation task is complete. Move its existing node to resolved and make only the necessary node mutation: set its summary exactly to "Schema validation is complete.", record exactly "Validated the signed schema contract." under # Result, refresh updated to the current UTC ISO-8601 time, and apply the correct semantic context revision behavior. Preserve its Area and dependency pin. Do not modify any other fixture file. Respond exactly: Routine mutation complete.
    PROMPT
  end
  if benchmark_case == "cold-resume"
    return <<~PROMPT
      You are resuming a cold engineering session. Inspect this repository's Markdown execution graph; do not guess from filenames alone.

      First explicitly invoke $knowledge-execution-graph and follow the project skill at .agents/skills/knowledge-execution-graph/SKILL.md before inspecting the graph.

      Return exactly one compact JSON object with these keys and no others:
      {"frontier":"ID","next":"exact next action"}

      `frontier` is the one currently executable active task deliberately selected by the index's Focus route. Exclude resolved history, blocked work, proposed work, and active work not selected by Focus. `next` is that task's exact frontmatter next action. Do not edit files.
    PROMPT
  end
  <<~PROMPT
    You have been asked to resume the active data-import hardening work. Inspect this repository's #{representation == "graph" ? "Markdown execution graph" : "conventional plan documents"}; do not guess from filenames alone.

    #{representation == "graph" ? "First explicitly invoke $knowledge-execution-graph and follow the project skill at .agents/skills/knowledge-execution-graph/SKILL.md before inspecting the graph." : "Use the conventional plan as the control representation; it expresses the same current work facts and historical distractors but does not supply graph-skill instructions."}

    Return exactly one compact JSON object with these keys and no others:
    {"frontier":"ID","current_decision":"ID","stale_dependents":["ID"],"orphan":"ID"}

    `frontier` is the currently executable active task selected by the active coordinator's next route. `current_decision` is the decision that remains in force, not a superseded decision. `stale_dependents` contains every task whose pinned dependency revision is older than the definition's current revision, sorted lexicographically. `orphan` is the unfinished actionable task with no primary route to any root hub. Do not edit files.
  PROMPT
end

def fixture_hash(root)
  files = fixture_files(root)
  Digest::SHA256.hexdigest(files.map { |path| "#{path.delete_prefix(root + "/")}\0#{File.binread(path)}" }.join)
end

def fixture_files(root)
  Dir.glob(File.join(root, "**", "*"), File::FNM_DOTMATCH)
     .select { |path| File.file?(path) && !path.delete_prefix(root + "/").start_with?(".git/") }
     .sort
end

def generate_fixture(root, representation, scale, benchmark_case)
  case_config = CASES.fetch(benchmark_case)
  expected = case_config.fetch(:expected)
  count = SCALES.fetch(scale)
  _, status = Open3.capture2e("git", "init", "-q", root)
  raise ArgumentError, "could not initialize isolated fixture repository" unless status.success?
  write(File.join(root, ".gitignore"), "*\n!.gitignore\n")
  if representation == "graph"
    skill_path = File.join(root, ".agents/skills/knowledge-execution-graph/SKILL.md")
    write(skill_path, File.binread(skill_source))
    write(File.join(root, ".agents/skills/knowledge-execution-graph/agents/openai.yaml"), File.binread(skill_metadata_source))
    write(File.join(root, ".agents/skills/knowledge-execution-graph/scripts/graph-check.rb"), File.binread(File.expand_path("graph-check.rb", __dir__)))
    if benchmark_case == "routine-mutation"
      write(File.join(root, "nodes/index-map.md"), "# Routes\n\n- Indexes [[IDX-001-import]]\n")
      write(File.join(root, "nodes/resolved/IDX-001-import.md"), "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\nsummary: Data import hardening area.\n---\n")
      definition = node(summary: "Signed schema contract.", extra: "# Invariant\n\nSigned schemas are required.").sub("context_rev: 1", "context_rev: 4")
      write(File.join(root, "nodes/resolved/DEF-020-import-contract.md"), definition)
      task = node(summary: "Validate the signed schema contract.", next_action: "Run signed schema validation.", extra: "Depends on [[DEF-020-import-contract]] at context_rev 4.").sub("context_rev: 1", "context_rev: 3")
      write(File.join(root, "nodes/active/TAS-201-validate-schema.md"), task)
    elsif benchmark_case == "cold-resume"
      write(File.join(root, "nodes/index-map.md"), "# Focus\n\n- [[TAS-101-apply-schema-migration]]\n\n# Routes\n\n- Indexes [[IDX-001-import]]\n")
      write(File.join(root, "nodes/resolved/IDX-001-import.md"), "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\nsummary: Data import hardening area.\n---\n")
      write(File.join(root, "nodes/active/TAS-101-apply-schema-migration.md"), node(summary: "Apply the resumable schema migration.", next_action: "Apply the reversible schema migration."))
      write(File.join(root, "nodes/blocked/TAS-102-vendor-access.md"), node(summary: "Wait for vendor credentials.", next_action: "Request vendor credentials."))
      write(File.join(root, "nodes/proposed/TAS-103-follow-up-cleanup.md"), node(summary: "Plan post-migration cleanup.", next_action: "Draft the cleanup plan."))
      write(File.join(root, "nodes/active/TAS-104-unselected-investigation.md"), node(summary: "Investigate an unrelated warning.", next_action: "Inspect unrelated warning logs."))
      count.times do |i|
        id = format("TAS-%03d", 200 + i)
        write(File.join(root, "nodes/resolved/#{id}-historical.md"), node(summary: "Resolved historical import item #{i}."))
      end
    else
      write(File.join(root, "nodes/index-map.md"), "# Routes\n\n- Indexes [[IDX-001-import]]\n")
    write(File.join(root, "nodes/resolved/IDX-001-import.md"), "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\nsummary: Data import hardening area.\n---\n")
    definition = node(summary: "Import contract now rejects unsigned manifests.", extra: "# Invariant\n\nRevision 4 requires signed manifests.").sub("context_rev: 1", "context_rev: 4")
    write(File.join(root, "nodes/resolved/DEF-020-import-contract.md"), definition)
    old_decision = node(summary: "Use the legacy routing branch.", extra: "Superseded by [[DEC-031-current-routing]].").sub("updated: 2026-01-01T00:00:00Z", "updated: 2026-01-01T00:00:00Z\ndisposition: superseded")
    write(File.join(root, "nodes/resolved/DEC-030-old-routing.md"), old_decision)
    write(File.join(root, "nodes/resolved/DEC-031-current-routing.md"), node(summary: "Use manifest-first routing.", extra: "# Decision\n\nManifest-first routing is current."))
    write(File.join(root, "nodes/active/TAS-040-import-coordinator.md"), node(summary: "Coordinate data-import hardening.", next_action: "\"[[TAS-041-validate-manifests]]\""))
    write(File.join(root, "nodes/active/TAS-041-validate-manifests.md"), node(summary: "Validate signed manifests.", next_action: "Run the signed-manifest validation.", area: nil, extra: "Parent [[TAS-040-import-coordinator]]."))
    %w[052 053].each do |number|
      write(File.join(root, "nodes/active/TAS-#{number}-stale-consumer.md"), node(summary: "Reconcile import contract consumer.", next_action: "Reconcile the pinned import-contract revision.", extra: "Depends on [[DEF-020-import-contract]] at context_rev 3."))
    end
    write(File.join(root, "nodes/active/TAS-060-unrouted-cleanup.md"), "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-01-01T00:00:00Z\nsummary: Remove obsolete import staging files.\nnext: Delete obsolete staging files.\n---\n")
    count.times do |i|
      id = format("TAS-%03d", 100 + i)
      write(File.join(root, "nodes/resolved/#{id}-historical.md"), node(summary: "Historical import note #{i}."))
    end
    end
  else
    raise ArgumentError, "cold-resume benchmark has no plan representation" if benchmark_case == "cold-resume"
    text = +<<~PLAN
      # Data import hardening plan

      ## Current work

      TAS-040 is the coordinator; its one active execution frontier is TAS-041.
      DEC-031 is the current routing decision; DEC-030 is superseded.
      DEF-020 is revision 4; TAS-052 and TAS-053 remain pinned to revision 3.
      TAS-060 is the one actionable unfinished cleanup task not routed to the import area hub.

      ## Historical completed items
    PLAN
    count.times { |i| text << "Historical completed item TAS-#{format('%03d', 100 + i)}.\n" }
    write(File.join(root, "plans/data-import.md"), text)
  end
  write(File.join(root, "TASK.txt"), fixture_prompt(representation, benchmark_case))
  write(File.join(root, "answer.schema.json"), JSON.pretty_generate(output_schema(expected)) + "\n") unless benchmark_case == "routine-mutation"
  metadata = { benchmark_case: benchmark_case, fixture_version: case_config.fetch(:fixture_version), fixture_seed: FIXTURE_SEED, fixture_sha256: fixture_hash(root) }
  metadata[:skill_sha256] = Digest::SHA256.file(skill_source).hexdigest if representation == "graph"
  metadata
end

def usage_hash(value)
  return nil unless value.is_a?(Hash)
  normalized = value.transform_keys(&:to_s)
  return nil unless FIELDS.all? { |key| normalized[key].is_a?(Integer) && normalized[key] >= 0 }
  result = FIELDS.to_h { |key| [key, normalized.fetch(key)] }
  result["uncached_input_tokens"] = result.fetch("input_tokens") - result.fetch("cached_input_tokens")
  raise ArgumentError, "cached input tokens exceed input tokens" if result["uncached_input_tokens"].negative?
  raise ArgumentError, "total tokens is not input plus output" unless result["total_tokens"] == result["input_tokens"] + result["output_tokens"]
  result
end

def turn_id!(payload)
  turn_id = payload["turn_id"]
  raise ArgumentError, "token_usage_record lacks payload.turn_id" unless turn_id.is_a?(String) && !turn_id.strip.empty?
  turn_id
end

def cumulative_snapshot!(previous, current, turn_id)
  regressed = FIELDS.find { |field| current.fetch(field) < previous.fetch(field) }
  raise ArgumentError, "turn #{turn_id.inspect} token usage regresses #{regressed}" if regressed
end

def session_usage(path)
  final_snapshots = {}
  File.foreach(path) do |line|
    event = JSON.parse(line)
    next unless event["type"] == "token_usage_record" && event["payload"].is_a?(Hash)
    next unless event["payload"].key?("turn_token_usage")
    usage = usage_hash(event["payload"]["turn_token_usage"])
    raise ArgumentError, "token_usage_record has malformed turn_token_usage" unless usage
    turn_id = turn_id!(event.fetch("payload"))
    previous = final_snapshots[turn_id]
    cumulative_snapshot!(previous, usage, turn_id) if previous
    # Codex emits cumulative snapshots for a turn. Keep its last valid record;
    # different turn IDs are independently additive.
    final_snapshots[turn_id] = usage
  end
  raise ArgumentError, "no token_usage_record.turn_token_usage in #{path}" if final_snapshots.empty?
  final_snapshots.values
end

def graph_fixture_facts(root)
  definition = File.binread(File.join(root, "nodes/resolved/DEF-020-import-contract.md"))
  revision = definition[/^context_rev: (\d+)$/, 1]&.to_i
  raise ArgumentError, "graph fixture definition has no context_rev" unless revision
  stale = Dir.glob(File.join(root, "nodes", "*", "*.md")).filter_map do |path|
    pin = File.binread(path)[/Depends on \[\[DEF-020-import-contract\]\] at context_rev (\d+)\./, 1]
    File.basename(path, ".md")[/\ATAS-\d+/] if pin && pin.to_i < revision
  end.sort
  { stale_dependents: stale }
end

def session_shapes(path)
  shapes = Hash.new(0)
  File.foreach(path) do |line|
    event = JSON.parse(line)
    next unless event["type"] == "token_usage_record" && event["payload"].is_a?(Hash)
    shapes[event["payload"].keys.map(&:to_s).sort.join(",")] += 1
  end
  raise ArgumentError, "no token_usage_record in #{path}" if shapes.empty?
  shapes
end

def scalar_values(events, type, field)
  events.select { |event| event["type"] == type && event["payload"].is_a?(Hash) }
        .map { |event| event["payload"][field] }.compact.map(&:to_s).uniq
end

def session_observations(path)
  events = File.foreach(path).map { |line| JSON.parse(line) }
  agent_paths = scalar_values(events, "session_meta", "agent_path")
  meta_cwd = scalar_values(events, "session_meta", "cwd")
  context_cwd = scalar_values(events, "turn_context", "cwd")
  {
    observed_agent_path: agent_paths,
    observed_cli_version: scalar_values(events, "session_meta", "cli_version"),
    observed_session_cwd: meta_cwd,
    observed_turn_cwd: context_cwd,
    observed_model: scalar_values(events, "turn_context", "model"),
    observed_reasoning_effort: scalar_values(events, "turn_context", "effort"),
    token_usage_payload_shapes: session_shapes(path)
  }
end

def exactly_one_observation!(observed, field)
  values = observed.fetch(field)
  raise ArgumentError, "session telemetry lacks #{field}" if values.empty?
  raise ArgumentError, "session telemetry has ambiguous #{field}" unless values.length == 1
  values.first
end

def historical_session_provenance(path, expected:)
  observed = session_observations(path)
  provenance = {
    task_path: exactly_one_observation!(observed, :observed_agent_path),
    cli_version: exactly_one_observation!(observed, :observed_cli_version),
    model: exactly_one_observation!(observed, :observed_model),
    reasoning_effort: exactly_one_observation!(observed, :observed_reasoning_effort)
  }
  { model: :model, effort: :reasoning_effort, task_path: :task_path }.each do |option, field|
    requested = expected.fetch(option)
    next unless requested
    raise ArgumentError, "session telemetry #{field} mismatch" unless provenance.fetch(field) == requested
  end
  provenance
end

def assert_live_observations!(path, requested:, fixture_dir:, cli_version:)
  observed = session_observations(path)
  required = {
    observed_cli_version: [cli_version.sub(/\Acodex-cli\s+/, "")], observed_session_cwd: [fixture_dir], observed_turn_cwd: [fixture_dir],
    observed_model: [requested.fetch(:model)], observed_reasoning_effort: [requested.fetch(:effort)]
  }
  required.each do |field, expected|
    actual = observed.fetch(field)
    raise ArgumentError, "session telemetry lacks #{field}" if actual.empty?
    raise ArgumentError, "session telemetry #{field} mismatch" unless actual == expected
  end
  observed
end

def totals(usages)
  (FIELDS + ["uncached_input_tokens"]).to_h { |field| [field, usages.sum { |usage| usage.fetch(field) }] }
end

def median(values)
  ordered = values.sort
  ordered[ordered.length / 2]
end

def emit_record(runs, metadata, output_path)
  sample_totals = runs.map { |run| totals(run) }
  medians = (FIELDS + ["uncached_input_tokens"]).to_h { |field| [field, median(sample_totals.map { |run| run.fetch(field) })] }
  record = { protocol: "codex-session-token-v2", correctness: true, samples: sample_totals, median: medians, metadata: metadata }
  puts "token_benchmark{runs,input_tokens,cached_input_tokens,uncached_input_tokens,output_tokens,reasoning_output_tokens,total_tokens,correct}: #{runs.length},#{medians.fetch('input_tokens')},#{medians.fetch('cached_input_tokens')},#{medians.fetch('uncached_input_tokens')},#{medians.fetch('output_tokens')},#{medians.fetch('reasoning_output_tokens')},#{medians.fetch('total_tokens')},true"
  puts JSON.generate(record)
  write(output_path, JSON.pretty_generate(record) + "\n") if output_path
end

def emit_historical_accounting(runs, provenance)
  samples = runs.map { |run| totals(run) }
  aggregate = (FIELDS + ["uncached_input_tokens"]).to_h do |field|
    [field, samples.sum { |sample| sample.fetch(field) }]
  end
  record = {
    protocol: "codex-session-token-v2",
    classification: "historical-implementation-cost",
    samples: samples,
    aggregate: aggregate,
    provenance: provenance
  }
  puts "historical_token_accounting{sessions,input_tokens,cached_input_tokens,uncached_input_tokens,output_tokens,reasoning_output_tokens,total_tokens}: #{samples.length},#{aggregate.fetch('input_tokens')},#{aggregate.fetch('cached_input_tokens')},#{aggregate.fetch('uncached_input_tokens')},#{aggregate.fetch('output_tokens')},#{aggregate.fetch('reasoning_output_tokens')},#{aggregate.fetch('total_tokens')}"
  puts JSON.generate(record)
end

def protocol
  puts "token_benchmark{status,live_calls,baseline}: ready,0,absent"
  puts "record: ruby scripts/token-benchmark.rb --record --model MODEL --reasoning-effort low --representation graph --scale small --repetitions 3 --output benchmark/token-baseline.json"
  puts "control: ruby scripts/token-benchmark.rb --record --model MODEL --reasoning-effort low --representation plan --scale small --repetitions 3 --output benchmark/token-plan-control.json"
  puts "historical accounting: ruby scripts/token-benchmark.rb --session PATH [--task-path /root/task]"
end

def newest_session(before, fixture_dir)
  candidates = Dir.glob(File.join(session_root, "**", "*.jsonl")).reject { |path| before.include?(path) }
  matching = candidates.select { |path| session_observations(path).fetch(:observed_session_cwd).include?(fixture_dir) }
  raise ArgumentError, "Codex did not create exactly one fresh fixture session" unless matching.length == 1
  matching.first
end

def session_root
  File.expand_path(ENV.fetch("KG_TOKEN_BENCHMARK_SESSIONS_DIR", "~/.codex/sessions"))
end

def codex_command
  ENV.fetch("KG_TOKEN_BENCHMARK_CODEX", "codex")
end

options = { sessions: [], record: false, representation: "graph", scale: "small", benchmark_case: "composite" }
OptionParser.new do |parser|
  parser.banner = "usage: ruby scripts/token-benchmark.rb --protocol | --session PATH [--task-path PATH] [--model MODEL] [--reasoning-effort EFFORT] | --record --model MODEL --reasoning-effort EFFORT [--case composite|cold-resume] [--representation graph|plan] [--scale small|large] [--repetitions 1..3] [--output PATH]"
  parser.on("--protocol", "Print the no-live-call protocol") { options[:protocol] = true }
  parser.on("--check-fixture", "Generate each fixture variant and verify its fixed metadata") { options[:check_fixture] = true }
  parser.on("--session PATH", "Parse one session JSONL") { |value| options[:sessions] << value }
  parser.on("--inspect-session PATH", "Print token-record key shapes only; never session content") { |value| options[:inspect] = value }
  parser.on("--check-recording STREAM", "Zero-live check of a canned Codex JSON stream; requires --answer PATH") { |value| options[:recording_stream] = value }
  parser.on("--answer PATH", "Answer artifact for --check-recording") { |value| options[:answer] = value }
  parser.on("--check-output-schema", "Print the generated output schema without making a live call") { options[:check_output_schema] = true }
  parser.on("--task-path PATH", "Validate observed session task path") { |value| options[:task_path] = value }
  parser.on("--model MODEL", "Record setting, or validate observed session model") { |value| options[:model] = value }
  parser.on("--reasoning-effort EFFORT", "Record setting, or validate observed session effort") { |value| options[:effort] = value }
  parser.on("--record", "Opt in to bounded live Codex sessions") { options[:record] = true }
  parser.on("--case NAME", CASES.keys, "composite, cold-resume, or routine-mutation") { |value| options[:benchmark_case] = value }
  parser.on("--representation NAME", REPRESENTATIONS, "graph or matched plan control") { |value| options[:representation] = value }
  parser.on("--scale NAME", SCALES.keys, "small or large") { |value| options[:scale] = value }
  parser.on("--repetitions N", Integer, "Live samples (1..#{MAX_REPETITIONS})") { |value| options[:repetitions] = value }
  parser.on("--timeout-seconds N", Integer, "Per-live-session timeout (1..600; default 300)") { |value| options[:timeout] = value }
  parser.on("--output PATH", "Write a reviewable JSON artifact") { |value| options[:output] = value }
  parser.on("-h", "--help", "Show help") { puts parser; exit }
end.parse!

begin
  if options[:check_output_schema]
    raise ArgumentError, "--check-output-schema cannot be combined" unless ARGV.empty? && !options[:record] && options[:sessions].empty? && !options[:recording_stream] && !options[:answer]
    puts JSON.generate(output_schema(CASES.fetch(options[:benchmark_case]).fetch(:expected)))
    exit
  end
  if options[:recording_stream]
    raise ArgumentError, "--check-recording requires --answer PATH" unless options[:answer]
    raise ArgumentError, "--check-recording cannot be combined" unless ARGV.empty? && !options[:record] && options[:sessions].empty?
    completed_answer!(File.binread(options[:recording_stream]), options[:answer], CASES.fetch(options[:benchmark_case]).fetch(:expected))
    puts "recording_check{status,live_calls}: valid,0"
    exit
  end
  if options[:check_fixture]
    raise ArgumentError, "--check-fixture cannot be combined" unless ARGV.empty? && !options[:record] && options[:sessions].empty?
    representations = %w[cold-resume routine-mutation].include?(options[:benchmark_case]) ? ["graph"] : REPRESENTATIONS
    variants = representations.product(SCALES.keys).map do |representation, scale|
      Dir.mktmpdir("kg-token-fixture-") do |dir|
        metadata = generate_fixture(dir, representation, scale, options[:benchmark_case])
        expected = CASES.fetch(options[:benchmark_case]).fetch(:expected)
        raise ArgumentError, "fixture prompt leaks expected answer" if expected.values.flatten.any? { |value| File.binread(File.join(dir, "TASK.txt")).include?(value) }
        if representation == "graph"
          graph_check = File.join(dir, ".agents/skills/knowledge-execution-graph/scripts/graph-check.rb")
          graph_args = options[:benchmark_case] == "composite" ? ["--allow-stale", "--allow-orphan", "TAS-060-unrouted-cleanup"] : []
          success = system("ruby", graph_check, *graph_args, File.join(dir, "nodes"), out: File::NULL, err: File::NULL)
          raise ArgumentError, "graph fixture structural check failed" unless success
          raise ArgumentError, "graph fixture does not copy the exact repository skill" unless File.binread(File.join(dir, ".agents/skills/knowledge-execution-graph/SKILL.md")) == File.binread(skill_source)
          raise ArgumentError, "graph fixture does not install the exact skill metadata" unless File.binread(File.join(dir, ".agents/skills/knowledge-execution-graph/agents/openai.yaml")) == File.binread(skill_metadata_source)
          if expected.key?("stale_dependents")
            raise ArgumentError, "graph fixture has unexpected stale dependencies" unless graph_fixture_facts(dir).fetch(:stale_dependents) == expected.fetch("stale_dependents")
          end
        end
        files = fixture_files(dir).length
        { representation: representation, scale: scale, files: files, **metadata }
      end
    end
    puts JSON.generate(protocol: "codex-session-token-v2", fixture_variants: variants)
    exit
  end
  if options[:inspect]
    raise ArgumentError, "--inspect-session cannot be combined" unless ARGV.empty? && !options[:record] && options[:sessions].empty?
    events = File.foreach(options[:inspect]).map { |line| JSON.parse(line) }
    safe_shapes = %w[session_meta turn_context].to_h do |type|
      fields = events.select { |event| event["type"] == type && event["payload"].is_a?(Hash) }
                     .flat_map { |event| event["payload"].keys.map(&:to_s) }.uniq.sort
      [type, fields]
    end
    puts JSON.generate(token_usage_record_payload_shapes: session_shapes(options[:inspect]), session_telemetry_fields: safe_shapes)
    exit
  end
  if options[:protocol]
    raise ArgumentError, "--protocol cannot be combined" unless ARGV.empty? && !options[:record] && options[:sessions].empty?
    protocol
    exit
  end
  raise ArgumentError, "--output is only valid with --record" if options[:output] && !options[:record]
  raise ArgumentError, "--timeout-seconds is only valid with --record" if options[:timeout] && !options[:record]
  if options[:record]
    raise ArgumentError, "--session is not valid with --record" unless options[:sessions].empty?
    raise ArgumentError, "--task-path is only valid with --session" if options[:task_path]
    raise ArgumentError, "--model and --reasoning-effort are required with --record" unless options[:model] && options[:effort]
    cli_version, version_status = Open3.capture2(codex_command, "--version")
    raise ArgumentError, "could not determine Codex CLI version" unless version_status.success?
    cli_version = cli_version.strip
    metadata = { requested_model: options[:model], requested_reasoning_effort: options[:effort], representation: options[:representation], scale: options[:scale], benchmark_case: options[:benchmark_case], requested_codex_version: cli_version }
    repetitions = options[:repetitions] || MAX_REPETITIONS
    raise ArgumentError, "repetitions must be 1 through #{MAX_REPETITIONS}" unless repetitions.between?(1, MAX_REPETITIONS)
    timeout_seconds = options[:timeout] || 300
    raise ArgumentError, "timeout must be 1 through 600 seconds" unless timeout_seconds.between?(1, 600)
    runs = repetitions.times.map do
      sessions_before = Dir.glob(File.join(session_root, "**", "*.jsonl"))
      Dir.mktmpdir("kg-token-benchmark-") do |dir|
        fixture = generate_fixture(dir, options[:representation], options[:scale], options[:benchmark_case])
        answer_path = File.join(dir, "answer.json")
        schema_path = File.join(dir, "answer.schema.json")
        fixture_before = fixture_files(dir).to_h { |path| [path.delete_prefix(dir + "/"), File.binread(path)] }
        command = [codex_command, "exec", "--json", "--ignore-user-config", "--ignore-rules", "-C", dir, "--model", options[:model], "-c", "model_reasoning_effort=#{options[:effort]}", "--sandbox", options[:benchmark_case] == "routine-mutation" ? "workspace-write" : "read-only"]
        command += ["--output-schema", schema_path] unless options[:benchmark_case] == "routine-mutation"
        command += ["--output-last-message", answer_path, "--", File.binread(File.join(dir, "TASK.txt"))]
        stdout, status = Timeout.timeout(timeout_seconds) { Open3.capture2e(*command) }
        raise ArgumentError, "live Codex run failed: #{stdout.lines.last&.strip}" unless status.success?
        if options[:benchmark_case] == "routine-mutation"
          completed_mutation!(stdout, answer_path, dir, fixture_before)
        else
          completed_answer!(stdout, answer_path, CASES.fetch(options[:benchmark_case]).fetch(:expected))
        end
        metadata.merge!(fixture)
        session_path = newest_session(sessions_before, dir)
        observations = assert_live_observations!(session_path, requested: { model: options[:model], effort: options[:effort] }, fixture_dir: dir, cli_version: cli_version)
        metadata[:observed_session_telemetry] = observations
        session_usage(session_path)
      end
    end
    emit_record(runs, metadata.merge(source: "fresh-codex-session"), options[:output])
  else
    raise ArgumentError, "provide --session or --record" if options[:sessions].empty?
    raise ArgumentError, "--repetitions is only valid with --record" if options[:repetitions]
    provenance = options[:sessions].map do |path|
      historical_session_provenance(path, expected: { model: options[:model], effort: options[:effort], task_path: options[:task_path] })
    end
    emit_historical_accounting(options[:sessions].map { |path| session_usage(path) }, provenance)
  end
rescue OptionParser::ParseError, ArgumentError, JSON::ParserError, Timeout::Error => error
  warn "error: #{error.message}"
  exit 2
end
