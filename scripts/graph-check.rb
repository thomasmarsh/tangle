#!/usr/bin/env ruby
# frozen_string_literal: true

# Read-only validator for a Knowledge Execution Graph vault. It deliberately
# keeps no cache or state: use it from a vault root, or pass its nodes directory.
require "time"
require "yaml"

STATUSES = %w[proposed active blocked resolved].freeze
CONTEXT_EDGES = %w[Depends\ on Implements Requires Governed\ by].freeze
RECIPROCAL_EDGE = /(?:Child|Parent of|Indexed by|Depended on by|Supersedes|Backlink)\s+\[\[/.freeze

def fail_with(errors)
  errors.each { |error| warn "error: #{error}" }
  exit 1
end

allow_stale = false
allowed_orphans = []
arguments = ARGV.dup
while arguments.first&.start_with?("--")
  case arguments.shift
  when "--allow-stale"
    allow_stale = true
  when "--allow-orphan"
    allowed_orphans << arguments.shift
  when "-h", "--help"
    puts "usage: ruby scripts/graph-check.rb [--allow-stale] [--allow-orphan NODE] [nodes-directory]"
    puts "Validate a file-only Knowledge Execution Graph without writing state."
    exit 0
  else
    fail_with(["unknown option"])
  end
end
nodes_dir = arguments.fetch(0, "nodes")
if arguments.length > 1
  puts "usage: ruby scripts/graph-check.rb [--allow-stale] [--allow-orphan NODE] [nodes-directory]"
  puts "Validate a file-only Knowledge Execution Graph without writing state."
  exit 2
end

errors = []
fail_with(["nodes directory does not exist: #{nodes_dir}"]) unless File.directory?(nodes_dir)
paths = Dir.glob(File.join(nodes_dir, "*", "*.md")).sort
errors << "no node files under #{nodes_dir}" if paths.empty?
nodes = []
paths.each do |path|
  status = File.basename(File.dirname(path))
  name = File.basename(path, ".md")
  text = File.read(path)
  unless STATUSES.include?(status)
    errors << "#{path}: invalid status directory #{status}"
    next
  end
  unless text.start_with?("---\n") && (parts = text.split(/^---\s*$/, 3)).length >= 3
    errors << "#{path}: missing frontmatter"
    next
  end
  header = parts[1]
  begin
    metadata = YAML.safe_load(header, permitted_classes: [Time], aliases: false)
  rescue Psych::Exception => e
    errors << "#{path}: invalid frontmatter: #{e.message.lines.first.strip}"
    next
  end
  unless metadata.is_a?(Hash)
    errors << "#{path}: frontmatter must be a mapping"
    next
  end
  errors << "#{path}: context_rev must be a positive integer" unless metadata["context_rev"].is_a?(Integer) && metadata["context_rev"].positive?
  updated = header[/^updated: ([^\n]+)$/, 1]
  errors << "#{path}: updated must be UTC ISO-8601" unless updated&.match?(/\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\z/)
  errors << "#{path}: summary is required" unless metadata["summary"].is_a?(String) && !metadata["summary"].empty?
  forbidden = metadata.keys & %w[id type status seq mtime rev]
  errors << "#{path}: duplicated authority fields: #{forbidden.join(', ')}" unless forbidden.empty?
  if %w[active proposed].include?(status) && name.start_with?("TAS-")
    errors << "#{path}: unfinished task requires next" unless metadata["next"].is_a?(String) && !metadata["next"].empty?
  end
  errors << "#{path}: resolved node must omit next" if status == "resolved" && metadata.key?("next")
  errors << "#{path}: stored reciprocal edge" if text.match?(RECIPROCAL_EDGE)
  nodes << { path: path, name: name, id: name[/\A[A-Z]+-\d+/], status: status, text: text, metadata: metadata }
end

by_name = nodes.group_by { |node| node[:name] }
by_name.each { |name, matches| errors << "duplicate node identity: #{name}" if matches.length > 1 }
by_id = nodes.group_by { |node| node[:id] }
by_id.each { |id, matches| errors << "duplicate node identity: #{id || matches.first[:name]}" if matches.length > 1 }

index_path = File.join(nodes_dir, "index-map.md")
index = File.file?(index_path) ? File.read(index_path) : ""
errors << "missing index-map.md" unless File.file?(index_path)
errors << "index-map.md contains copied node-state table" if index.match?(/^\| .*\[\[/)
root_hubs = index.scan(/^\s*- Indexes \[\[([^\]]+)\]\]/).flatten.uniq
errors << "index-map.md lacks an Indexes root route" if root_hubs.empty?
root_hubs.each { |hub| errors << "root hub is not IDX: #{hub}" unless hub.match?(/\AIDX-\d+/) }
focus = index[/^# Focus\n(.*?)(?=^# |\z)/m, 1].to_s.scan(/\[\[([^\]]+)\]\]/).flatten.uniq

nodes.each do |node|
  node[:text].scan(/\[\[([^\]]+)\]\]/).flatten.each do |target|
    errors << "#{node[:path]}: broken link [[#{target}]]" unless by_name.key?(target)
  end
  node[:text].scan(/^(?:#{CONTEXT_EDGES.join('|')})\s+\[\[([^\]]+)\]\](.*)$/).each do |target, suffix|
    pin_match = /\A at context_rev (\d+)\.\z/.match(suffix)
    pin = pin_match && pin_match[1].to_i
    unless pin
      errors << "#{node[:path]}: invalid or missing context_rev pin for [[#{target}]]"
      next
    end
    target_node = by_name[target]&.first
    next unless target_node
    errors << "#{node[:path]}: context_rev mismatch for [[#{target}]] (pinned #{pin}, current #{target_node[:metadata]['context_rev']})" if !allow_stale && target_node[:metadata]["context_rev"] != pin
  end
end
index.scan(/\[\[([A-Z]+-\d+[^\]]*)\]\]/).flatten.each do |target|
  errors << "index-map.md: broken link [[#{target}]]" unless by_name.key?(target)
end

routes = {}
nodes.each do |node|
  found = node[:text].scan(/^(?:Parent|Area) \[\[([^\]]+)\]\]\./).flatten
  if root_hubs.include?(node[:name])
    errors << "#{node[:path]}: root hub must not have Parent or Area" unless found.empty?
  elsif found.length != 1 && !allowed_orphans.include?(node[:name])
    errors << "#{node[:path]}: requires exactly one primary Parent or Area route"
  else
    routes[node[:name]] = found.first
  end
end

nodes.each do |node|
  next unless node[:metadata]["next"]
  frontier = node[:metadata]["next"].scan(/\[\[([^\]]+)\]\]/).flatten
  errors << "#{node[:path]}: next names multiple frontier nodes" if frontier.length > 1
  errors << "#{node[:path]}: frontier is not a direct child" if frontier.length == 1 && routes[frontier.first] != node[:name]
end

nodes.reject { |node| node[:status] == "resolved" }.each do |node|
  current = node[:name]
  seen = {}
  until root_hubs.include?(current) || focus.include?(current)
    if seen[current]
      errors << "#{node[:path]}: parent cycle at #{current}"
      break
    end
    seen[current] = true
    unless routes.key?(current)
      errors << "#{node[:path]}: orphan unfinished node" unless allowed_orphans.include?(node[:name]) || allowed_orphans.include?(node[:id])
      break
    end
    current = routes[current]
  end
end
active_tasks = nodes.select { |node| node[:status] == "active" && node[:name].start_with?("TAS-") }
errors << "index-map.md: Focus remains without active tasks" if active_tasks.empty? && !focus.empty?
focus.each do |target|
  target_node = by_name[target]&.first
  errors << "index-map.md: Focus target is not active: #{target}" unless target_node && target_node[:status] == "active"
end

fail_with(errors) unless errors.empty?
puts "graph check: passed (#{nodes.length} nodes)"
