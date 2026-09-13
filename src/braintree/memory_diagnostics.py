"""Offline pipeline diagnostics for the five-arm memory causal result.

This module realizes Stage 3 of :mod:`research.agent-memory-theory-evaluation`
("Diagnose the pipeline") and the diagnostic-label section of
:mod:`research.agent-memory-evaluation-contract`. It reads a recorded
``memory-causal-v1`` result and attributes every failure to exactly one
bottleneck from :data:`braintree.memory_contract.DIAGNOSTIC_LABELS`.

The adjudication procedure scores the two halves of the pipeline separately, as
the contract requires:

* **Retrieval evidence** asks whether the memory actually delivered to the
  reader carried every source episode the gold evidence cites. It is a pure
  function of the frozen case and the arm's deterministic construction.
* **Downstream use** asks what the reader did once the evidence was delivered.
  It is only scored when retrieval succeeded, so a retrieval miss can never be
  reported as a reader failure.

Two independent reviewers label the same failures and their agreement is
reported: an *evidence-priority* reviewer decides the memory stage first, and a
*behaviour-priority* reviewer lets an explicit discard/ignore action decide
first. Where they disagree, the disagreement is recorded rather than hidden;
the evidence-priority label is the committed one because a downstream action
cannot be blamed for evidence that was never delivered.

The module makes **zero live model calls**. ``record`` and ``verify`` are
offline, like the runner and corpus they read.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import memory_causal, memory_contract, memory_corpus, memory_scenario
from .toon import table

__all__ = [
    "DIAGNOSTIC_ARTIFACT",
    "DIAGNOSTIC_LABELS",
    "DIAGNOSTIC_PROTOCOL",
    "DIAGNOSTIC_TAXONOMY",
    "DOWNSTREAM_LABELS",
    "DiagnosticError",
    "MEMORY_LABELS",
    "adjudicate",
    "diagnose",
    "failure_records",
    "main",
    "report_problems",
    "review_disagreements",
    "second_opinion",
    "verify",
]

Json = dict[str, Any]

DIAGNOSTIC_PROTOCOL = "memory-diagnostics-v1"
DIAGNOSTIC_ARTIFACT = "benchmark/memory-diagnostics-report.json"
CAUSAL_ARTIFACT = "benchmark/memory-causal-result.json"

# Each bottleneck label belongs to exactly one pipeline stage and names the
# later workstream it would justify. The labels are the contract's; the stage
# mapping is this module's adjudication vocabulary.
DIAGNOSTIC_TAXONOMY: tuple[tuple[str, str, str, str], ...] = (
    (
        "write-miss",
        "admission",
        "The required memory was never admitted: the arm holds no memory and the "
        "required source episodes are unavailable at query time.",
        "corpus admission design; no new memory mechanism",
    ),
    (
        "organization-error",
        "organization",
        "A required source episode was available to write from but the "
        "organization or consolidation step omitted it from query-time memory.",
        "TAS-125 episode and consolidation",
    ),
    (
        "retrieval-miss",
        "retrieval",
        "A required source episode was available to write from but bounded "
        "retrieval did not surface it within the memory budget.",
        "TAS-124 action-weighted retrieval",
    ),
    (
        "stale-or-conflicting-retrieval",
        "stale-or-conflicting",
        "The delivered memory carried a non-gold decision, action, or failure "
        "episode (competing guidance) alongside the gold evidence in a conflict "
        "or authority case.",
        "TAS-126 interference and TAS-127 provenance and security",
    ),
    (
        "reader-failure",
        "reading",
        "The required gold evidence was delivered but the action did not follow "
        "from it, so the loss is in reading or reasoning.",
        "skill prose and model interaction; not a memory mechanism",
    ),
    (
        "action-failure",
        "action",
        "The required evidence was delivered and the action explicitly discarded "
        "or ignored the observation, so the loss is in action selection.",
        "action selection and tooling",
    ),
)

DIAGNOSTIC_LABELS = tuple(label for label, _, _, _ in DIAGNOSTIC_TAXONOMY)
MEMORY_LABELS = ("write-miss", "organization-error", "retrieval-miss")
DOWNSTREAM_LABELS = ("stale-or-conflicting-retrieval", "reader-failure", "action-failure")
CONFLICT_GROUPS = ("revision-and-conflict", "transfer-interference-and-authority")
DISCARD_VERBS = ("discard", "ignore")
# Only a delivered non-gold decision, action, or failure is competing guidance.
# An unrelated observation is not a stale claim, so it never earns the label.
COMPETING_EPISODE_KINDS = ("decision", "action", "failure")

# The ordered adjudication procedure, as reviewed prose. Rule order is the
# adjudication: a memory-stage miss dominates because a downstream action cannot
# be blamed for evidence that was never delivered.
PROCEDURE: tuple[str, ...] = (
    "The oracle arm is injected with the distilled gold evidence, so its "
    "retrieval stage is exact by construction and every failure is downstream.",
    "The repository-only arm holds no memory, so every failure is write-miss: "
    "the admission stage never supplied the required evidence.",
    "For a memory arm, compare the required gold source episodes with the "
    "query-time memory: braintree omitting a source it could write from is "
    "organization-error; raw-history or flat-memory omitting it is retrieval-miss.",
    "When the required evidence was delivered, a chosen action whose leading "
    "verb discards or ignores the observation while the expected action does not "
    "is action-failure.",
    "Otherwise, a conflict or authority case whose delivered memory also carried "
    "a non-gold decision, action, or failure (competing guidance) is "
    "stale-or-conflicting-retrieval; an unrelated observation is not competing "
    "guidance and never earns that label.",
    "Every remaining delivered-evidence failure is reader-failure.",
)


class DiagnosticError(ValueError):
    """The causal result, the corpus, or the diagnostic report is malformed."""


def _base(root: Path | None) -> Path:
    return Path(__file__).resolve().parents[2] if root is None else Path(root)


def _required_episode_ids(case: memory_scenario.Scenario) -> frozenset[str]:
    """Return every episode the case's gold evidence cites."""
    return frozenset(
        source for evidence in case.grading.gold_evidence for source in evidence.source_episodes
    )


def _delivered_episode_ids(case: memory_scenario.Scenario, arm: str) -> frozenset[str]:
    """Return the construction episodes actually present in the arm's memory.

    The oracle injects distilled gold statements rather than raw episodes, so it
    is special-cased to the required set; every other arm's memory is text
    derived from the raw episode statements :func:`braintree.memory_causal.arm_memory`
    returns. ``flat-memory`` frames each episode as ``note N: <statement>``, so
    membership is an exact match or a trailing-statement match, never a bare
    substring that could confuse one episode with another.
    """
    if arm == "oracle":
        return _required_episode_ids(case)
    if arm == "repository-only":
        return frozenset()
    statements = tuple(memory_causal.arm_memory(case, arm))
    return frozenset(
        episode.id
        for episode in case.construction.episodes
        if any(item == episode.statement or item.endswith(episode.statement) for item in statements)
    )


def _retrieval_record(case: memory_scenario.Scenario, arm: str) -> Json:
    """Score the retrieval stage for one case and arm."""
    required = _required_episode_ids(case)
    delivered = _delivered_episode_ids(case, arm)
    missed = required - delivered
    return {
        "required": sorted(required),
        "delivered": sorted(required & delivered),
        "missed": sorted(missed),
        "score": 1.0 if not missed else 0.0,
    }


def _memory_label(case: memory_scenario.Scenario, arm: str) -> str | None:
    """Return the memory-stage bottleneck, or ``None`` when evidence was delivered."""
    if arm == "oracle":
        return None
    if arm == "repository-only":
        return "write-miss"
    if _retrieval_record(case, arm)["score"] == 1.0:
        return None
    if arm == "braintree":
        return "organization-error"
    return "retrieval-miss"


def _leads_with_discard(action: str, expected: str) -> bool:
    """Return whether an action rejects the observation while the gold action does not."""
    chosen_verb = action.split("-", 1)[0]
    expected_verb = expected.split("-", 1)[0]
    return chosen_verb in DISCARD_VERBS and expected_verb not in DISCARD_VERBS


def _downstream_label(case: memory_scenario.Scenario, arm: str, action: str) -> str:
    """Return the downstream bottleneck for a delivered-evidence failure."""
    if _leads_with_discard(action, case.grading.expected_outcome):
        return "action-failure"
    if memory_scenario.curation_group(case.family) in CONFLICT_GROUPS:
        gold = _required_episode_ids(case)
        delivered = _delivered_episode_ids(case, arm)
        if any(
            episode.id not in gold
            and episode.id in delivered
            and episode.kind in COMPETING_EPISODE_KINDS
            for episode in case.construction.episodes
        ):
            return "stale-or-conflicting-retrieval"
    return "reader-failure"


def adjudicate(
    case: memory_scenario.Scenario, arm: str, action: str
) -> tuple[str, str]:
    """Return the committed ``(label, rule)`` under the evidence-priority procedure."""
    memory_label = _memory_label(case, arm)
    if memory_label is not None:
        return memory_label, "memory-stage"
    return _downstream_label(case, arm, action), "downstream-stage"


def second_opinion(
    case: memory_scenario.Scenario, arm: str, action: str
) -> tuple[str, str]:
    """Return the independent behaviour-priority ``(label, rule)`` review.

    This reviewer lets an explicit discard/ignore action decide before the
    memory stage, so it disagrees with the committed adjudicator exactly where an
    action rejects evidence that was never delivered.
    """
    if _leads_with_discard(action, case.grading.expected_outcome):
        return "action-failure", "action-first"
    memory_label = _memory_label(case, arm)
    if memory_label is not None:
        return memory_label, "memory-stage"
    return _downstream_label(case, arm, action), "downstream-stage"


def _cases(root: Path | None) -> dict[str, memory_scenario.Scenario]:
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    return {case.case_id: case for envelope in corpus for case in envelope.cases}


def _load_result(root: Path | None) -> Json:
    path = _base(root) / CAUSAL_ARTIFACT
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DiagnosticError(f"cannot read {CAUSAL_ARTIFACT}: {error}") from error
    if not isinstance(document, Mapping):
        raise DiagnosticError(f"{CAUSAL_ARTIFACT} is not a JSON object")
    problems = memory_causal.result_problems(document)
    if problems:
        raise DiagnosticError("; ".join(problems))
    try:
        corpus = memory_corpus.load_corpus(_base(root))
    except memory_corpus.CorpusError as error:
        raise DiagnosticError(str(error)) from error
    if document.get("corpus_digest") != memory_corpus.corpus_digest(corpus):
        raise DiagnosticError("causal result corpus digest does not match the committed corpus")
    return dict(document)


def failure_records(root: Path | None = None) -> list[Json]:
    """Return one adjudicated record per causal failure, in result order."""
    result = _load_result(root)
    cases = _cases(root)
    failures = result.get("failures")
    if not isinstance(failures, list):
        raise DiagnosticError("causal result carries no failures list")
    records: list[Json] = []
    for raw in failures:
        if not isinstance(raw, Mapping):
            raise DiagnosticError("a causal failure is not a JSON object")
        case_id = str(raw.get("case_id"))
        case = cases.get(case_id)
        if case is None:
            raise DiagnosticError(f"failure names an unknown case: {case_id}")
        action = _action_for(result, str(raw.get("key")))
        label, rule = adjudicate(case, str(raw.get("arm")), action)
        other, other_rule = second_opinion(case, str(raw.get("arm")), action)
        retrieval = _retrieval_record(case, str(raw.get("arm")))
        records.append(
            {
                "key": raw.get("key"),
                "case_id": case_id,
                "family": case.family,
                "severity": case.severity,
                "arm": raw.get("arm"),
                "model": raw.get("model"),
                "repetition": raw.get("repetition"),
                "action": action,
                "expected_outcome": case.grading.expected_outcome,
                "retrieval": retrieval,
                "label": label,
                "rule": rule,
                "reviewer": {"label": other, "rule": other_rule},
                "agreement": label == other,
            }
        )
    return records


def _action_for(result: Mapping[str, Any], key: str) -> str:
    samples = result.get("samples")
    if not isinstance(samples, list):
        raise DiagnosticError("causal result carries no samples list")
    for sample in samples:
        if isinstance(sample, Mapping) and sample.get("key") == key:
            return str(sample.get("action") or "")
    raise DiagnosticError(f"failure has no matching sample: {key}")


def review_disagreements(records: Sequence[Mapping[str, Any]]) -> list[Json]:
    """Group reviewer disagreements by label pair, preserving first-seen order."""
    grouped: dict[tuple[str, str], list[str]] = {}
    for record in records:
        if record["agreement"]:
            continue
        pair = (str(record["label"]), str(record["reviewer"]["label"]))
        grouped.setdefault(pair, []).append(str(record["key"]))
    return [
        {"committed": pair[0], "reviewer": pair[1], "count": len(keys), "keys": keys}
        for pair, keys in grouped.items()
    ]


def _severity_counts(records: Sequence[Mapping[str, Any]]) -> Json:
    counts: Json = {severity: 0 for severity in memory_scenario.SEVERITIES}
    for record in records:
        counts[str(record["severity"])] += 1
    return counts


def _weighted(records: Sequence[Mapping[str, Any]]) -> float:
    return round(
        sum(float(memory_scenario.SEVERITY_WEIGHTS[str(record["severity"])])
            for record in records),
        2,
    )


def _label_table(records: Sequence[Mapping[str, Any]]) -> list[Json]:
    total = len(records)
    rows: list[Json] = []
    for label, stage, _, workstream in DIAGNOSTIC_TAXONOMY:
        selected = [record for record in records if record["label"] == label]
        rows.append(
            {
                "label": label,
                "stage": stage,
                "count": len(selected),
                "share": round(len(selected) / total, 4) if total else 0.0,
                "severity_weighted": _weighted(selected),
                "severity_counts": _severity_counts(selected),
                "arms": sorted({str(record["arm"]) for record in selected}),
                "workstream": workstream,
            }
        )
    return rows


def _retrieval_table(records: Sequence[Mapping[str, Any]]) -> Json:
    table_rows: Json = {}
    for arm in memory_causal.CAUSAL_ARMS:
        selected = [record for record in records if record["arm"] == arm]
        delivered = sum(1 for record in selected if record["retrieval"]["score"] == 1.0)
        table_rows[arm] = {
            "failures": len(selected),
            "delivered": delivered,
            "missed": len(selected) - delivered,
            "miss_rate": round((len(selected) - delivered) / len(selected), 4)
            if selected
            else 0.0,
        }
    return table_rows


def _justified(records: Sequence[Mapping[str, Any]]) -> list[Json]:
    """Return the four later workstreams with their evidence and status."""
    by_label: dict[str, list[Mapping[str, Any]]] = {
        label: [record for record in records if record["label"] == label]
        for label in DIAGNOSTIC_LABELS
    }
    poisoning_actions = [
        record
        for record in by_label["action-failure"]
        if record["family"] == "poisoning-and-authority"
    ]

    def workstream(
        name: str, selected: Sequence[Mapping[str, Any]], evidence: str
    ) -> Json:
        return {
            "workstream": name,
            "status": "justified" if selected else "not-demonstrated",
            "count": len(selected),
            "severity_weighted": _weighted(selected),
            "evidence": evidence,
        }

    return [
        workstream(
            "TAS-124-action-weighted-retrieval",
            by_label["retrieval-miss"],
            "ranked retrieval omitted a required source the history held",
        ),
        workstream(
            "TAS-125-episode-consolidation-transfer",
            by_label["organization-error"],
            "consolidation omitted a required source the history held",
        ),
        workstream(
            "TAS-126-interference-forgetting",
            by_label["stale-or-conflicting-retrieval"],
            "delivered memory carried interfering or superseded guidance",
        ),
        workstream(
            "TAS-127-uncertainty-provenance-security",
            [*by_label["stale-or-conflicting-retrieval"], *poisoning_actions],
            "delivered poisoning or authority evidence was discarded rather than adjudicated",
        ),
    ]


def _limits(result: Mapping[str, Any], root: Path | None) -> Json:
    """Return the structural limits that bound what this run can demonstrate."""
    cases = _cases(root)
    raw_cases = result.get("cases")
    listed = raw_cases if isinstance(raw_cases, list) else []
    case_ids = {str(record["case_id"]) for record in listed if isinstance(record, Mapping)}
    max_episodes = max(
        (len(cases[case_id].construction.episodes) for case_id in case_ids if case_id in cases),
        default=0,
    )
    budget = int(result.get("memory_budget") or 0)
    return {
        "split": result.get("split"),
        "evidence": result.get("evidence"),
        "memory_budget": budget,
        "max_construction_episodes": max_episodes,
        "retrieval_saturated": budget >= max_episodes,
        "note": (
            "raw-history and flat-memory surface every construction episode when the "
            "memory budget meets or exceeds the largest case, so their retrieval miss "
            "rate is zero by construction; a retrieval-miss bottleneck cannot be "
            "demonstrated from a corpus this small. write-miss is entirely the "
            "repository-only baseline (see each label's arms) and measures that the "
            "corpus is memory-required, not a defect of a memory system. The "
            "downstream labels are one-action observables: reader-failure and "
            "action-failure separate a discard/ignore action from any other wrong "
            "action, not a proven reading versus action defect. "
            "stale-or-conflicting-retrieval keys on a non-gold delivered "
            "decision/action/failure episode because the schema records no explicit "
            "supersession link, so a corpus without such an episode reports zero."
        ),
    }


def diagnose(root: Path | None = None) -> Json:
    """Return the deterministic diagnostic report for the committed causal result."""
    result = _load_result(root)
    records = failure_records(root)
    labels = _label_table(records)
    agreement = sum(1 for record in records if record["agreement"])
    report: Json = {
        "protocol": DIAGNOSTIC_PROTOCOL,
        "source": {
            "causal_protocol": result.get("protocol"),
            "causal_result": CAUSAL_ARTIFACT,
            "corpus_digest": result.get("corpus_digest"),
            "plan_digest": result.get("plan_digest"),
            "source_revision": result.get("source_revision"),
            "evidence": result.get("evidence"),
            "status": result.get("status"),
            "split": result.get("split"),
            "samples": result.get("sample_count"),
            "failures": len(records),
        },
        "taxonomy": [
            {"label": label, "stage": stage, "definition": definition, "workstream": workstream}
            for label, stage, definition, workstream in DIAGNOSTIC_TAXONOMY
        ],
        "procedure": list(PROCEDURE),
        "labels": labels,
        "stages": [
            {
                "stage": stage,
                "count": sum(row["count"] for row in labels if row["stage"] == stage),
                "severity_weighted": round(
                    sum(
                        float(row["severity_weighted"])
                        for row in labels
                        if row["stage"] == stage
                    ),
                    2,
                ),
            }
            for _, stage, _, _ in DIAGNOSTIC_TAXONOMY
        ],
        "retrieval": _retrieval_table(records),
        "downstream": {
            "delivered_failures": sum(
                1 for record in records if record["retrieval"]["score"] == 1.0
            ),
            "labels": {
                label: sum(
                    1
                    for record in records
                    if record["retrieval"]["score"] == 1.0 and record["label"] == label
                )
                for label in DOWNSTREAM_LABELS
            },
        },
        "bottlenecks": sorted(
            (row for row in labels if row["count"]),
            key=lambda row: (
                -float(row["severity_weighted"]),
                -int(row["count"]),
                str(row["label"]),
            ),
        ),
        "limits": _limits(result, root),
        "review": {
            "committed": "evidence-priority",
            "independent": "behaviour-priority",
            "scored": len(records),
            "agreement": agreement,
            "agreement_rate": round(agreement / len(records), 4) if records else 0.0,
            "disagreements": review_disagreements(records),
        },
        "justified_workstreams": _justified(records),
        "failures": records,
    }
    return report


def report_problems(report: Mapping[str, Any], root: Path | None = None) -> list[str]:
    """Return the schema and consistency problems that make a report unusable."""
    problems: list[str] = []
    for name in (
        "protocol",
        "source",
        "taxonomy",
        "procedure",
        "labels",
        "stages",
        "retrieval",
        "downstream",
        "bottlenecks",
        "limits",
        "review",
        "justified_workstreams",
        "failures",
    ):
        if name not in report:
            problems.append(f"report is missing {name}")
    if problems:
        return problems
    if report["protocol"] != DIAGNOSTIC_PROTOCOL:
        problems.append(f"report protocol is not {DIAGNOSTIC_PROTOCOL}")
    if set(DIAGNOSTIC_LABELS) != set(memory_contract.DIAGNOSTIC_LABELS):
        problems.append("diagnostic labels diverge from the evaluation contract")
    if list(report["taxonomy"]) != [
        {"label": label, "stage": stage, "definition": definition, "workstream": workstream}
        for label, stage, definition, workstream in DIAGNOSTIC_TAXONOMY
    ]:
        problems.append("report taxonomy does not match the module taxonomy")
    labels = {
        str(row["label"]): int(row["count"])
        for row in report["labels"]
        if isinstance(row, Mapping)
    }
    if set(labels) != set(DIAGNOSTIC_LABELS):
        problems.append("report labels do not cover the contract taxonomy")
    failures = report["failures"]
    if not isinstance(failures, list):
        problems.append("report failures is not a list")
        return problems
    if sum(labels.values()) != len(failures):
        problems.append("label counts do not sum to the failure count")
    agreement = sum(1 for record in failures if isinstance(record, Mapping) and record["agreement"])
    review = report["review"]
    if isinstance(review, Mapping) and int(review["agreement"]) != agreement:
        problems.append("review agreement does not match the failure records")
    return problems


def verify(root: Path | None = None) -> list[str]:
    """Return the problems that make the committed diagnostics unsatisfiable.

    Offline and model-free: it re-derives the report from the committed causal
    result and corpus and compares every field, so any drift in a case, an arm,
    or the analysis is reported.
    """
    base = _base(root)
    problems = memory_corpus.verify(base)
    if problems:
        return problems
    path = base / DIAGNOSTIC_ARTIFACT
    if not path.is_file():
        return [f"missing diagnostics artifact: {DIAGNOSTIC_ARTIFACT}"]
    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"unreadable diagnostics artifact: {error}"]
    if not isinstance(committed, Mapping):
        return ["diagnostics artifact is not a JSON object"]
    problems = report_problems(committed, base)
    if problems:
        return problems
    recomputed = diagnose(base)
    if dict(committed) != recomputed:
        mismatched = sorted(
            str(key)
            for key in set(committed) | set(recomputed)
            if committed.get(key) != recomputed.get(key)
        )
        return [f"diagnostics artifact differs from a re-derivation: {mismatched}"]
    return []


_USAGE = (
    "usage: braintree benchmark diagnostics record [--output REPORT.json]\n"
    "       braintree benchmark diagnostics verify\n"
    "Attach the pipeline bottleneck labels to the committed five-arm causal result."
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``record`` (write the report) or ``verify`` (re-derive and compare)."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0 if arguments else 2
    command = arguments[0]
    rest = arguments[1:]
    try:
        if command == "verify":
            if rest:
                raise DiagnosticError(f"unknown argument: {rest[0]}")
            problems = verify()
            for problem in problems:
                print(f"problem: {problem}")
            if problems:
                return 1
            report = diagnose()
            print(f'protocol: "{DIAGNOSTIC_PROTOCOL}"')
            print(f"failures: {len(report['failures'])}")
            print(f"agreement: {report['review']['agreement_rate']}")
            print(
                table(
                    "labels",
                    "label,count,severity_weighted",
                    (
                        (row["label"], row["count"], row["severity_weighted"])
                        for row in report["labels"]
                    ),
                )
            )
            print("verification: passed")
            return 0
        if command == "record":
            output: str | None = None
            values = list(rest)
            index = 0
            while index < len(values):
                name = values[index]
                if name == "--output" and index + 1 < len(values):
                    output = values[index + 1]
                    index += 2
                    continue
                raise DiagnosticError(f"unknown argument: {name}")
            report = diagnose()
            problems = report_problems(report)
            if problems:
                raise DiagnosticError("; ".join(problems))
            rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
            if output is None:
                print(rendered, end="")
            else:
                Path(output).write_text(rendered, encoding="utf-8")
            return 0
        print(f"error: unknown diagnostics command: {command}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2
    except DiagnosticError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
