"""Isolated, repeated separability pilot harness (protocol ``memory-pilot-v2``).

TAS-147's single-repetition re-run could not decide the phase-one gate: it used
the built-in Pi ``delegate`` child, whose inherited project context exposed
``AGENTS.md`` outside the arm fixture, pinned the wrong model, and recorded no
per-repetition provenance. This module is the replacement harness. It is
dependency-free, makes zero live model calls, and is covered by zero-live tests.

The harness separates two concerns the pilot must never conflate:

* **The plan** is a pure function of the frozen corpus and the protocol. It
  derives the 12 preregistered development cases, builds each arm fixture by
  embedding the observable files and the arm's memory directly in the prompt,
  renders one prompt per ``(case, arm, repetition)`` episode, and chunks the 72
  episodes into three deterministic 24-child batches.
* **The recording** ingests raw child outputs and telemetry, validates every
  contract pin and provenance field, grades each action with
  :func:`tangle.memory_scenario.grade`, and applies the preregistered paired
  majority. A missing or infrastructure-failed sample makes the run
  *incomplete*; a malformed model answer is a *model failure*, never
  infrastructure.

The child is the project agent profile ``.pi/agents/memory-pilot-child.md``:
replacement system prompt, fresh context, no tools, no skills, no project or
global context, no ambient extensions, and the explicit
``deepseek/deepseek-v4-flash`` model at ``high`` effort with no fallback.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import memory_contract, memory_corpus, memory_scenario, store
from .toon import field, table

__all__ = [
    "PILOT_V2_ARMS",
    "PILOT_V2_BATCHES",
    "PILOT_V2_BATCH_SIZE",
    "PILOT_V2_CHILD_PROFILE",
    "PILOT_V2_CONTROL_THRESHOLD",
    "PILOT_V2_GRADER",
    "PILOT_V2_HARNESS",
    "PILOT_V2_MODEL",
    "PILOT_V2_PROTOCOL",
    "PILOT_V2_REASONING_EFFORT",
    "PILOT_V2_REPETITIONS",
    "PILOT_V2_SEPARATION_THRESHOLD",
    "PILOT_V2_VERDICTS",
    "REQUIRED_TELEMETRY",
    "SYSTEM_PROMPT",
    "ObservableFile",
    "PilotError",
    "PilotFixture",
    "PilotOutputError",
    "build_fixture",
    "build_plan",
    "case_verdict",
    "dry_run",
    "dry_run_problems",
    "fixture_digest",
    "main",
    "parse_action",
    "pin_document",
    "plan_document",
    "plan_problems",
    "record",
    "render_prompt",
    "result_problems",
    "source_revision",
    "verify",
]

Json = dict[str, Any]

PILOT_V2_PROTOCOL = "memory-pilot-v2"
PILOT_V2_ARMS = ("repository-only", "oracle")
PILOT_V2_REPETITIONS = 3
PILOT_V2_SEPARATION_THRESHOLD = 2
PILOT_V2_CONTROL_THRESHOLD = 2
PILOT_V2_BATCH_SIZE = 24
PILOT_V2_BATCHES = 3
PILOT_V2_CHILD_PROFILE = "memory-pilot-child"
PILOT_V2_MODEL = "deepseek/deepseek-v4-flash"
PILOT_V2_MODEL_REVISION = "deepseek-v4-flash"
PILOT_V2_REASONING_EFFORT = "high"
PILOT_V2_HARNESS = "pi-subagents"
PILOT_V2_GRADER = "memory_scenario.grade"
PILOT_V2_VERDICTS = ("proceed", "revise", "stop")
PILOT_V2_FIXTURE_VERSION = "memory-pilot-v2-fixture-1"
PILOT_V2_PROMPT_REVISION = "memory-pilot-v2-prompt-1"
PILOT_V2_TOOL_REVISION = "no-tools"
PILOT_V2_GRADER_VERSION = "memory-scenario-v1"
PILOT_V2_BUDGET = "one isolated child turn per episode; no tools; no retries"
PILOT_V2_ALLOWED_COMMANDS: tuple[str, ...] = ()

SYSTEM_PROMPT = (
    "You are an isolated memory-evaluation solver. Each task gives you one "
    "engineering episode: the task, the repository files you may observe, an "
    "optional memory, and the allowed actions.\n"
    "\n"
    "Rules:\n"
    "- Use only the information in the task. Do not use outside knowledge, the "
    "repository, the network, or any tool.\n"
    "- The task embeds every observable file and every memory item; nothing else "
    "is available.\n"
    "- Choose exactly one action from the allowed list.\n"
    '- Reply with exactly one JSON object and no other text, in this form: '
    '{"action": "<one allowed action>"}\n'
    "- Do not explain, justify, or add any other field."
)

# A sample's telemetry must name every contract token and interaction metric
# except ``latency_ms``, which the recorder computes from the retained
# timestamps instead of trusting a self-reported duration.
_INPUT_METRICS = tuple(
    metric for metric in memory_contract.INTERACTION_METRICS if metric != "latency_ms"
)
REQUIRED_TELEMETRY = (*memory_contract.TOKEN_METRICS, *_INPUT_METRICS)

_STATUS_DIRS = ("proposed", "active", "blocked", "resolved")
_PROFILE_RELATIVE = ".pi/agents/memory-pilot-child.md"


class PilotError(ValueError):
    """The pilot plan, a fixture, or a recorded sample is malformed."""


class PilotOutputError(PilotError):
    """A child's raw output does not contain one allowed action."""


@dataclass(frozen=True)
class ObservableFile:
    """One repository file an arm may observe, resolved and embedded."""

    path: str
    resolved_path: str
    content: str


@dataclass(frozen=True)
class PilotFixture:
    """One case as one arm sees it, independent of the repetition."""

    case_id: str
    family: str
    arm: str
    control: bool
    task: str
    observable: tuple[ObservableFile, ...]
    memory: tuple[str, ...]
    allowed_actions: tuple[str, ...]


def _repo_root() -> Path:
    """Return the checkout root that holds the corpus and the child profile."""
    return Path(__file__).resolve().parents[2]


def _base(root: Path | None) -> Path:
    return _repo_root() if root is None else Path(root)


def source_revision(root: Path | None = None) -> str:
    """Return the harness source revision, or ``unknown`` outside a Git checkout."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=_base(root),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    revision = completed.stdout.strip()
    return revision or "unknown"


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_canonical(document: Any) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_text(payload)


def _resolve_observable(root: Path, path: str) -> ObservableFile:
    parts = path.split("/")
    if len(parts) == 3 and parts[0] == ".tangle" and parts[1] in _STATUS_DIRS:
        found = store.find_by_name(str(root / ".tangle"), parts[2])
        if found is None:
            raise PilotError(f"observable path missing from the vault: {path}")
        status, candidate = found
        resolved = f".tangle/{status}/{parts[2]}"
        return ObservableFile(path, resolved, Path(candidate).read_text(encoding="utf-8"))
    checkout = root / path
    if not checkout.is_file():
        raise PilotError(f"observable path missing from the checkout: {path}")
    return ObservableFile(path, path, checkout.read_text(encoding="utf-8"))


def build_fixture(
    case: memory_scenario.Scenario,
    arm: str,
    root: Path | None = None,
    cache: dict[str, ObservableFile] | None = None,
) -> PilotFixture:
    """Build one arm's fixture, embedding every observable file and its memory.

    ``repository-only`` carries no memory; ``oracle`` carries the case's minimal
    gold evidence. Both see identical task, observable files, and allowed
    actions, so only the available history differs.
    """
    if arm == "repository-only":
        memory: tuple[str, ...] = ()
    elif arm == "oracle":
        memory = tuple(evidence.statement for evidence in case.grading.gold_evidence)
    else:
        raise PilotError(f"unsupported pilot arm: {arm}")
    base = _base(root)
    files: list[ObservableFile] = []
    for path in case.query.observable_paths:
        if cache is not None and path in cache:
            files.append(cache[path])
            continue
        resolved = _resolve_observable(base, path)
        if cache is not None:
            cache[path] = resolved
        files.append(resolved)
    return PilotFixture(
        case_id=case.case_id,
        family=case.family,
        arm=arm,
        control=memory_corpus.is_control(case),
        task=case.query.task,
        observable=tuple(files),
        memory=memory,
        allowed_actions=case.query.allowed_actions,
    )


def render_prompt(fixture: PilotFixture) -> str:
    """Render the exact user prompt for one fixture; the system prompt is separate."""
    lines: list[str] = ["# Task", fixture.task, "", "# Observable files"]
    if fixture.observable:
        for item in fixture.observable:
            lines.extend([f"## {item.path}", "```", item.content.rstrip("\n"), "```"])
    else:
        lines.append("None.")
    lines.extend(["", "# Available memory"])
    if fixture.memory:
        lines.extend(f"- {statement}" for statement in fixture.memory)
    else:
        lines.append("None.")
    lines.extend(["", "# Allowed actions"])
    lines.extend(f"- {action}" for action in fixture.allowed_actions)
    lines.extend(
        [
            "",
            "# Required response",
            (
                "Reply with exactly one JSON object and nothing else: "
                '{"action": "<one allowed action>"}'
            ),
            "",
        ]
    )
    return "\n".join(lines)


def prompt_digest(prompt: str) -> str:
    """Return a content address over the system prompt and the rendered task."""
    return _sha256_text(SYSTEM_PROMPT + "\n\n" + prompt)


def fixture_digest(fixture: PilotFixture) -> str:
    """Return a content address over the structured fixture, including file bytes."""
    return _sha256_canonical(
        {
            "case_id": fixture.case_id,
            "family": fixture.family,
            "arm": fixture.arm,
            "control": fixture.control,
            "task": fixture.task,
            "allowed_actions": list(fixture.allowed_actions),
            "observable": [
                {
                    "path": item.path,
                    "resolved_path": item.resolved_path,
                    "digest": _sha256_text(item.content),
                }
                for item in fixture.observable
            ],
            "memory": list(fixture.memory),
        }
    )


def pin_document(corpus_digest: str, source_revision: str) -> Json:
    """Return every contract pin field as a value the run must preserve."""
    return {
        "protocol": PILOT_V2_PROTOCOL,
        "corpus-digest": corpus_digest,
        "fixture-version": PILOT_V2_FIXTURE_VERSION,
        "source-revision": source_revision,
        "model": PILOT_V2_MODEL,
        "model-revision": PILOT_V2_MODEL_REVISION,
        "reasoning-effort": PILOT_V2_REASONING_EFFORT,
        "prompt-revision": PILOT_V2_PROMPT_REVISION,
        "tool-revision": PILOT_V2_TOOL_REVISION,
        "budget": PILOT_V2_BUDGET,
        "allowed-commands": list(PILOT_V2_ALLOWED_COMMANDS),
        "grader-version": PILOT_V2_GRADER_VERSION,
    }


def _episode_key(case_id: str, arm: str, repetition: int) -> str:
    return f"{case_id}--{arm}--r{repetition}"


def _fixture_hashes(
    case: memory_scenario.Scenario,
    arm: str,
    root: Path,
    cache: dict[str, ObservableFile],
) -> tuple[str, str]:
    fixture = build_fixture(case, arm, root, cache)
    return prompt_digest(render_prompt(fixture)), fixture_digest(fixture)


def build_plan(root: Path | None = None) -> tuple[Json, ...]:
    """Return the 72 uniquely keyed episodes, batch-ordered, as plain records."""
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    subset = memory_corpus.pilot_subset(corpus)
    cache: dict[str, ObservableFile] = {}
    episodes: list[Json] = []
    for case in subset:
        for arm in PILOT_V2_ARMS:
            prompt_hash, fixture_hash = _fixture_hashes(case, arm, base, cache)
            for repetition in range(1, PILOT_V2_REPETITIONS + 1):
                episodes.append(
                    {
                        "key": _episode_key(case.case_id, arm, repetition),
                        "batch": len(episodes) // PILOT_V2_BATCH_SIZE + 1,
                        "case_id": case.case_id,
                        "arm": arm,
                        "repetition": repetition,
                        "control": memory_corpus.is_control(case),
                        "prompt_digest": prompt_hash,
                        "fixture_digest": fixture_hash,
                        "launch": {
                            "agent": PILOT_V2_CHILD_PROFILE,
                            "model": PILOT_V2_MODEL,
                            "thinking": PILOT_V2_REASONING_EFFORT,
                            "context": "fresh",
                        },
                    }
                )
    return tuple(episodes)


def plan_document(root: Path | None = None) -> Json:
    """Return the deterministic run plan, including pins and a plan digest."""
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    digest = memory_corpus.corpus_digest(corpus)
    episodes = build_plan(base)
    document: Json = {
        "protocol": PILOT_V2_PROTOCOL,
        "harness": PILOT_V2_HARNESS,
        "grader": PILOT_V2_GRADER,
        "child_profile": PILOT_V2_CHILD_PROFILE,
        "model": PILOT_V2_MODEL,
        "reasoning_effort": PILOT_V2_REASONING_EFFORT,
        "corpus_digest": digest,
        "pins": pin_document(digest, source_revision(base)),
        "case_count": len({str(episode["case_id"]) for episode in episodes}),
        "arm_count": len(PILOT_V2_ARMS),
        "repetitions": PILOT_V2_REPETITIONS,
        "sample_count": len(episodes),
        "batch_size": PILOT_V2_BATCH_SIZE,
        "batch_count": PILOT_V2_BATCHES,
        "episodes": list(episodes),
    }
    document["plan_digest"] = plan_digest(document)
    return document


def plan_digest(document: Mapping[str, Any]) -> str:
    """Return the content address of a plan's pins and episode identities."""
    raw_episodes = document.get("episodes")
    episodes = raw_episodes if isinstance(raw_episodes, list) else []
    keys = ("key", "batch", "case_id", "arm", "repetition", "prompt_digest", "fixture_digest")
    return _sha256_canonical(
        {
            "protocol": document.get("protocol"),
            "pins": document.get("pins"),
            "episodes": [
                {key: episode.get(key) for key in keys}
                for episode in episodes
                if isinstance(episode, Mapping)
            ],
        }
    )


def plan_problems(root: Path | None = None) -> list[str]:
    """Return the structural problems that make the generated plan unusable."""
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    problems = memory_corpus.pilot_problems(corpus)
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    subset = memory_corpus.pilot_subset(corpus)
    episodes = build_plan(base)
    expected_keys = {
        _episode_key(case.case_id, arm, repetition)
        for case in subset
        for arm in PILOT_V2_ARMS
        for repetition in range(1, PILOT_V2_REPETITIONS + 1)
    }
    keys = [str(episode["key"]) for episode in episodes]
    if len(keys) != len(set(keys)):
        problems.append("plan: episode keys are not unique")
    if set(keys) != expected_keys:
        missing = sorted(expected_keys - set(keys))
        extra = sorted(set(keys) - expected_keys)
        if missing:
            problems.append(f"plan: missing episodes {missing}")
        if extra:
            problems.append(f"plan: unexpected episodes {extra}")
    batches: dict[int, int] = {}
    for episode in episodes:
        batch = episode["batch"]
        if not isinstance(batch, int) or not 1 <= batch <= PILOT_V2_BATCHES:
            problems.append(f"plan: episode {episode.get('key')} has batch {batch!r}")
            continue
        batches[batch] = batches.get(batch, 0) + 1
        for name in ("key", "case_id", "arm", "repetition", "prompt_digest", "fixture_digest"):
            if episode.get(name) in (None, ""):
                problems.append(f"plan: episode {episode.get('key')} misses {name}")
    for batch in range(1, PILOT_V2_BATCHES + 1):
        if batches.get(batch) != PILOT_V2_BATCH_SIZE:
            problems.append(f"plan: batch {batch} has {batches.get(batch, 0)} episodes")
    cache: dict[str, ObservableFile] = {}
    for episode in episodes:
        case_id = str(episode["case_id"])
        arm = str(episode["arm"])
        if case_id not in cases:
            problems.append(f"plan: unknown case {case_id}")
            continue
        prompt_hash, hash_value = _fixture_hashes(cases[case_id], arm, base, cache)
        if episode.get("prompt_digest") != prompt_hash:
            problems.append(f"plan: prompt digest drifted for {episode.get('key')}")
        if episode.get("fixture_digest") != hash_value:
            problems.append(f"plan: fixture digest drifted for {episode.get('key')}")
    document = plan_document(base)
    if document["plan_digest"] != plan_digest(document):
        problems.append("plan: plan digest is not a content address of the plan")
    if set(document["pins"]) != set(memory_contract.PIN_FIELDS):
        problems.append("plan: pins do not cover every contract pin field")
    return problems


def parse_action(raw: str, allowed: Sequence[str]) -> str:
    """Return the one allowed action a child's raw output carries.

    The output must contain a JSON object with an ``action`` member naming one of
    the allowed actions. Additional members are tolerated; a missing, malformed,
    or out-of-list action raises :class:`PilotOutputError`.
    """
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end < start:
        raise PilotOutputError("no JSON object in the child output")
    try:
        payload = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as error:
        raise PilotOutputError(f"child output is not valid JSON: {error}") from error
    if not isinstance(payload, Mapping):
        raise PilotOutputError("child output JSON is not an object")
    action = payload.get("action")
    if not isinstance(action, str):
        raise PilotOutputError("child output does not carry a string action")
    if action not in allowed:
        raise PilotOutputError(f"child action is not allowed: {action!r}")
    return action


def _latency_ms(started_at: Any, finished_at: Any) -> int:
    if not isinstance(started_at, str) or not isinstance(finished_at, str):
        raise PilotError("started_at and finished_at are required timestamps")
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(finished_at)
    except ValueError as error:
        raise PilotError(f"invalid timestamp: {error}") from error
    if start.tzinfo is None or end.tzinfo is None:
        raise PilotError("timestamps must carry a UTC offset")
    delta_ms = (end - start).total_seconds() * 1000.0
    if delta_ms < 0:
        raise PilotError("finished_at precedes started_at")
    return round(delta_ms)


def _telemetry(raw: Any) -> tuple[Json, list[str]]:
    if not isinstance(raw, Mapping):
        return {}, ["missing telemetry"]
    problems: list[str] = []
    document: Json = {}
    for metric in REQUIRED_TELEMETRY:
        value = raw.get(metric)
        if metric == "monetary_cost":
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                problems.append(f"telemetry.{metric} must be a non-negative number")
                continue
            document[metric] = float(value)
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            problems.append(f"telemetry.{metric} must be a non-negative integer")
            continue
        document[metric] = value
    return document, problems


def _empty_sample(
    episode: Mapping[str, Any], case: memory_scenario.Scenario, raw: Mapping[str, Any]
) -> Json:
    return {
        "key": episode["key"],
        "case_id": episode["case_id"],
        "arm": episode["arm"],
        "repetition": episode["repetition"],
        "control": episode["control"],
        "child_run_id": raw.get("child_run_id"),
        "raw_output_ref": raw.get("raw_output_ref"),
        "raw_output": raw.get("raw_output", ""),
        "prompt_digest": raw.get("prompt_digest"),
        "started_at": raw.get("started_at"),
        "finished_at": raw.get("finished_at"),
        "expected_outcome": case.grading.expected_outcome,
        "acceptable_actions": list(case.grading.acceptable_actions),
        "action": None,
        "correct": False,
        "credit": 0.0,
        "regret": 0.0,
        "parse_error": None,
        "incomplete": False,
        "infrastructure_error": None,
        "telemetry": {},
    }


def _one_sample(
    episode: Mapping[str, Any],
    raw: Mapping[str, Any],
    case: memory_scenario.Scenario,
) -> Json:
    record = _empty_sample(episode, case, raw)
    infrastructure = raw.get("infrastructure_error")
    if infrastructure:
        record["incomplete"] = True
        record["infrastructure_error"] = str(infrastructure)
        return record
    problems: list[str] = []
    if not record["child_run_id"]:
        problems.append("missing child_run_id")
    if not record["raw_output_ref"]:
        problems.append("missing raw_output_ref")
    if raw.get("model") != PILOT_V2_MODEL:
        problems.append(f"model is not pinned to {PILOT_V2_MODEL}")
    if record["prompt_digest"] != episode["prompt_digest"]:
        problems.append("prompt digest does not match the plan")
    try:
        latency_ms = _latency_ms(record["started_at"], record["finished_at"])
    except PilotError as error:
        problems.append(str(error))
        latency_ms = 0
    telemetry, telemetry_problems = _telemetry(raw.get("telemetry"))
    problems.extend(telemetry_problems)
    if problems:
        record["incomplete"] = True
        record["infrastructure_error"] = "; ".join(problems)
        return record
    record["telemetry"] = {**telemetry, "latency_ms": latency_ms}
    try:
        action = parse_action(str(record["raw_output"]), case.query.allowed_actions)
    except PilotOutputError as error:
        record["parse_error"] = str(error)
        action = ""
    record["action"] = action
    grade = memory_scenario.grade(case, action)
    record["correct"] = grade.correct
    record["credit"] = grade.credit
    record["regret"] = grade.regret
    return record


def _case_records(
    plan: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    cases: Mapping[str, memory_scenario.Scenario],
) -> list[Json]:
    order: list[str] = []
    raw_episodes = plan.get("episodes")
    for episode in raw_episodes if isinstance(raw_episodes, list) else []:
        if not isinstance(episode, Mapping):
            continue
        case_id = str(episode["case_id"])
        if case_id not in order:
            order.append(case_id)
    records: list[Json] = []
    for case_id in order:
        case = cases[case_id]
        members = [sample for sample in samples if sample["case_id"] == case_id]
        repository = {
            int(sample["repetition"]): sample
            for sample in members
            if sample["arm"] == "repository-only"
        }
        oracle = {
            int(sample["repetition"]): sample
            for sample in members
            if sample["arm"] == "oracle"
        }
        repository_correct = [
            repository[repetition]["correct"] if repetition in repository else None
            for repetition in range(1, PILOT_V2_REPETITIONS + 1)
        ]
        oracle_correct = [
            oracle[repetition]["correct"] if repetition in oracle else None
            for repetition in range(1, PILOT_V2_REPETITIONS + 1)
        ]
        control = memory_corpus.is_control(case)
        if control:
            valid = sum(1 for value in repository_correct if value is True)
            classification = "valid" if valid >= PILOT_V2_CONTROL_THRESHOLD else "invalid"
            separations = 0
        else:
            separations = sum(
                1
                for repository_value, oracle_value in zip(
                    repository_correct, oracle_correct, strict=True
                )
                if repository_value is False and oracle_value is True
            )
            classification = (
                "separates" if separations >= PILOT_V2_SEPARATION_THRESHOLD else "fails"
            )
        records.append(
            {
                "case_id": case_id,
                "family": case.family,
                "control": control,
                "classification": classification,
                "repository_only_correct": repository_correct,
                "oracle_correct": oracle_correct,
                "paired_separations": separations,
                "repetitions": PILOT_V2_REPETITIONS,
            }
        )
    return records


def case_verdict(case_records: Sequence[Mapping[str, Any]]) -> str:
    """Return the preregistered phase-one verdict for the case-level results.

    ``proceed`` when every case meets its criterion; ``revise`` when one or two
    cases fail but the retained subset keeps the 8-case floor and every curation
    group; ``stop`` when three or more memory-required cases fail to separate, or
    no repair can retain the floor and coverage.
    """
    failing = [
        record for record in case_records if record["classification"] in {"fails", "invalid"}
    ]
    required_failures = [record for record in failing if not record["control"]]
    if len(required_failures) >= 3:
        return "stop"
    retained = [record for record in case_records if record not in failing]
    retained_groups = {memory_scenario.curation_group(str(record["family"])) for record in retained}
    needed_groups = {group for group, _ in memory_contract.CURATION_GROUPS}
    if len(retained) < memory_corpus.MIN_PILOT_CASES or retained_groups != needed_groups:
        return "stop"
    if failing:
        return "revise"
    return "proceed"


def record(
    plan: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    root: Path | None = None,
) -> Json:
    """Ingest raw samples and return the preregistered result document."""
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    raw_episodes = plan.get("episodes")
    if not isinstance(raw_episodes, list) or not raw_episodes:
        raise PilotError("plan has no episodes")
    episodes = [episode for episode in raw_episodes if isinstance(episode, Mapping)]
    by_key = {str(episode["key"]): episode for episode in episodes}
    provided: dict[str, Mapping[str, Any]] = {}
    for raw in samples:
        if not isinstance(raw, Mapping):
            raise PilotError("a sample is not a JSON object")
        key = raw.get("key")
        if not isinstance(key, str) or key not in by_key:
            raise PilotError(f"sample key is not in the plan: {key!r}")
        if key in provided:
            raise PilotError(f"duplicate sample key: {key}")
        provided[key] = raw
    missing = [key for key in by_key if key not in provided]
    records: list[Json] = []
    incomplete: list[str] = [f"missing sample {key}" for key in missing]
    for episode in episodes:
        sample_raw = provided.get(str(episode["key"]))
        if sample_raw is None:
            continue
        sample = _one_sample(episode, sample_raw, cases[str(episode["case_id"])])
        if sample["incomplete"]:
            incomplete.append(f"{sample['key']}: {sample['infrastructure_error']}")
        records.append(sample)
    status = "incomplete" if incomplete else "complete"
    case_records = _case_records(plan, records, cases)
    pins = plan.get("pins")
    source_revision_value = pins.get("source-revision") if isinstance(pins, Mapping) else None
    return {
        "protocol": PILOT_V2_PROTOCOL,
        "status": status,
        "verdict": case_verdict(case_records) if status == "complete" else None,
        "harness": PILOT_V2_HARNESS,
        "grader": PILOT_V2_GRADER,
        "child_profile": PILOT_V2_CHILD_PROFILE,
        "model": PILOT_V2_MODEL,
        "reasoning_effort": PILOT_V2_REASONING_EFFORT,
        "corpus_digest": plan.get("corpus_digest"),
        "source_revision": source_revision_value,
        "pins": pins,
        "plan_digest": plan.get("plan_digest"),
        "case_count": plan.get("case_count"),
        "sample_count": len(records),
        "expected_sample_count": len(episodes),
        "repetitions": PILOT_V2_REPETITIONS,
        "batches": list(range(1, PILOT_V2_BATCHES + 1)),
        "cases": case_records,
        "samples": records,
        "missing_keys": missing,
        "incomplete_reasons": incomplete,
    }


def result_problems(result: Mapping[str, Any]) -> list[str]:
    """Return the schema problems that make a recorded result unusable."""
    problems: list[str] = []
    for name in (
        "protocol",
        "status",
        "verdict",
        "harness",
        "grader",
        "model",
        "corpus_digest",
        "pins",
        "case_count",
        "sample_count",
        "expected_sample_count",
        "cases",
        "samples",
        "missing_keys",
    ):
        if name not in result:
            problems.append(f"result: missing {name}")
    if problems:
        return problems
    if result["protocol"] != PILOT_V2_PROTOCOL:
        problems.append("result: wrong protocol")
    status = result["status"]
    if status not in {"complete", "incomplete"}:
        problems.append(f"result: unknown status {status!r}")
    if status == "complete":
        if result["verdict"] not in PILOT_V2_VERDICTS:
            problems.append("result: complete run has no valid verdict")
        if result["missing_keys"]:
            problems.append("result: complete run has missing keys")
        if result["sample_count"] != result["expected_sample_count"]:
            problems.append("result: complete run does not cover every episode")
    elif result["verdict"] is not None:
        problems.append("result: incomplete run must not carry a verdict")
    pins = result["pins"]
    if not isinstance(pins, Mapping) or set(pins) != set(memory_contract.PIN_FIELDS):
        problems.append("result: pins do not cover every contract pin field")
    samples = result["samples"]
    if not isinstance(samples, list):
        return [*problems, "result: samples must be a list"]
    for sample in samples:
        if not isinstance(sample, Mapping):
            problems.append("result: a sample is not an object")
            continue
        for name in ("key", "case_id", "arm", "repetition"):
            if sample.get(name) in (None, ""):
                problems.append(f"result: sample {sample.get('key')} misses {name}")
        if sample.get("incomplete"):
            continue
        for name in (
            "child_run_id",
            "raw_output_ref",
            "prompt_digest",
            "correct",
        ):
            if sample.get(name) in (None, ""):
                problems.append(f"result: sample {sample.get('key')} misses {name}")
        telemetry = sample.get("telemetry")
        if not isinstance(telemetry, Mapping):
            problems.append(f"result: sample {sample.get('key')} misses telemetry")
            continue
        for name in (*REQUIRED_TELEMETRY, "latency_ms"):
            if name not in telemetry:
                problems.append(f"result: sample {sample.get('key')} misses telemetry.{name}")
    cases = result["cases"]
    if isinstance(cases, list):
        for case in cases:
            if case.get("classification") not in {"separates", "fails", "valid", "invalid"}:
                problems.append(f"result: case {case.get('case_id')} has no classification")
        if status == "complete" and result["verdict"] in PILOT_V2_VERDICTS:
            if case_verdict(cases) != result["verdict"]:
                problems.append("result: verdict does not match the case classifications")
    return problems


def _synthetic_samples(plan: Mapping[str, Any], root: Path) -> list[Json]:
    """Return a zero-live synthetic sample set that must aggregate to ``proceed``."""
    corpus = memory_corpus.load_corpus(root)
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    samples: list[Json] = []
    raw_episodes = plan.get("episodes")
    if not isinstance(raw_episodes, list):
        raise PilotError("plan has no episodes")
    for episode in raw_episodes:
        if not isinstance(episode, Mapping):
            continue
        case = cases[str(episode["case_id"])]
        acceptable = set(case.grading.acceptable_actions)
        action = case.grading.expected_outcome
        if not bool(episode["control"]) and episode["arm"] == "repository-only":
            wrong = next(
                (
                    candidate
                    for candidate in case.query.allowed_actions
                    if candidate not in acceptable
                ),
                None,
            )
            if wrong is None:
                raise PilotError(f"case {case.case_id} has no wrong observable action")
            action = wrong
        samples.append(
            {
                "key": episode["key"],
                "child_run_id": f"synthetic-{episode['key']}",
                "raw_output_ref": f"synthetic/{episode['key']}.txt",
                "started_at": "2026-09-13T00:00:00Z",
                "finished_at": "2026-09-13T00:00:12Z",
                "model": PILOT_V2_MODEL,
                "prompt_digest": episode["prompt_digest"],
                "raw_output": json.dumps({"action": action}),
                "telemetry": {
                    **{metric: 1 for metric in REQUIRED_TELEMETRY if metric != "monetary_cost"},
                    "monetary_cost": 0.0,
                },
            }
        )
    return samples


def dry_run(root: Path | None = None) -> Json:
    """Build, validate, and synthetically aggregate the plan without a live call."""
    base = _base(root)
    plan = plan_document(base)
    problems = plan_problems(base)
    if problems:
        raise PilotError("; ".join(problems))
    result = record(plan, _synthetic_samples(plan, base), base)
    problems = result_problems(result)
    if problems:
        raise PilotError("; ".join(problems))
    if result["status"] != "complete" or result["verdict"] != "proceed":
        raise PilotError(
            f"dry run did not aggregate to proceed: {result['status']}/{result['verdict']}"
        )
    return result


def dry_run_problems(root: Path | None = None) -> list[str]:
    """Return the problems the zero-live dry run finds; empty means it passed."""
    try:
        dry_run(root)
    except PilotError as error:
        return str(error).split("; ")
    return []


def verify() -> list[str]:
    """Return the internal inconsistencies that would make the harness unusable."""
    problems: list[str] = []
    if PILOT_V2_PROTOCOL != "memory-pilot-v2":
        problems.append("protocol literal drifted")
    if PILOT_V2_ARMS != ("repository-only", "oracle"):
        problems.append("pilot arms drifted")
    if PILOT_V2_REPETITIONS < memory_contract.MIN_REPETITIONS:
        problems.append("repetitions are below the contract minimum")
    if PILOT_V2_SEPARATION_THRESHOLD * 2 <= PILOT_V2_REPETITIONS:
        problems.append("separation threshold is not a strict majority")
    if PILOT_V2_CONTROL_THRESHOLD * 2 <= PILOT_V2_REPETITIONS:
        problems.append("control threshold is not a strict majority")
    if PILOT_V2_BATCH_SIZE * PILOT_V2_BATCHES < 1:
        problems.append("batch geometry is empty")
    if set(pin_document("sha256:x", "rev")) != set(memory_contract.PIN_FIELDS):
        problems.append("pins do not cover every contract pin field")
    if PILOT_V2_MODEL != "deepseek/deepseek-v4-flash":
        problems.append("model literal drifted")
    if not SYSTEM_PROMPT.strip():
        problems.append("the child system prompt is empty")
    return problems


_USAGE = (
    "usage: tangle benchmark pilot plan\n"
    "       tangle benchmark pilot dry-run\n"
    "       tangle benchmark pilot record --input RAW.json [--output RESULT.json]\n"
    "Preregister, dry-run, or record the isolated repeated memory separability pilot."
)


def _print_plan(plan: Mapping[str, Any]) -> None:
    print(field("protocol", plan["protocol"]))
    print(field("harness", plan["harness"]))
    print(field("child_profile", plan["child_profile"]))
    print(field("model", plan["model"]))
    print(field("reasoning_effort", plan["reasoning_effort"]))
    print(field("corpus_digest", plan["corpus_digest"]))
    print(field("plan_digest", plan["plan_digest"]))
    print(field("samples", plan["sample_count"]))
    print(field("batches", plan["batch_count"]))
    episodes = plan["episodes"]
    print(
        table(
            "episodes",
            "key,batch,case,arm,repetition",
            (
                (
                    episode["key"],
                    episode["batch"],
                    episode["case_id"],
                    episode["arm"],
                    episode["repetition"],
                )
                for episode in episodes
            ),
        )
    )


def _read_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PilotError(f"cannot read JSON {path}: {error}") from error


def _record_cli(arguments: Sequence[str]) -> int:
    input_path: str | None = None
    output_path: str | None = None
    values = list(arguments)
    index = 0
    while index < len(values):
        name = values[index]
        if name == "--input" and index + 1 < len(values):
            input_path = values[index + 1]
            index += 2
            continue
        if name == "--output" and index + 1 < len(values):
            output_path = values[index + 1]
            index += 2
            continue
        raise PilotError(f"unknown argument: {name}")
    if input_path is None:
        raise PilotError("record requires --input")
    document = _read_json(input_path)
    if not isinstance(document, Mapping):
        raise PilotError("record input must be a JSON object")
    samples = document.get("samples")
    if not isinstance(samples, list):
        raise PilotError("record input must carry a samples list")
    result = record(plan_document(), samples)
    problems = result_problems(result)
    if problems:
        raise PilotError("; ".join(problems))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if output_path is None:
        print(rendered, end="")
    else:
        Path(output_path).write_text(rendered, encoding="utf-8")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``plan``, ``dry-run``, or ``record`` for the pilot harness."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0 if arguments else 2
    command = arguments[0]
    try:
        if command == "plan":
            if len(arguments) != 1:
                raise PilotError(f"unknown argument: {arguments[1]}")
            _print_plan(plan_document())
            return 0
        if command == "dry-run":
            if len(arguments) != 1:
                raise PilotError(f"unknown argument: {arguments[1]}")
            result = dry_run()
            print(field("protocol", result["protocol"]))
            print(field("status", result["status"]))
            print(field("verdict", result["verdict"]))
            print(field("samples", result["sample_count"]))
            print("dry-run: passed")
            return 0
        if command == "record":
            return _record_cli(arguments[1:])
        print(f"error: unknown pilot command: {command}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2
    except PilotError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
