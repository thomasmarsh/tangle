#!/usr/bin/env ruby
# frozen_string_literal: true

# Deterministic, offline filesystem diagnostic for the file-only graph. It
# creates a realistic cold-resumption corpus and measures bounded local reads;
# it is not a model-token benchmark.
require "fileutils"
require "tmpdir"
require "time"
require "yaml"

ROOT = "IDX-900-execution-memory"
BASELINE = File.expand_path("../benchmark/behavioral-baseline.txt", __dir__)
DEFAULT_SCALES = [100, 1000].freeze
MAX_SCALE = 10_000

def usage
  puts "usage: ruby scripts/behavioral-benchmark.rb [--scales N,N] [--verify]"
  puts "Generate temporary fixtures and report secondary filesystem diagnostics."
end

def parse_options(argv)
  scales = DEFAULT_SCALES
  verify = false
  until argv.empty?
    case argv.shift
    when "--verify" then verify = true
    when "--scales"
      value = argv.shift or raise ArgumentError, "--scales requires N,N"
      scales = value.split(",").map { |n| Integer(n, 10) }
    when "-h", "--help" then usage; exit 0
    else raise ArgumentError, "unknown option"
    end
  end
  raise ArgumentError, "scales must be 13 through #{MAX_SCALE}" unless scales.all? { |scale| scale.between?(13, MAX_SCALE) }
  [scales.uniq, verify]
end

def node(rev:, summary:, body:, priority: nil, next_action: nil, disposition: nil)
  fields = ["---", "context_rev: #{rev}"]
  fields << "priority: #{priority}" if priority
  fields << "updated: 2026-01-15T12:00:00Z"
  fields << "summary: #{summary}"
  fields << "next: #{next_action}" if next_action
  fields << "disposition: #{disposition}" if disposition
  (fields + ["---", "", body, ""]).join("\n")
end

def write_fixture(root, scale)
  %w[proposed active blocked resolved].each { |status| FileUtils.mkdir_p(File.join(root, status)) }
  write = lambda { |status, name, text| File.write(File.join(root, status, "#{name}.md"), text) }
  File.write(File.join(root, "index-map.md"), "# Root hubs\n\n- Indexes [[#{ROOT}]]: benchmark execution-memory route.\n")
  write.call("resolved", ROOT, node(rev: 1, summary: "Durable root for benchmark work.", body: "# Invariant\n\nRoot hub."))
  write.call("resolved", "DEF-900-routing", node(rev: 2, summary: "Token routing invariant.", body: "# Context\n\nArea [[#{ROOT}]].\n\n# Invariant\n\nUse the current routing rule."))
  write.call("resolved", "DEC-900-routing-v1", node(rev: 1, summary: "Old token routing decision.", disposition: "superseded", body: "# Context\n\nArea [[#{ROOT}]].\n\nSuperseded by [[DEC-901-routing-v2]]."))
  write.call("resolved", "DEC-901-routing-v2", node(rev: 1, summary: "Current token routing decision.", body: "# Context\n\nArea [[#{ROOT}]].\n\n# Decision\n\nUse the current routing rule."))
  (scale - 5).times do |i|
    id = format("TAS-%05d", i + 1)
    # The cold-resume record must be executable, not merely historically P0.
    status = i == 7 ? "active" : %w[active proposed blocked resolved][i % 4]
    priority = i == 7 ? "P0" : "P2"
    pin = i.even? ? 2 : 1
    topic = i == 7 ? "Cold-resume token routing incident." : "Routine maintenance record #{i}."
    body = "# Context\n\nArea [[#{ROOT}]].\n\nDepends on [[DEF-900-routing]] at context_rev #{pin}.\n\n# Outcome\n\n#{topic}\n"
    next_action = status == "resolved" ? nil : "Inspect the current routing invariant."
    write.call(status, id, node(rev: 1, summary: topic, priority: priority, next_action: next_action, body: body))
  end
  # An unfinished disconnected record is an actionable integrity failure.
  write.call("active", "TAS-99999-orphan", node(rev: 1, summary: "Disconnected actionable record.", next_action: "Restore its primary route.", body: "# Context\n\nParent [[MISSING-900]]."))
end

def metadata(text)
  YAML.safe_load(text.split(/^---\s*$/, 3).fetch(1), permitted_classes: [Time], aliases: false)
end

def assert_result(label, actual, expected)
  return if actual == expected
  abort "fixture workflow failure for #{label}: expected #{expected.inspect}, got #{actual.inspect}"
end

def scan(paths)
  reads = 0
  bytes = 0
  paths.each do |path|
    text = File.read(path)
    reads += 1
    bytes += text.bytesize
    yield(path, text) if block_given?
  end
  [reads, bytes]
end

def run_scale(scale)
  Dir.mktmpdir("kg-behavioral-") do |root|
    write_fixture(root, scale)
    paths = Dir.glob(File.join(root, "*", "*.md")).sort
    work = { reads: 0, bytes: 0 }
    measure = lambda do |&block|
      started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      result, reads, bytes = block.call
      work[:reads] += reads
      work[:bytes] += bytes
      [result, ((Process.clock_gettime(Process::CLOCK_MONOTONIC) - started) * 1000).round(2)]
    end
    resume, resume_ms = measure.call do
      route = File.read(File.join(root, "index-map.md"))
      abort "fixture lacks root route" unless route.include?("Indexes [[#{ROOT}]]")
      hits = []
      reads, bytes = scan(paths) do |path, text|
        fields = metadata(text)
        next unless File.dirname(path).end_with?("/active") && fields["priority"] == "P0" && text.include?("Cold-resume token routing incident.")
        abort "cold resume selected a task without an executable next action" unless fields["next"] == "Inspect the current routing invariant."
        hits << File.basename(path, ".md")
      end
      assert_result("cold resume", hits, ["TAS-00008"])
      [hits, reads + 1, bytes + route.bytesize]
    end
    current, current_ms = measure.call do
      hits = []
      reads, bytes = scan(paths) do |path, text|
        fields = metadata(text)
        hits << File.basename(path, ".md") if File.basename(path).start_with?("DEC-") && !fields.key?("disposition") && text.include?("# Decision\n")
      end
      assert_result("current decision", hits, ["DEC-901-routing-v2"])
      [hits, reads, bytes]
    end
    stale, stale_ms = measure.call do
      definition = File.read(File.join(root, "resolved", "DEF-900-routing.md"))
      current_rev = definition[/^context_rev: (\d+)$/, 1]
      hits = []
      reads, bytes = scan(paths) do |path, text|
        pin = text[/Depends on \[\[DEF-900-routing\]\] at context_rev (\d+)\./, 1]
        hits << File.basename(path, ".md") if pin && pin != current_rev
      end
      assert_result("stale dependencies", hits.length, (scale - 5) / 2)
      [hits, reads + 1, bytes + definition.bytesize]
    end
    orphans, orphan_ms = measure.call do
      known = paths.map { |path| File.basename(path, ".md") }.to_h { |name| [name, true] }
      hits = []
      reads, bytes = scan(paths) do |path, text|
        target = text[/^(?:Parent|Area) \[\[([^\]]+)\]\]\./, 1]
        hits << File.basename(path, ".md") if target && !known[target] && File.dirname(path).end_with?("/active")
      end
      assert_result("unfinished orphan discovery", hits, ["TAS-99999-orphan"])
      [hits, reads, bytes]
    end
    { scale: scale, nodes: paths.length, reads: work[:reads], bytes: work[:bytes], resume: resume.length, current: current.length, stale: stale.length, orphan: orphans.length, work_units: work[:reads] + work[:bytes], ms: [resume_ms, current_ms, stale_ms, orphan_ms] }
  end
end

def baseline
  File.readlines(BASELINE, chomp: true).filter_map do |line|
    next if line.empty? || line.start_with?("#")
    scale, values = line.split(":", 2)
    [Integer(scale, 10), values.split(",").map { |v| Integer(v, 10) }]
  end.to_h
end

begin
  scales, verify = parse_options(ARGV)
  expected = baseline
  missing = scales - expected.keys
  abort "no tracked baseline for scale(s): #{missing.join(',')}" if verify && !missing.empty?
  scales.map { |scale| run_scale(scale) }.each do |r|
    metrics = [r[:nodes], r[:reads], r[:bytes], r[:resume], r[:current], r[:stale], r[:orphan], r[:work_units]]
    abort "baseline mismatch at scale #{r[:scale]}: expected #{expected.fetch(r[:scale]).join(',')}, got #{metrics.join(',')}" if verify && expected.fetch(r[:scale]) != metrics
    puts format("filesystem_diagnostic{scale,nodes,reads,bytes,resume,current,stale,orphan,work_units,ms}: %d,%d,%d,%d,%d,%d,%d,%d,%d,%.2f/%.2f/%.2f/%.2f", r[:scale], *metrics, *r[:ms])
  end
  puts "verification: passed" if verify
rescue ArgumentError => e
  warn "error: #{e.message}"
  usage
  exit 2
end
