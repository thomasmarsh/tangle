---
context_rev: 1
status: resolved
updated: 2026-09-15T18:51:46Z
summary: Surface packet completion criteria and the record operation.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

ASTRA.md section 2 asks the packet to provide "the task, its next action, and
completion criteria" and "the expected verification and the operation for recording
progress." The packet resumption work (tas-32btrf71jvz66am5pempkhqapy) surfaced the
manifest files and verification but not the node # Done when text or the record
operation, so those two ASTRA section 2 bullets remain open.

There is no command that updates an existing node; progress is recorded by editing
the authoritative status field in place and landing the # Result change in the same
commit (SKILL.md mutation rules), with tangle check before handoff.

Gates this artifact enters: tests/test_packet.py and tests/test_manifest.py for
packet behavior, tests/test_skill.py for the client-responsibility boundary, and
default ruff, mypy, and pytest discovery.

# Outcome

tangle packet reports the ready node completion criteria and the operation that
records progress, so its output is sufficient both to start and to close the work.

# Done when

- tangle packet ready output includes the ready node # Done when completion criteria,
  reported as zero when the node has none, without introducing a new planning format.
- tangle packet names the operation that records progress for the ready node.
- tests/test_packet.py covers a node with completion criteria, a node without, and the
  record-operation line.
- tangle check and make test pass.

# Result

tangle packet now reports the ready node # Done when completion criteria and the operation for recording progress, closing the last two ASTRA section 2 execution-packet bullets.
graph_check.parse_done_when reads the section (one bullet is one criterion, a wrapped continuation joins it, a prose section keeps one criterion per paragraph); packet prints a bounded criteria table (limit 20 with an explicit omitted-overage line, zero when the node has none) and a stable record line naming the in-place status edit plus # Result with tangle check before handoff. No new planning format was added.
Evidence: tests/test_packet.py covers criteria-present, zero-criteria, and the bounded overage; make test green (803 passed, 3 skipped); tangle check passed (271 nodes); no frozen observable changed.
