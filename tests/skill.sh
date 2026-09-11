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
abort "Markdown authority contract missing" unless text.include?("Markdown is the durable, human-visible authority") && text.include?("Obsidian-compatible")
abort "sidecar command boundary missing" unless text.include?("scripts/kg` command") && text.include?("do not have workers read or write SQLite directly")
abort "derived sidecar contract missing" unless text.include?("kg reindex [nodes]") && text.include?("FTS data from Markdown")
abort "sidecar authority split missing" unless text.include?("authoritative only for local operational coordination") && text.include?("kg allocate PREFIX") && text.include?("kg claim NODE AGENT")
abort "sidecar recovery contract missing" unless text.include?("Loss of the database may lose claims and indexes") && text.include?("kg init` then `kg reindex")
abort "same-host WAL boundary missing" unless text.include?("one host and a local filesystem") && text.include?("network-mounted") && text.include?("PostgreSQL")
abort "deferred stationary migration contract missing" unless text.include?("stationary-path/status-in-database migration is deferred")
abort "stationary status metadata became authoritative" if text.include?("stationary node metadata")
abort "global sequence ledger survived" if text.include?("sequence ledger") || text.include?("vault-wide revision")
abort "semantic context revision contract missing" unless text.include?("context_rev") && text.include?("not an edit counter")
abort "obsolete every-write revision rule survived" if text.include?("increment it on every write")
abort "actionable admission contract missing" unless text.include?("Admit a node only when") && text.include?("future decision or action")
abort "admission exclusions missing" unless text.include?("tool-call logs") && text.include?("routine narration or") && text.include?("duplicate source material")
abort "low-friction update-or-create rule missing" unless text.include?("Prefer updating the existing node") && text.include?("independently resumable outcome, blocker, dependency,")
abort "independent-resumability admission limit missing" unless text.include?("Independent resumability is\nnecessary but not sufficient") && text.include?("materially reduce future resumption cost")
abort "non-durable boundary exclusions missing" unless text.include?("Agent boundaries, exclusive write-set") && text.include?("failed checks, incidental or mechanical cleanup, routine") && text.include?("verification, and handoffs alone never qualify")
abort "same-node fresh-worker contract missing" unless text.include?("A fresh worker may continue the same graph\nnode; agents and nodes are not one-to-one")
abort "parallel advisory-state contract missing" unless text.include?("advisory navigation, never a work claim")
abort "parallel coordinator assignment contract missing" unless text.include?("coordinator assigns each worker a direct node path and an exclusive write set")
abort "parallel one-writer contract missing" unless text.include?("One agent writes a node and its status path at a time")
abort "parallel shared-state serialization contract missing" unless text.include?("Shared parents, `index-map.md`, definitions, and root hubs are coordinator-owned") && text.include?("explicitly serialized")
abort "parallel worktree snapshot contract missing" unless text.include?("A worktree is a snapshot, not global truth")
abort "parallel parent-resolution contract missing" unless text.include?("alone resolves a coordinating parent after all required child work is integrated")
abort "parallel ID allocation contract missing" unless text.include?("kg allocate PREFIX") && text.include?("Coordinator preallocation") && text.include?("explicitly disjoint numeric ranges")
abort "parallel local collision detection contract missing" unless text.include?("checks for an existing collision only; it is never an ID reservation")
abort "parallel atomic reservation contract missing" unless text.include?("kg allocate PREFIX` to atomically reserve an ID")
abort "parallel branch-local claim limitation missing" unless text.include?("Branch-local `owner` or claim metadata is insufficient")
abort "worker integration-base contract missing" unless text.include?("worker records the integration base and its assigned node path and write set")
abort "worker sidecar claim contract missing" unless text.include?("hashes its starting Markdown node, and claims it with `kg claim`") && text.include?("then release the matching claim")
abort "worktree-slice node-boundary limit missing" unless text.include?("A worktree slice is not a node boundary: a fresh worker may continue the assigned node")
abort "coherent worker handoff contract missing" unless text.include?("content update and its status move coherent in one commit or handoff bundle")
abort "worker write-set verification contract missing" unless text.include?("verify every changed, created, and moved path remains in that assigned write set")
abort "worker handoff evidence contract missing" unless text.include?("Report the base, touched paths, created paths, moved paths, dependency evidence, and test evidence")
abort "serial coordinator integration contract missing" unless text.include?("coordinator integrates worker branches one at a time")
abort "same-node divergence reconciliation contract missing" unless text.include?("Never blindly auto-merge an upstream change to the assigned node or divergent status paths") && text.include?("manual semantic reconciliation")
abort "post-integration graph validation contract missing" unless text.include?("After each integration, run `ruby scripts/graph-check.rb nodes`")
abort "exact stale-dependency search contract missing" unless text.include?("exact `rg -n -F 'Depends on [[ID]] at context_rev '` searches")
abort "stale consumer execution barrier missing" unless text.include?("reconcile stale consumers before their dependent execution")
abort "integrated child evidence parent barrier missing" unless text.include?("only after its required child evidence has been integrated")
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
  abort "invalid context_rev: #{path}" unless metadata["context_rev"].is_a?(Integer) && metadata["context_rev"].positive?
  updated = header[/^updated: ([^\n]+)$/, 1]
  abort "invalid updated: #{path}" unless updated&.match?(/\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\z/)
  abort "missing summary: #{path}" unless metadata["summary"].is_a?(String) && !metadata["summary"].empty?
  forbidden = metadata.keys & %w[id type status seq mtime rev]
  abort "duplicated authority in #{path}: #{forbidden.join(',')}" unless forbidden.empty?
  if %w[active proposed].include?(status) && File.basename(path).start_with?("TAS-")
    abort "missing next: #{path}" unless metadata["next"].is_a?(String) && !metadata["next"].empty?
  end
  if status == "resolved" && metadata.key?("next")
    abort "resolved node retains next: #{path}"
  end
  text.scan(/(?:Depends on|Implements|Requires|Governed by) \[\[[^\]]+\]\](?! at context_rev \d+)/) do |edge|
    abort "unpinned dependency in #{path}: #{edge}"
  end
  if text.match?(/(?:Child|Parent of|Indexed by|Depended on by|Supersedes|Backlink) \[\[/)
    abort "stored reciprocal relationship in #{path}"
  end
  text.scan(/\[\[([^\]]+)\]\]/).flatten.each do |target|
    next if target == "index-map"
    abort "missing link target #{target} from #{path}" unless by_name.key?(target)
  end
end

index = File.read("nodes/index-map.md")
abort "index contains a node-state table" if index.match?(/^\| .*\[\[/)
abort "index lacks authority warning" unless index.include?("not copied node state")
abort "index lacks canonical Indexes route" unless index.match?(/Indexes \[\[/)
root_hubs = index.scan(/^\s*- Indexes \[\[([^\]]+)\]\]/).flatten.uniq
abort "index lacks IDX root hub" if root_hubs.empty?
root_hubs.each do |target|
  abort "root hub is not IDX: #{target}" unless target.match?(/\AIDX-\d+/)
end
index.scan(/\[\[([^\]]+)\]\]/).flatten.each do |target|
  next unless target.match?(/\A[A-Z]+-\d+/)
  abort "missing index target #{target}" unless by_name.key?(target)
end
focus_targets = index[/^# Focus\n(.*?)(?=^# |\z)/m, 1].to_s.scan(/\[\[([^\]]+)\]\]/).flatten.uniq
root_hubs.each do |hub|
  text = File.read(by_name.fetch(hub))
  abort "root hub has primary route: #{hub}" if text.match?(/^(?:Parent|Area) \[\[/)
end

primary_routes = {}
paths.each do |path|
  routes = File.read(path).scan(/^(?:Parent|Area) \[\[([^\]]+)\]\]\./).flatten
  name = File.basename(path, ".md")
  if root_hubs.include?(name)
    abort "root hub has primary route: #{name}" unless routes.empty?
  else
    abort "missing or multiple primary routes: #{path}" unless routes.length == 1
    primary_routes[name] = routes.first
  end
end

paths.each do |path|
  metadata = YAML.safe_load(path.then { |p| File.read(p).split(/^---\s*$/, 3)[1] }, permitted_classes: [Time])
  frontier = metadata["next"]
  next unless frontier
  targets = frontier.scan(/\[\[([^\]]+)\]\]/)
  abort "multiple child frontiers: #{path}" if targets.length > 1
  next if targets.empty?
  target = targets.first.first
  name = File.basename(path, ".md")
  abort "frontier is not a direct child: #{path}" unless primary_routes[target] == name
end

unfinished = paths.reject { |path| File.dirname(path).end_with?("/resolved") }
unfinished.each do |path|
  name = File.basename(path, ".md")
  seen = {}
  until root_hubs.include?(name) || focus_targets.include?(name)
    abort "orphan unfinished node: #{File.basename(path, '.md')}" if seen[name] || !primary_routes.key?(name)
    seen[name] = true
    name = primary_routes.fetch(name)
  end
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

ruby scripts/graph-check.rb nodes

ruby <<'RUBY'
text = File.read("SKILL.md")
abort "canonical edge-direction contract missing" unless text.include?("Store each relationship in one canonical direction")
abort "child ownership contract missing" unless text.include?("put `Parent` on the child")
abort "derived inverse-edge contract missing" unless text.include?("do not store them as reciprocal edges")
abort "primary Parent-or-Area contract missing" unless text.include?("exactly one primary")
abort "orphan-unfinished-node contract missing" unless text.include?("orphan")
abort "just-in-time decomposition contract missing" unless text.include?("Decompose just in time") && text.include?("independently resumable")
abort "decomposition durable-value threshold missing" unless text.include?("verification boundary that also retains durable execution-memory value")
abort "frontier contract missing" unless text.include?("one concrete frontier action") && text.include?("one wikilinked direct child")
abort "evidence-based roll-up contract missing" unless text.include?("Roll up from evidence") && text.include?("resolving children alone does not complete the parent")
abort "decision-node convention missing" unless text.include?("A `DEC` node records a settled choice")
abort "resolved-knowledge validity contract missing" unless text.include?("resolved `DEF` or `DEC` is current knowledge")
puts "canonical edge direction: passed"
RUBY

ruby <<'RUBY'
parent = File.read("nodes/resolved/TAS-008-fit-for-purpose-hardening.md")
child = File.read("nodes/resolved/TAS-012-decomposition-rollup.md")
admission = File.read("nodes/resolved/TAS-016-actionable-admission-policy.md")
abort "decomposition parent lacks outcome" unless parent.include?("# Outcome\n")
abort "decomposition parent lacks completion criteria" unless parent.include?("# Done when\n")
frontier = parent[/^next: (.+)$/m, 1]
abort "resolved hardening task retains next" if frontier
abort "resolved decomposition node lacks outcome" unless child.include?("# Outcome\n")
abort "resolved decomposition node lacks completion criteria" unless child.include?("# Done when\n")
abort "resolved decomposition node lacks roll-up evidence" unless child.include?("# Result\n")
abort "resolved decomposition node lacks canonical parent" unless child.include?("Parent [[TAS-008-fit-for-purpose-hardening]].")
abort "resolved admission node retains next" if admission.match?(/^next:/)
abort "resolved admission node lacks result evidence" unless admission.include?("# Result\n")
abort "resolved admission node lacks canonical parent" unless admission.include?("Parent [[TAS-008-fit-for-purpose-hardening]].")
puts "decomposition roll-up: passed"
RUBY

ruby <<'RUBY'
storage = File.read("nodes/resolved/TAS-017-stationary-canonical-storage.md")
parent = File.read("nodes/resolved/TAS-008-fit-for-purpose-hardening.md")
abort "storage decision retains next" if storage.match?(/^next:/)
abort "storage decision lacks recorded evidence" unless storage.include?("# Result\n") && storage.include?("storage-comparison.rb")
abort "hardening roll-up lacks storage evidence" unless parent.include?("TAS-017") && parent.include?("# Result\n")
puts "stationary-storage decision: passed"
RUBY

ruby <<'RUBY'
decision = File.read("nodes/resolved/DEC-001-decision-node-convention.md")
task = File.read("nodes/resolved/TAS-013-decision-memory.md")
%w[Decision Rationale Consequences].each do |section|
  abort "decision node lacks #{section}" unless decision.include?("# #{section}\n")
end
abort "decision node lacks canonical parent" unless decision.include?("Parent [[TAS-013-decision-memory]].")
abort "decision node incorrectly marked obsolete" if decision.match?(/^disposition:/)
abort "decision-memory task retains next" if task.match?(/^next:/)
abort "decision-memory task lacks evidence" unless task.include?("# Result\n")
puts "decision lifecycle: passed"
RUBY
