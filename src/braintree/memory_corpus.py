"""Whole-corpus validation, deterministic splits, leakage audit, and digest.

TAS-131 through TAS-134 curated the nine scenario families as one versioned
envelope each; this module is the whole-corpus gate that replaces their
per-family guards as the authority. It validates every envelope and case
offline, proves the development/held-out split is deterministic and stratified,
audits the corpus for answer leakage, and content-addresses the frozen corpus
with a committed digest plus a verify mode. It imports no optional model
runtime and makes zero live model calls.

The operative information boundary is each case's ``query.observable_paths``.
The frozen contract's broader "repository contents at the frozen source
revision" is the outer envelope: every cited path must exist at that revision,
but the arm only observes the paths the case names. A case is a
**memory-irrelevant control** when its gold evidence cites only observable
paths; otherwise it is **memory-required**. The contract asks every family for
both; the audit records the per-family balance and the two curation groups that
are deliberately all memory-required (see
``research/agent-memory-corpus-validation.md``).

Two committed artifacts live beside the corpus:
``benchmark/memory-corpus/manifest.json`` (the per-family digests, the case
count, the frozen split assignment, the control balance, and the whole-corpus
digest) and the prose authority named above. ``braintree benchmark corpus
verify`` re-derives the manifest and fails on any drift; ``freeze`` rewrites it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import memory_contract, memory_scenario

__all__ = [
    "CORPUS_DIR_RELATIVE",
    "GROWTH_CLASSES",
    "MANIFEST_NAME",
    "MAX_PILOT_CASES",
    "MAX_TOTAL_CASES",
    "MIN_CASES_PER_FAMILY",
    "MIN_CONTROL_FAMILIES",
    "MIN_PILOT_CASES",
    "MIN_TOTAL_CASES",
    "PILOT_ARMS",
    "PILOT_PROTOCOL",
    "PILOT_VERDICTS",
    "PROTOCOL",
    "SCHEMA_VERSION",
    "CorpusError",
    "Envelope",
    "build_manifest",
    "control_balance",
    "corpus_digest",
    "family_digest",
    "freeze",
    "leakage",
    "load_corpus",
    "load_documents",
    "main",
    "manifest_problems",
    "outcome_label",
    "parse_documents",
    "path_exists",
    "pilot_problems",
    "pilot_subset",
    "source_incident",
    "split_manifest",
    "validate",
    "verify",
]

Json = dict[str, Any]

PROTOCOL = "memory-corpus-v1"
SCHEMA_VERSION = memory_scenario.SCENARIO_SCHEMA_VERSION
CORPUS_DIR_RELATIVE = "benchmark/memory-corpus"
MANIFEST_NAME = "manifest.json"

# The admitted corpus is a 40-60 case set; every family carries at least a
# diagnostic minimum, because a family with fewer cases cannot separate a
# per-family effect from noise.
MIN_CASES_PER_FAMILY = 3
MIN_TOTAL_CASES = 40
MAX_TOTAL_CASES = 60

# A gold-evidence statement is "leaked" into an observable file when a
# distinctive multi-word span of it appears there. Eight words is long enough
# that incidental overlap does not fire and short enough to catch a copied
# sentence.
GOLD_SHINGLE_WORDS = 8

# Memory-irrelevant controls must appear in more than one family; a corpus whose
# every control sits in one family cannot tell a always-consult strategy apart.
MIN_CONTROL_FAMILIES = 2

# The three interference growth classes the forgetting family must cover. The
# class is frozen here; the growth *size* is a harness knob owned by the causal
# runner, because the schema records no size field.
GROWTH_CLASSES = ("irrelevant-growth", "superseded-growth", "near-duplicate-growth")

# The separability pilot is a bounded two-arm pre-run over development cases:
# repository-only is the floor and oracle the ceiling. Its subset is derived
# deterministically from the frozen corpus before any live run, so no case can
# be chosen or dropped after an outcome is seen. Protocol and verdicts live here
# so the prose preregistration and the test that pins it share one authority.
PILOT_PROTOCOL = "memory-pilot-v1"
PILOT_ARMS = ("repository-only", "oracle")
PILOT_VERDICTS = ("proceed", "revise", "stop")
MIN_PILOT_CASES = 8
MAX_PILOT_CASES = 12

RESEARCH_THEORY = "research/agent-memory-theory-evaluation.md"
UNCERTAINTY_NODE = "TAS-127"

_NODE_ID = re.compile(r"\b[A-Z]{2,5}-\d+\b")
_WIKILINK = re.compile(r"\[\[[^\]]+\]\]")
_REVISION = re.compile(r"^[0-9A-Za-z._-]{4,64}$")
_INCIDENT_SEQUENCE = re.compile(r"-\d+$")
_NON_WORD = re.compile(r"[^a-z0-9]+")
_STATUS_DIRS = ("proposed", "active", "blocked", "resolved")


class CorpusError(ValueError):
    """The corpus directory or its manifest is unreadable or malformed."""


@dataclass(frozen=True)
class Envelope:
    """One family's versioned corpus file with its parsed cases."""

    family: str
    corpus_version: str
    schema_version: str
    source_revision: str
    cases: tuple[memory_scenario.Scenario, ...]


def _repo_root() -> Path:
    """Return the checkout root that holds the committed corpus."""
    return Path(__file__).resolve().parents[2]


def _base(root: Path | None) -> Path:
    return _repo_root() if root is None else Path(root)


def expected_corpus_version(family: str) -> str:
    """Return the one admitted ``corpus_version`` for ``family``."""
    return f"memory-{family}-corpus-v1"


def source_incident(case_id: str) -> str:
    """Return the source incident a case id belongs to.

    Variants of one source incident share a slug and differ only by a trailing
    sequence number, so ``-001`` and ``-002`` group together. A variation of one
    incident may never cross the development/held-out split.
    """
    return _INCIDENT_SEQUENCE.sub("", case_id)


def outcome_label(case: memory_scenario.Scenario) -> str:
    """Return the outcome stratum a case is balanced within.

    The admission family deliberately encodes three retained/discarded labels as
    the leading verb of its action; every other family's accepted action is
    already the finest stratum, so its outcome is its own label.
    """
    if case.family == "admission":
        for label in ("retain", "update-existing", "discard"):
            if case.grading.expected_outcome.startswith(label):
                return label
    return case.grading.expected_outcome


def load_documents(root: Path | None = None) -> dict[str, Json]:
    """Read every corpus envelope keyed by family; the manifest is skipped.

    Raises :class:`CorpusError` when the corpus directory is missing or a file
    is not readable JSON. An unexpected file is returned under its stem so
    :func:`validate` can reject it.
    """
    directory = _base(root) / CORPUS_DIR_RELATIVE
    if not directory.is_dir():
        raise CorpusError(f"missing corpus directory: {CORPUS_DIR_RELATIVE}")
    documents: dict[str, Json] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == MANIFEST_NAME:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CorpusError(f"unreadable corpus file {path.name}: {error}") from error
        if not isinstance(data, dict):
            raise CorpusError(f"corpus file {path.name} is not a JSON object")
        documents[path.stem] = data
    return documents


def parse_envelope(document: Mapping[str, Any], family: str | None = None) -> Envelope:
    """Parse one envelope document into a typed :class:`Envelope`."""
    if not isinstance(document, Mapping):
        raise CorpusError("envelope must be a mapping")
    resolved = document.get("family")
    if not isinstance(resolved, str) or not resolved:
        resolved = family
    if not isinstance(resolved, str) or not resolved:
        raise CorpusError("envelope has no family")
    version = document.get("schema_version")
    revision = document.get("source_revision")
    raw_cases = document.get("cases")
    listed = raw_cases if isinstance(raw_cases, list) else []
    cases = tuple(memory_scenario.parse_scenario(raw) for raw in listed)
    return Envelope(
        family=resolved,
        corpus_version=str(document.get("corpus_version", "")),
        schema_version=str(version),
        source_revision=str(revision),
        cases=cases,
    )


def parse_documents(documents: Mapping[str, Json]) -> tuple[Envelope, ...]:
    """Parse the whole document set, ordered by the contract's family order."""
    parsed: list[Envelope] = []
    for family in memory_contract.SCENARIO_FAMILIES:
        document = documents.get(family)
        if document is None:
            continue
        parsed.append(parse_envelope(document, family=family))
    return tuple(parsed)


def load_corpus(root: Path | None = None) -> tuple[Envelope, ...]:
    """Load and parse the committed corpus, ordered by family."""
    return parse_documents(load_documents(root))


def _cases(corpus: Sequence[Envelope]) -> list[memory_scenario.Scenario]:
    return [case for envelope in corpus for case in envelope.cases]


def gold_paths(case: memory_scenario.Scenario) -> set[str]:
    """Return the repository paths the case's minimal gold memory cites."""
    episodes = {episode.id: episode for episode in case.construction.episodes}
    paths: set[str] = set()
    for evidence in case.grading.gold_evidence:
        for source in evidence.source_episodes:
            episode = episodes.get(source)
            if episode is not None:
                paths.update(episode.evidence)
    return paths


def is_control(case: memory_scenario.Scenario) -> bool:
    """Return whether a case is memory-irrelevant under the operative boundary."""
    return gold_paths(case) <= set(case.query.observable_paths)


def control_balance(corpus: Sequence[Envelope]) -> Json:
    """Return the per-family observable-only control versus memory-required count."""
    balance: Json = {}
    for envelope in corpus:
        controls = sum(1 for case in envelope.cases if is_control(case))
        balance[envelope.family] = {
            "observable-only-controls": controls,
            "memory-required": len(envelope.cases) - controls,
        }
    return balance


def pilot_subset(corpus: Sequence[Envelope]) -> tuple[memory_scenario.Scenario, ...]:
    """Return the deterministic preregistered development subset for the pilot.

    The rule is fixed before any live run so no case can be chosen or dropped
    after its outcome is seen. For each family it takes the lexicographically
    first memory-required development case and, when the family has one, the
    lexicographically first observable-only control development case. The
    result spans every family and curation group and pairs required cases with
    controls that must stay solvable without oracle evidence.
    """
    by_family = {
        envelope.family: sorted(envelope.cases, key=lambda case: case.case_id)
        for envelope in corpus
    }
    selected: list[memory_scenario.Scenario] = []
    for family in memory_contract.SCENARIO_FAMILIES:
        development = [case for case in by_family.get(family, []) if case.split == "development"]
        required = [case for case in development if not is_control(case)]
        controls = [case for case in development if is_control(case)]
        if required:
            selected.append(required[0])
        if controls:
            selected.append(controls[0])
    return tuple(selected)


def pilot_problems(corpus: Sequence[Envelope]) -> list[str]:
    """Return the structural problems that make the pilot subset unusable.

    The subset must stay inside the admitted 8-12 range, span every family and
    every curation group, and mix memory-required cases with memory-irrelevant
    controls so an always-consult-memory strategy cannot pass the pilot.
    """
    selected = pilot_subset(corpus)
    problems: list[str] = []
    if not (MIN_PILOT_CASES <= len(selected) <= MAX_PILOT_CASES):
        problems.append(
            f"pilot: {len(selected)} cases outside {MIN_PILOT_CASES}..{MAX_PILOT_CASES}"
        )
    families = {case.family for case in selected}
    missing_families = [
        family for family in memory_contract.SCENARIO_FAMILIES if family not in families
    ]
    if missing_families:
        problems.append(f"pilot: misses families {missing_families}")
    groups = {memory_scenario.curation_group(case.family) for case in selected}
    for group, _ in memory_contract.CURATION_GROUPS:
        if group not in groups:
            problems.append(f"pilot: misses curation group {group}")
    if not any(is_control(case) for case in selected):
        problems.append("pilot: has no memory-irrelevant control")
    if not any(not is_control(case) for case in selected):
        problems.append("pilot: has no memory-required case")
    return problems


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _normalize(text: str) -> str:
    return _NON_WORD.sub(" ", text.lower()).strip()


def _shingles(statements: Iterable[str], width: int = GOLD_SHINGLE_WORDS) -> set[str]:
    spans: set[str] = set()
    for statement in statements:
        words = _normalize(statement).split()
        for start in range(max(0, len(words) - width + 1)):
            spans.add(" ".join(words[start : start + width]))
    return spans


def path_exists(base: Path, path: str) -> bool:
    """Return whether a cited path resolves in the vault or the repository.

    A ``.braintree/<status>/<name>.md`` citation is checked by node name across
    every status directory, because a node legitimately moves between them and
    its stable identity is the name, not the directory it occupied when the
    case was curated. Every other path is checked literally.
    """
    parts = path.split("/")
    if len(parts) == 3 and parts[0] == ".braintree" and parts[1] in _STATUS_DIRS:
        name = parts[2]
        return any((base / ".braintree" / status / name).is_file() for status in _STATUS_DIRS)
    return (base / path).exists()


def _path_problems(case: memory_scenario.Scenario, base: Path) -> list[str]:
    problems: list[str] = []
    paths = set(case.query.observable_paths)
    for episode in case.construction.episodes:
        paths.update(episode.evidence)
    for path in sorted(paths):
        if not path_exists(base, path):
            problems.append(f"path {case.case_id}: cited path does not exist: {path}")
    return problems


def _validate_documents(
    documents: Mapping[str, Json], root: Path | None
) -> tuple[list[str], tuple[Envelope, ...] | None]:
    base = _base(root)
    problems: list[str] = []
    expected = list(memory_contract.SCENARIO_FAMILIES)
    known = set(expected)
    for missing in sorted(known - set(documents)):
        problems.append(f"envelope: missing family file {missing}.json")
    for extra in sorted(set(documents) - known):
        problems.append(f"envelope: unknown family file {extra}.json")
    envelopes: list[Envelope] = []
    clean = True
    total = 0
    seen: dict[str, str] = {}
    for family in expected:
        document = documents.get(family)
        if document is None:
            continue
        where = f"{family}.json"
        if not isinstance(document, Mapping):
            problems.append(f"envelope {where}: not a JSON object")
            clean = False
            continue
        if document.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"envelope {where}: schema_version must be {SCHEMA_VERSION}")
            clean = False
        if document.get("family") != family:
            problems.append(f"envelope {where}: family must be {family}")
            clean = False
        wanted = expected_corpus_version(family)
        if document.get("corpus_version") != wanted:
            problems.append(f"envelope {where}: corpus_version must be {wanted}")
            clean = False
        revision = document.get("source_revision")
        if not isinstance(revision, str) or _REVISION.fullmatch(revision) is None:
            problems.append(f"envelope {where}: source_revision is not a revision")
            clean = False
        raw_cases = document.get("cases")
        if not isinstance(raw_cases, list) or not raw_cases:
            problems.append(f"envelope {where}: cases must be a non-empty list")
            clean = False
            continue
        if len(raw_cases) < MIN_CASES_PER_FAMILY:
            problems.append(
                f"count {where}: {len(raw_cases)} cases is below the {MIN_CASES_PER_FAMILY} minimum"
            )
            clean = False
        total += len(raw_cases)
        cases: list[memory_scenario.Scenario] = []
        for index, raw in enumerate(raw_cases):
            try:
                case = memory_scenario.parse_scenario(raw)
            except memory_scenario.ScenarioError as error:
                problems.append(f"case {where}[{index}]: {error}")
                clean = False
                continue
            if case.family != family:
                problems.append(
                    f"case {case.case_id}: family {case.family} differs from envelope {family}"
                )
                clean = False
            if case.source_revision != revision:
                problems.append(f"case {case.case_id}: source_revision differs from envelope")
                clean = False
            if case.case_id in seen:
                problems.append(f"case {case.case_id}: duplicate id also in {seen[case.case_id]}")
                clean = False
            else:
                seen[case.case_id] = family
            problems.extend(_path_problems(case, base))
            cases.append(case)
        if len(cases) == len(raw_cases) and isinstance(revision, str):
            envelopes.append(
                Envelope(
                    family=family,
                    corpus_version=str(document.get("corpus_version", "")),
                    schema_version=str(document.get("schema_version", "")),
                    source_revision=revision,
                    cases=tuple(cases),
                )
            )
    if total and not (MIN_TOTAL_CASES <= total <= MAX_TOTAL_CASES):
        problems.append(f"count: {total} cases outside {MIN_TOTAL_CASES}..{MAX_TOTAL_CASES}")
        clean = False
    parsed = tuple(envelopes) if clean and len(envelopes) == len(expected) else None
    return problems, parsed


def _validate_structure(corpus: tuple[Envelope, ...]) -> list[str]:
    problems: list[str] = []
    by_family = {envelope.family: list(envelope.cases) for envelope in corpus}
    for family, family_cases in sorted(by_family.items()):
        splits = {
            split: sum(1 for case in family_cases if case.split == split)
            for split in memory_contract.SPLITS
        }
        for split in memory_contract.SPLITS:
            if splits[split] == 0:
                problems.append(f"split {family}: no {split} cases")
        if splits["development"] * 3 < len(family_cases) or splits["held-out"] * 3 < len(
            family_cases
        ):
            problems.append(f"split {family}: unbalanced {splits}")
    for group, families in memory_contract.CURATION_GROUPS:
        group_cases = [case for family in families for case in by_family.get(family, [])]
        for split in memory_contract.SPLITS:
            if not any(case.split == split for case in group_cases):
                problems.append(f"split {group}: no {split} cases")
    strata: dict[tuple[str, str], list[memory_scenario.Scenario]] = {}
    for case in _cases(corpus):
        strata.setdefault((case.family, outcome_label(case)), []).append(case)
    for (family, label), members in sorted(strata.items()):
        if len(members) < 2:
            continue
        development = sum(1 for case in members if case.split == "development")
        held = len(members) - development
        if development * 3 < len(members) or held * 3 < len(members):
            problems.append(
                f"split stratum {family}/{label}: unbalanced "
                f"{development} development, {held} held-out"
            )
    incidents: dict[str, set[str]] = {}
    for case in _cases(corpus):
        incidents.setdefault(source_incident(case.case_id), set()).add(case.split)
    for incident, incident_splits in sorted(incidents.items()):
        if len(incident_splits) > 1:
            problems.append(f"split incident {incident}: crosses {sorted(incident_splits)}")
    balance = control_balance(corpus)
    control_families = sorted(
        family for family, record in balance.items() if record["observable-only-controls"] > 0
    )
    if sum(record["observable-only-controls"] for record in balance.values()) == 0:
        problems.append("control: the corpus has no memory-irrelevant control")
    if len(control_families) < MIN_CONTROL_FAMILIES:
        problems.append(f"control: only {len(control_families)} families carry controls")
    forgetting = by_family.get("forgetting-and-interference", [])
    missing = [
        growth
        for growth in GROWTH_CLASSES
        if not any(growth in case.case_id for case in forgetting)
    ]
    if missing:
        problems.append(f"growth: forgetting-and-interference misses {missing}")
    for case in by_family.get("conflict-and-uncertainty", []):
        if not any(RESEARCH_THEORY in episode.evidence for episode in case.construction.episodes):
            problems.append(f"citation {case.case_id}: does not cite {RESEARCH_THEORY}")
    return problems


def validate(documents: Mapping[str, Json], root: Path | None = None) -> list[str]:
    """Return every whole-corpus problem in ``documents``.

    Covers envelope identity, schema conformance of every case, globally unique
    case ids, source-revision agreement, repository path existence, case counts,
    split determinism and stratification, incident grouping, the control and
    growth balance, and the conflict-norm citation. Case order, gold evidence,
    graders, and family labels are enforced by the scenario schema this calls.
    """
    problems, parsed = _validate_documents(documents, root)
    if parsed is not None:
        problems.extend(_validate_structure(parsed))
    return problems


def leakage(corpus: Sequence[Envelope], root: Path | None = None) -> list[str]:
    """Return the answer leaks that expose a case outside its intended arm.

    Flags a node id, wikilink, expected outcome, or allowed action in the shared
    task prompt; a gold-evidence phrase in the task or in an observable file;
    and a gold statement that merely restates a construction episode.
    """
    base = _base(root)
    problems: list[str] = []
    for case in _cases(corpus):
        task = case.query.task
        if case.grading.expected_outcome in task:
            problems.append(f"leak {case.case_id}: the expected outcome appears in the task")
        for action in case.query.allowed_actions:
            if action in task:
                problems.append(
                    f"leak {case.case_id}: allowed action {action!r} appears in the task"
                )
        if _NODE_ID.search(task):
            problems.append(f"leak {case.case_id}: the task names a node id")
        if _WIKILINK.search(task):
            problems.append(f"leak {case.case_id}: the task carries a wikilink")
        episode_statements = {
            _normalize(episode.statement) for episode in case.construction.episodes
        }
        spans = _shingles(evidence.statement for evidence in case.grading.gold_evidence)
        task_text = _normalize(task)
        for evidence in case.grading.gold_evidence:
            gold = _normalize(evidence.statement)
            if gold in episode_statements:
                problems.append(
                    f"leak {case.case_id}: gold evidence restates a construction episode"
                )
            if gold in task_text or task_text in gold:
                problems.append(f"leak {case.case_id}: a gold statement is copied into the task")
        answer = _normalize(case.grading.expected_outcome.replace("-", " "))
        for path in case.query.observable_paths:
            text = _read_text(base / path)
            if text is None:
                continue
            normalized = _normalize(text)
            if len(answer.split()) >= 3 and answer in normalized:
                problems.append(f"leak {case.case_id}: the expected action is written in {path}")
            if any(span in normalized for span in spans):
                problems.append(f"leak {case.case_id}: a gold phrase is written in {path}")
    return problems


def split_manifest(corpus: Sequence[Envelope]) -> Json:
    """Return the frozen development and held-out case ids, sorted."""
    return {
        split: sorted(case.case_id for case in _cases(corpus) if case.split == split)
        for split in memory_contract.SPLITS
    }


def _canonical(document: Json) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _family_record(envelope: Envelope) -> Json:
    return {
        "family": envelope.family,
        "corpus_version": envelope.corpus_version,
        "schema_version": envelope.schema_version,
        "source_revision": envelope.source_revision,
        "cases": [
            memory_scenario.scenario_document(case)
            for case in sorted(envelope.cases, key=lambda case: case.case_id)
        ],
    }


def family_digest(envelope: Envelope) -> str:
    """Return the content address of one family's canonical corpus record."""
    payload = _canonical(_family_record(envelope)).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _corpus_record(corpus: Sequence[Envelope]) -> Json:
    return {
        "protocol": PROTOCOL,
        "schema_version": SCHEMA_VERSION,
        "families": [
            _family_record(envelope) for envelope in sorted(corpus, key=lambda item: item.family)
        ],
    }


def corpus_digest(corpus: Sequence[Envelope]) -> str:
    """Return the content address of the whole canonical corpus."""
    payload = _canonical(_corpus_record(corpus)).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build_manifest(corpus: Sequence[Envelope]) -> Json:
    """Return the deterministic committed manifest for ``corpus``."""
    ordered = sorted(corpus, key=lambda item: item.family)
    balance = control_balance(ordered)
    controls = sorted(
        family for family, record in balance.items() if record["observable-only-controls"] > 0
    )
    memory_only = sorted(
        family for family, record in balance.items() if record["observable-only-controls"] == 0
    )
    return {
        "protocol": PROTOCOL,
        "schema_version": SCHEMA_VERSION,
        "cases": sum(len(envelope.cases) for envelope in ordered),
        "digest": corpus_digest(ordered),
        "families": [
            {
                "family": envelope.family,
                "path": f"{envelope.family}.json",
                "corpus_version": envelope.corpus_version,
                "source_revision": envelope.source_revision,
                "cases": len(envelope.cases),
                "digest": family_digest(envelope),
            }
            for envelope in ordered
        ],
        "splits": split_manifest(ordered),
        "controls": {
            "per-family": balance,
            "control-families": controls,
            "all-memory-required-families": memory_only,
        },
        "growth": {
            "classes": list(GROWTH_CLASSES),
            "size-scaling": "harness-owned; the corpus freezes the growth class only",
        },
        "audit": {
            "boundary": (
                "operative boundary is each case's query.observable_paths; "
                "the frozen source revision is the outer envelope"
            ),
            "conflict-norms": (
                f"conflict-and-uncertainty gold cites {RESEARCH_THEORY} and the "
                f"still-proposed [[{UNCERTAINTY_NODE}-uncertainty-provenance-security]]"
            ),
            "control-exception": (
                "revision-and-conflict and transfer-interference-and-authority are "
                "deliberately all memory-required"
            ),
        },
    }


def manifest_problems(committed: Mapping[str, Any], recomputed: Mapping[str, Any]) -> list[str]:
    """Return the manifest keys whose committed value differs from a re-derivation."""
    problems: list[str] = []
    for key in (
        "protocol",
        "schema_version",
        "cases",
        "digest",
        "families",
        "splits",
        "controls",
        "growth",
        "audit",
    ):
        if committed.get(key) != recomputed.get(key):
            problems.append(f"manifest: {key} differs from the committed corpus")
    return problems


def verify(root: Path | None = None) -> list[str]:
    """Return the integrity problems that make the committed corpus unusable.

    Offline and model-free: it re-validates every envelope, re-audits leakage,
    and re-derives the committed manifest so any drift in a case, a split, or
    the digest is reported.
    """
    base = _base(root)
    try:
        documents = load_documents(base)
    except CorpusError as error:
        return [str(error)]
    problems = validate(documents, base)
    if problems:
        return problems
    corpus = parse_documents(documents)
    problems = leakage(corpus, base)
    if problems:
        return problems
    manifest_file = base / CORPUS_DIR_RELATIVE / MANIFEST_NAME
    if not manifest_file.is_file():
        return [f"manifest: missing {CORPUS_DIR_RELATIVE}/{MANIFEST_NAME}"]
    try:
        committed = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"manifest: unreadable: {error}"]
    if not isinstance(committed, Mapping):
        return ["manifest: not a JSON object"]
    return manifest_problems(committed, build_manifest(corpus))


def freeze(root: Path | None = None) -> Json:
    """Validate the corpus and rewrite its committed manifest; raise on a defect."""
    base = _base(root)
    documents = load_documents(base)
    problems = validate(documents, base)
    corpus = parse_documents(documents)
    problems.extend(leakage(corpus, base))
    if problems:
        raise CorpusError("; ".join(problems))
    manifest = build_manifest(corpus)
    path = base / CORPUS_DIR_RELATIVE / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


_USAGE = (
    "usage: braintree benchmark corpus verify\n"
    "       braintree benchmark corpus freeze\n"
    "Validate the whole gold memory corpus offline, or rewrite its committed digest manifest."
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``verify`` or ``freeze`` for the whole gold corpus."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        print(_USAGE)
        return 2
    if arguments[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0
    command = arguments[0]
    if len(arguments) != 1:
        print(f"error: unknown argument: {arguments[1]}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2
    try:
        if command == "verify":
            problems = verify()
            for problem in problems:
                print(f"problem: {problem}")
            if problems:
                return 1
            manifest = build_manifest(load_corpus())
            print(f'corpus: "{CORPUS_DIR_RELATIVE}"')
            print(f"corpus{{cases,digest}}: {manifest['cases']},{manifest['digest']}")
            print("verification: passed")
            return 0
        if command == "freeze":
            manifest = freeze()
            print(f"corpus{{cases,digest}}: {manifest['cases']},{manifest['digest']}")
            return 0
        print(f"error: unknown argument: {command}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2
    except CorpusError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
