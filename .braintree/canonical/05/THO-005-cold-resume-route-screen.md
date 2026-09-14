---
status: resolved
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: Rejected the concise cold-resume route rule; recorder now admits only the verified Reading pre-stream line while retaining strict event parsing.
---

# Context

Area [[IDX-001-execution-graph]].

# Result

Added the isolated `cold-resume-frontier-v1` fixture and exact gate: select
`# Focus`'s active task and its exact `next`, excluding resolved, blocked,
proposed, and unselected active distractors. Its zero-live structural checks
pass.

Two planned live invocation attempts were consumed after the prior cumulative
count of two: the first was rejected before an answer for an output-schema
defect; the corrected second wrote telemetry but no completed turn or answer
artifact. The recorder now omits the unsupported schema dialect declaration and
requires `turn.completed`, an exact answer artifact, and final cumulative
per-turn telemetry before it can record a sample. Canned zero-live streams
cover both a complete turn and a telemetry-only incomplete turn. No candidate
rule was installed, and no token comparison is valid. Do not treat either
attempt as evidence.

# Result

The final two authorized invocations raised the project count from four to six.
Both completed and their final session answers exactly selected `TAS-101` and
`Apply the reversible schema migration.` The baseline used skill
`a50cd53da62c7969a8903cf062e3867be8357e74ba771a572a28be9a1393ee5b`
and fixture `f00c27f91051f0e8db98a3cd68410c120e89e1aacc17c13d6609565bf249d658`:
input/cached/uncached/output/reasoning/total =
83,630/38,400/45,230/535/124/84,165. The candidate added only “On a cold
resume with `# Focus`, use that index route, read only the selected node's
header before its body, and open other nodes only when that node requires their
context.” Its skill and fixture hashes were
`e9b3117e4acb6c3f0b286332ef9620c16774e299cc00689bfb9a9de942096feb` and
`8f18b8c4f510f148c026857c27811baa155f3e0393dc52013f29c1c60259bf04`;
totals were 105,931/91,904/14,027/607/102/106,538. The candidate was 22,373
tokens (26.6%) higher. Same case, seed, small scale, prompt, Terra medium,
CLI 0.154.0, read-only configuration, and exact gate were used; fixture hashes
differ only because each fixture hashes its installed skill copy.

Both `--record` commands rejected their stdout before writing artifacts because
Codex prefixed the JSON stream with `Reading`; the sessions nevertheless had
`turn.completed`, exact final answers, and final cumulative per-turn telemetry.
Treat these recovered values as a diagnostic screen, not accepted recorder
evidence. With no calls remaining and no improvement, restore and reject the
rule; do not repeat this theory. The Terra implementation-session cost is not
unambiguously recoverable from the shared orchestration session.

The exact captured failure was `unexpected character: 'Reading' at line 1
column 1`. The recorder now removes only an initial line exactly equal to
`Reading`, then parses every remaining event line strictly; canned zero-live
checks accept that prefix before a complete stream and reject malformed JSON
after it. This parser repair does not retroactively create artifacts or promote
the two exhausted invocations into benchmark evidence.
