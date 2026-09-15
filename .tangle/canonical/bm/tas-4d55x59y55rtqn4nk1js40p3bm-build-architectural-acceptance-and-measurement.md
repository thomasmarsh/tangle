---
context_rev: 1
status: proposed
updated: 2026-09-15T20:38:27Z
summary: Build the architectural acceptance scenarios and measurements.
next: Decide which named scenarios belong to slice children and which need a dedicated harness.
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md section 7 closes with a small acceptance scenario set and an inexpensive
measurement set. The scenarios are: a cold worker receives the intended action;
two initiatives remain ambiguous; a changed decision invalidates its consumer; a
cleared gate does not complete work; a partial result resumes; a parent cannot
resolve prematurely; a direct edit is visible despite unchanged mtime; a
conflicting helper write is rejected; and combined code/graph integration
revalidates assumptions. Crashes are tested where writes occur, and parser
fixtures are retained for malformed metadata and links. Measurements cover
startup and packet latency at actual and synthetic vault sizes, required
follow-up reads, output size, and suite duration.

# Outcome

The ARCH replacement has an executable acceptance scenario harness over tiny
in-memory graphs plus a bounded CLI/installer integration suite, and recorded
startup, packet, follow-up-read, output-size, and suite-duration measurements.

# Done when

- Every named scenario is an executable behavioral check, most calling pure
  functions over tiny in-memory graphs.
- The CLI/installer integration suite stays bounded and separate from research
  verification.
- Measurements are recorded at the live vault size and at a synthetic larger
  size.

# Scoping

Needs finer-grained scoping: yes. First decide which scenarios belong to slice
children as their `# Done when` evidence and which need a dedicated harness;
then split the scenario harness from the measurement harness.
