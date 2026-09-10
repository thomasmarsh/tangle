#!/bin/sh
set -eu

ruby <<'RUBY'
require "time"
require "yaml"

text = File.read("SKILL.md")
abort "missing frontmatter" unless text.start_with?("---\n")
metadata = YAML.safe_load(text.split(/^---\s*$/, 3)[1])
abort "invalid name" unless metadata["name"] == "knowledge-execution-graph"
abort "missing description" unless metadata["description"].is_a?(String)
abort "missing status-directory contract" unless %w[proposed active blocked resolved].all? { |status| text.include?("nodes/#{status}/") }
abort "global sequence ledger survived" if text.include?("sequence ledger") || text.include?("vault-wide revision")
puts "skill contract: passed"
RUBY

ruby <<'RUBY'
require "time"
require "yaml"

allowed_statuses = %w[proposed active blocked resolved]
paths = Dir["nodes/*/*.md"].sort
abort "missing graph nodes" if paths.empty?

by_name = paths.to_h { |path| [File.basename(path, ".md"), path] }
abort "duplicate node basename" unless by_name.length == paths.length

paths.each do |path|
  text = File.read(path)
  abort "missing frontmatter: #{path}" unless text.start_with?("---\n")
  header = text.split(/^---\s*$/, 3)[1]
  metadata = YAML.safe_load(header, permitted_classes: [Time])
  status = File.basename(File.dirname(path))
  abort "invalid status directory: #{path}" unless allowed_statuses.include?(status)
  abort "invalid rev: #{path}" unless metadata["rev"].is_a?(Integer) && metadata["rev"].positive?
  updated = header[/^updated: ([^\n]+)$/, 1]
  abort "invalid updated: #{path}" unless updated&.match?(/\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\z/)
  abort "missing summary: #{path}" unless metadata["summary"].is_a?(String) && !metadata["summary"].empty?
  forbidden = metadata.keys & %w[id type status seq mtime]
  abort "duplicated authority in #{path}: #{forbidden.join(',')}" unless forbidden.empty?
  if %w[active proposed].include?(status) && File.basename(path).start_with?("TAS-")
    abort "missing next: #{path}" unless metadata["next"].is_a?(String) && !metadata["next"].empty?
  end
  if status == "resolved" && metadata.key?("next")
    abort "resolved node retains next: #{path}"
  end
  text.scan(/(?:Depends on|Implements|Requires|Governed by) \[\[[^\]]+\]\](?! at rev \d+)/) do |edge|
    abort "unpinned dependency in #{path}: #{edge}"
  end
  text.scan(/\[\[([^\]]+)\]\]/).flatten.each do |target|
    next if target == "index-map"
    abort "missing link target #{target} from #{path}" unless by_name.key?(target)
  end
end

index = File.read("nodes/index-map.md")
abort "index contains a node-state table" if index.match?(/^\| .*\[\[/)
abort "index lacks authority warning" unless index.include?("not copied node state")
index.scan(/\[\[([^\]]+)\]\]/).flatten.each do |target|
  next unless target.match?(/\A[A-Z]+-\d+/)
  abort "missing index target #{target}" unless by_name.key?(target)
end
active_tasks = paths.select { |path| File.dirname(path).end_with?("/active") && File.basename(path).start_with?("TAS-") }
focus = index[/^# Focus\n(.*?)(?=^# |\z)/m, 1]
if active_tasks.empty?
  abort "focus remains without active work" if focus
elsif focus
  focus.scan(/\[\[([^\]]+)\]\]/).flatten.each do |target|
    path = by_name[target]
    abort "focus target is not active: #{target}" unless path && File.dirname(path).end_with?("/active")
  end
end
puts "graph invariants: passed"
RUBY
