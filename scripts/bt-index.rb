#!/usr/bin/env ruby
# Rebuildable Markdown-derived graph index.  Durable graph state stays in Markdown.
require 'digest'
require 'open3'
require 'time'

db, command, *args = ARGV
abort 'bt index helper requires database and command' unless db && command

def sql(value)
  "'#{value.to_s.gsub("'", "''")}'"
end

def run_sql(db, statements)
  output, status = Open3.capture2e('sqlite3', db, stdin_data: statements)
  abort output unless status.success?
  output
end

def frontmatter(text)
  match = text.match(/\A---\s*\n(.*?)\n---\s*\n/m)
  return [{}, text] unless match
  fields = {}
  match[1].each_line do |line|
    key, value = line.chomp.split(':', 2)
    next unless key && value
    value = value.strip
    value = value[1..-2] if value.start_with?('"') && value.end_with?('"')
    fields[key] = value
  end
  [fields, text[match.end(0)..] || '']
end

def schema
  <<~SQL
    CREATE TABLE IF NOT EXISTS nodes (
      id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, type TEXT NOT NULL,
      status TEXT NOT NULL, summary TEXT, context_rev INTEGER,
      content_hash TEXT NOT NULL, indexed_at TEXT NOT NULL, body TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS edges (
      source_id TEXT NOT NULL, relation TEXT NOT NULL, target_id TEXT NOT NULL,
      pinned_context_rev INTEGER, PRIMARY KEY(source_id, relation, target_id)
    );
    CREATE INDEX IF NOT EXISTS edges_target ON edges(target_id);
    CREATE INDEX IF NOT EXISTS edges_source ON edges(source_id);
    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(id UNINDEXED, summary, body);
    CREATE TABLE IF NOT EXISTS graph_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
  SQL
end

def reindex(db, root)
  root = File.expand_path(root)
  abort "nodes directory does not exist: #{root}" unless File.directory?(root)
  rows, edges = [], []
  Dir.glob(File.join(root, '*', '*.md')).sort.each do |path|
    status = File.basename(File.dirname(path))
    next unless %w[proposed active blocked resolved].include?(status)
    basename = File.basename(path, '.md')
    match = basename.match(/\A([A-Z][A-Z0-9_]*-\d+)-/)
    next unless match
    id = match[1]
    text = File.read(path, encoding: 'UTF-8')
    header, body = frontmatter(text)
    rows << [id, path.sub(%r{\A#{Regexp.escape(root)}/?}, ''), id.split('-', 2).first, status,
             header['summary'], Integer(header['context_rev'] || 0), Digest::SHA256.hexdigest(text), Time.now.utc.iso8601, body]
    body.scan(/^([A-Za-z][A-Za-z ]*?)\s+\[\[([^\]]+)\]\](?:\s+at context_rev\s+(\d+))?\.?\s*$/) do |relation, target, pin|
      edges << [id, relation.strip, target, pin && Integer(pin)]
    end
  end
  names = rows.to_h { |row| [File.basename(row[1], '.md'), row[0]] }
  edges.map! { |source, relation, target, pin| [source, relation, names.fetch(target, target), pin] }
  statements = schema + "\nBEGIN IMMEDIATE; DELETE FROM edges; DELETE FROM nodes_fts; DELETE FROM nodes;\n"
  rows.each do |row|
    statements << "INSERT INTO nodes VALUES(#{row.map { |v| sql(v) }.join(',')});\n"
    statements << "INSERT INTO nodes_fts VALUES(#{sql(row[0])},#{sql(row[4])},#{sql(row[8])});\n"
  end
  edges.uniq.each { |row| statements << "INSERT INTO edges VALUES(#{row.map { |v| v.nil? ? 'NULL' : sql(v) }.join(',')});\n" }
  statements << "INSERT INTO graph_meta(key,value) VALUES('nodes_root',#{sql(root)}) ON CONFLICT(key) DO UPDATE SET value=excluded.value; COMMIT;\n"
  run_sql(db, statements)
  puts "nodes: #{rows.length}\nedges: #{edges.uniq.length}\nroot: #{root}"
end

def query(db, sql_text)
  out = run_sql(db, ".mode tabs\n.headers off\n#{sql_text}\n")
  out.lines.map { |line| line.chomp.split("\t", -1) }
end

case command
when 'reindex'
  reindex(db, args.fetch(0))
when 'search'
  term, limit = args
  begin
    rows = query(db, "SELECT n.id,n.status,n.summary FROM nodes_fts f JOIN nodes n ON n.id=f.id WHERE nodes_fts MATCH #{sql(term)} ORDER BY bm25(nodes_fts) LIMIT #{Integer(limit)};")
  rescue SystemExit
    abort 'invalid full-text query; use words, quoted phrases, or AND/OR'
  end
  puts rows.empty? ? 'nodes: 0 matching nodes' : "nodes[#{rows.length}]{id,status,summary}:\n" + rows.map { |r| "  #{r.map { |v| %Q(\"#{v.gsub('"', '\\\"')}\") }.join(',')}" }.join("\n")
when 'backlinks'
  rows = query(db, "SELECT e.source_id,n.status,e.relation,e.pinned_context_rev FROM edges e LEFT JOIN nodes n ON n.id=e.source_id WHERE e.target_id=#{sql(args.fetch(0))} ORDER BY e.source_id,e.relation;")
  puts rows.empty? ? 'backlinks: 0 matching edges' : "backlinks[#{rows.length}]{source,status,relation,pinned_context_rev}:\n" + rows.map { |r| "  #{r.map { |v| %Q(\"#{v.gsub('"', '\\\"')}\") }.join(',')}" }.join("\n")
when 'stale'
  rows = query(db, "SELECT e.source_id,n.status,e.target_id,COALESCE(e.pinned_context_rev,''),COALESCE(d.context_rev,'') FROM edges e JOIN nodes n ON n.id=e.source_id LEFT JOIN nodes d ON d.id=e.target_id WHERE e.relation='Depends on' AND (e.pinned_context_rev IS NULL OR d.id IS NULL OR d.context_rev != e.pinned_context_rev) ORDER BY e.source_id,e.target_id;")
  puts rows.empty? ? 'stale: 0 dependency pins' : "stale[#{rows.length}]{source,status,target,pinned,current}:\n" + rows.map { |r| "  #{r.map { |v| %Q(\"#{v.gsub('"', '\\\"')}\") }.join(',')}" }.join("\n")
else
  abort "unknown index command: #{command}"
end
