#!/usr/bin/env ruby
# frozen_string_literal: true

# Offline comparison of four status representations.  It creates disposable
# Git repositories only; no fixture, cache, or status view is retained.
require "fileutils"
require "open3"
require "tmpdir"

NODES = 100
ACTIVE = 25
BASELINE = File.expand_path("../benchmark/storage-comparison-baseline.txt", __dir__)

def run(*command, chdir:)
  out, status = Open3.capture2e(*command, chdir: chdir)
  raise "#{command.join(" ")}: #{out}" unless status.success?
  out
end

def node(id, status = nil)
  metadata = ["---", "context_rev: 1", "updated: 2026-09-10T00:00:00Z", "summary: Fixture #{id}."]
  metadata << "status: #{status}" if status
  (metadata + ["---", "", "Area [[IDX-900-root]].", ""]).join("\n")
end

def git_setup(root)
  run("git", "init", "-q", chdir: root)
  run("git", "config", "user.email", "fixture@example.invalid", chdir: root)
  run("git", "config", "user.name", "Fixture", chdir: root)
end

def commit(root, message)
  run("git", "add", ".", chdir: root)
  run("git", "commit", "-qm", message, chdir: root)
end

def merge_conflicts(root, transition)
  base = run("git", "branch", "--show-current", chdir: root).strip
  run("git", "checkout", "-qb", "left", chdir: root)
  transition.call("TAS-00001")
  commit(root, "left transition")
  run("git", "checkout", "-q", base, chdir: root)
  run("git", "checkout", "-qb", "right", chdir: root)
  transition.call("TAS-00002")
  commit(root, "right transition")
  output, status = Open3.capture2e("git", "merge", "left", chdir: root)
  status.success? ? 0 : output.scan(/^UU /).length + output.scan(/^CONFLICT /).length
end

def diff_shape(root, transition)
  transition.call("TAS-00003")
  run("git", "add", "-A", chdir: root)
  codes = run("git", "diff", "--cached", "--name-status", "-M", chdir: root).lines.map(&:split).map(&:first)
  [codes.sort.join("+"), codes.sum { |code| code.start_with?("R", "C") ? 2 : 1 }]
end

def restore(root)
  run("git", "reset", "--hard", "-q", "HEAD", chdir: root)
  run("git", "clean", "-fdq", chdir: root)
end

def status_count(paths)
  paths.count { |path| File.exist?(path) }
end

def directory_case(root)
  %w[active proposed blocked resolved].each { |status| FileUtils.mkdir_p(File.join(root, "nodes", status)) }
  NODES.times do |i|
    id = format("TAS-%05d", i + 1)
    status = i < ACTIVE ? "active" : "resolved"
    File.write(File.join(root, "nodes", status, "#{id}.md"), node(id))
  end
  query_entries = status_count(Dir.glob(File.join(root, "nodes", "active", "*.md")))
  commit(root, "baseline")
  transition = lambda do |id|
    FileUtils.mv(File.join(root, "nodes", "active", "#{id}.md"), File.join(root, "nodes", "resolved", "#{id}.md"))
  end
  shape, paths = diff_shape(root, transition)
  restore(root)
  conflicts = merge_conflicts(root, transition)
  { shape: shape, paths: paths, query_reads: 0, query_entries: query_entries, conflicts: conflicts, stale: 0, stable: 0 }
end

def stationary_case(root)
  canonical = File.join(root, "nodes", "canonical")
  NODES.times do |i|
    id = format("TAS-%05d", i + 1)
    FileUtils.mkdir_p(File.join(canonical, id[-2, 2]))
    File.write(File.join(canonical, id[-2, 2], "#{id}.md"), node(id, i < ACTIVE ? "active" : "resolved"))
  end
  paths = Dir.glob(File.join(canonical, "*", "*.md"))
  query_entries = paths.count { |path| File.read(path).include?("status: active") }
  commit(root, "baseline")
  transition = lambda do |id|
    path = Dir.glob(File.join(canonical, "*", "#{id}.md")).fetch(0)
    File.write(path, File.read(path).sub("status: active", "status: resolved"))
  end
  shape, paths_changed = diff_shape(root, transition)
  restore(root)
  conflicts = merge_conflicts(root, transition)
  { shape: shape, paths: paths_changed, query_reads: paths.length, query_entries: query_entries, conflicts: conflicts, stale: 0, stable: 1 }
end

def symlink_case(root)
  canonical = File.join(root, "nodes", "canonical")
  %w[active resolved].each { |status| FileUtils.mkdir_p(File.join(root, "nodes", "status", status)) }
  NODES.times do |i|
    id = format("TAS-%05d", i + 1)
    source = File.join(canonical, id[-2, 2], "#{id}.md")
    FileUtils.mkdir_p(File.dirname(source))
    File.write(source, node(id))
    status = i < ACTIVE ? "active" : "resolved"
    File.symlink(File.join("..", "..", "canonical", id[-2, 2], "#{id}.md"), File.join(root, "nodes", "status", status, "#{id}.md"))
  end
  query_entries = status_count(Dir.glob(File.join(root, "nodes", "status", "active", "*.md")))
  commit(root, "baseline")
  transition = lambda do |id|
    old = File.join(root, "nodes", "status", "active", "#{id}.md")
    new = File.join(root, "nodes", "status", "resolved", "#{id}.md")
    FileUtils.mv(old, new)
  end
  shape, paths = diff_shape(root, transition)
  restore(root)
  conflicts = merge_conflicts(root, transition)
  # A deleted view entry is invisible to a directory query although its canonical
  # node still exists; this is the stale/broken-view failure mode.
  FileUtils.rm(File.join(root, "nodes", "status", "active", "TAS-00004.md"))
  stale_link = File.join(root, "nodes", "status", "active", "TAS-00004.md")
  source = Dir.glob(File.join(canonical, "*", "TAS-00004.md")).fetch(0)
  stale = File.exist?(source) && !File.exist?(stale_link) ? 1 : 0
  { shape: shape, paths: paths, query_reads: 0, query_entries: query_entries, conflicts: conflicts, stale: stale, stable: 1 }
end

def index_case(root)
  canonical = File.join(root, "nodes", "canonical")
  NODES.times do |i|
    id = format("TAS-%05d", i + 1)
    FileUtils.mkdir_p(File.join(canonical, id[-2, 2]))
    File.write(File.join(canonical, id[-2, 2], "#{id}.md"), node(id))
  end
  active = (1..ACTIVE).map { |n| format("TAS-%05d", n) }
  index_path = File.join(root, "nodes", "status-index.md")
  write_index = lambda { |ids| File.write(index_path, "active: #{ids.join(",")}\n") }
  read_index = lambda do
    match = /^active: (.*)$/.match(File.read(index_path))
    raise "missing active status index" unless match
    match[1].split(",").reject(&:empty?)
  end
  write_index.call(active)
  query_entries = active.length
  commit(root, "baseline")
  transition = lambda do |id|
    # Read the checked-out fixture state for each scenario.  A closure over a
    # mutable array would let diff-shape mutations leak into the two branches.
    write_index.call(read_index.call - [id])
  end
  shape, paths = diff_shape(root, transition)
  restore(root)
  conflicts = merge_conflicts(root, transition)
  # Removing a name from the cache leaves the canonical file untouched.
  write_index.call(read_index.call - ["TAS-00004"])
  stale = File.exist?(Dir.glob(File.join(canonical, "*", "TAS-00004.md")).fetch(0)) ? 1 : 0
  { shape: shape, paths: paths, query_reads: 1, query_entries: query_entries, conflicts: conflicts, stale: stale, stable: 1 }
end

def result_for(name)
  Dir.mktmpdir("kg-storage-") do |root|
    git_setup(root)
    send("#{name}_case", root)
  end
end

expected = File.readlines(BASELINE, chomp: true).reject { |line| line.empty? || line.start_with?("#") }.to_h { |line| line.split(":", 2) }
%w[directory stationary symlink index].each do |name|
  r = result_for(name)
  line = [r[:shape], r[:paths], r[:query_reads], r[:query_entries], r[:conflicts], r[:stale], r[:stable]].join(",")
  abort "baseline mismatch for #{name}: expected #{expected.fetch(name)}, got #{line}" if ARGV == ["--verify"] && expected.fetch(name) != line
  puts "storage{name,diff,transition_paths,query_reads,query_entries,merge_conflicts,stale_view,stable_canonical_path}: #{name},#{line}"
end
puts "verification: passed" if ARGV == ["--verify"]
