"""Matched five-arm causal runner for the frozen memory corpus.

This module realizes Stage 2 of the staged plan in
:mod:`research.agent-memory-theory-evaluation` and the causal-arm section of the
frozen contract in :mod:`research.agent-memory-evaluation-contract`. It is the
machine-readable half of
``research/agent-memory-causal-preregistration.md``.

Every arm shares the *same* task prompt, observable-file bytes, tools, model
settings, memory budget, repetition count, and deterministic grader. Only the
available persistent history differs, so a difference in the graded action is
attributable to memory construction and retrieval rather than to a confound.
The five arms are the contract's canonical ids: ``repository-only`` (floor),
``raw-history``, ``flat-memory``, ``braintree`` (system under test), and
``oracle`` (ceiling).

The module separates **planning** from **recording**, exactly as the pilot
harness does. Planning is a pure function of the frozen corpus, the model list,
and the repetition count; recording ingests raw child outputs and telemetry,
enforces the correctness-before-cost gate, and reports paired effects with a
percentile bootstrap confidence interval, token and interaction costs, and
failures. All literals come from :mod:`braintree.memory_contract`, so the runner
cannot drift from the protocol it implements.

The module makes **zero live model calls**. ``plan``, ``dry-run``, and
``record`` are offline; a live or paid run needs the contract's recorded owner
authorization first, which this module documents but never manufactures.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import statistics
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import memory_contract, memory_corpus, memory_pilot, memory_scenario
from .toon import field, table

__all__ = [
    "CAUSAL_ARMS",
    "CAUSAL_BASELINE_ARMS",
    "CAUSAL_BATCH_COUNT",
    "CAUSAL_BATCH_SIZE",
    "CAUSAL_BOOTSTRAP_RESAMPLES",
    "CAUSAL_BOOTSTRAP_SEED",
    "CAUSAL_BUDGET",
    "CAUSAL_CEILING_ARM",
    "CAUSAL_CHILD_PROFILE",
    "CAUSAL_CONFIDENCE_LEVEL",
    "CAUSAL_CONFIRMATORY_PROTOCOL",
    "CAUSAL_CONFIRMATORY_SPLIT",
    "CAUSAL_CONTRASTS",
    "CAUSAL_DECISION_CONTRASTS",
    "CAUSAL_FIXTURE_VERSION",
    "CAUSAL_GRADER",
    "CAUSAL_GRADER_VERSION",
    "CAUSAL_MEMORY_BUDGET",
    "CAUSAL_MIN_MODELS",
    "CAUSAL_MODELS",
    "CAUSAL_PROMPT_REVISION",
    "CAUSAL_PROTOCOL",
    "CAUSAL_REASONING_EFFORT",
    "CAUSAL_REPETITIONS",
    "CAUSAL_TOOL_REVISION",
    "CAUSAL_TREATMENT_ARM",
    "CausalError",
    "CausalOutputError",
    "arm_memory",
    "bootstrap_confidence_interval",
    "build_fixture",
    "build_plan",
    "dry_run",
    "dry_run_problems",
    "fixture_digest",
    "held_out_cases",
    "main",
    "paired_effects",
    "plan_digest",
    "plan_document",
    "plan_problems",
    "record",
    "render_prompt",
    "result_problems",
    "source_revision",
    "verify",
]

Json = dict[str, Any]

CAUSAL_PROTOCOL = "memory-causal-v1"
CAUSAL_CONFIRMATORY_PROTOCOL = "memory-causal-confirmatory-v1"
CAUSAL_CONFIRMATORY_SPLIT = "held-out"
# The exploratory runner plans only the development split; the frozen held-out
# split is the confirmatory split, and a plan's protocol names which one it is.
CAUSAL_SPLIT_PROTOCOLS = {
    "development": CAUSAL_PROTOCOL,
    CAUSAL_CONFIRMATORY_SPLIT: CAUSAL_CONFIRMATORY_PROTOCOL,
}
CAUSAL_ARMS = memory_contract.CANONICAL_ARM_IDS
CAUSAL_BASELINE_ARMS = ("repository-only", "raw-history", "flat-memory")
CAUSAL_TREATMENT_ARM = "braintree"
CAUSAL_CEILING_ARM = "oracle"
# The two contrasts the contract's support criterion names; the others are
# reported for diagnosis but do not decide the claim.
CAUSAL_DECISION_CONTRASTS = (("braintree", "repository-only"), ("braintree", "raw-history"))
CAUSAL_CONTRASTS = (
    *CAUSAL_DECISION_CONTRASTS,
    ("braintree", "flat-memory"),
    ("oracle", "braintree"),
)

# Three text models cover the contract's "three models or model families"
# minimum. They are one provider family; the preregistration records that a
# second family is a later-confirmation requirement, not a current claim.
CAUSAL_MODELS = (
    "deepseek/deepseek-flash",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
)
CAUSAL_REASONING_EFFORT = "high"
CAUSAL_REPETITIONS = memory_contract.MIN_REPETITIONS
CAUSAL_MIN_MODELS = memory_contract.MIN_MODELS

# The memory budget every arm shares: a bounded statement count. An arm with no
# history uses none; raw-history, flat-memory, and braintree retrieve up to the
# cap; the oracle injects the minimal gold, which the schema keeps small.
CAUSAL_MEMORY_BUDGET = 8
CAUSAL_BOOTSTRAP_RESAMPLES = memory_contract.BOOTSTRAP_RESAMPLES
CAUSAL_BOOTSTRAP_SEED = 20260913
CAUSAL_CONFIDENCE_LEVEL = memory_contract.CONFIDENCE_LEVEL

CAUSAL_CHILD_PROFILE = "memory-pilot-child"
CAUSAL_GRADER = "memory_scenario.grade"
CAUSAL_HARNESS = "pi-subagents"
CAUSAL_FIXTURE_VERSION = "memory-causal-fixture-1"
CAUSAL_PROMPT_REVISION = "memory-causal-prompt-1"
CAUSAL_TOOL_REVISION = "no-tools"
CAUSAL_GRADER_VERSION = "memory-scenario-v1"
CAUSAL_BUDGET = "one isolated child turn per episode; no tools; no retries"
CAUSAL_ALLOWED_COMMANDS: tuple[str, ...] = ()

# pi-subagents launches at most 64 children per run; 60 keeps a full model's
# repetitions inside one batch. 12 cases x 5 arms x 3 models x 3 repetitions =
# 540 episodes, nine deterministic batches.
CAUSAL_BATCH_SIZE = 60
CAUSAL_BATCH_COUNT = 9


class CausalError(ValueError):
    """The causal plan, a fixture, or a recorded sample is malformed."""


CausalOutputError = memory_pilot.PilotOutputError

_STOPWORDS = frozenset(
    "a an the and or of to in is are was were be been being it its this that "
    "these those for on with as by at from we you i they he she them us our "
    "your not no do does did so if then than but can could should would may "
    "might must will shall have has had".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _base(root: Path | None) -> Path:
    return _repo_root() if root is None else Path(root)


def source_revision(root: Path | None = None) -> str:
    """Return the runner source revision, or ``unknown`` outside a Git checkout."""
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


def _model_slug(model: str) -> str:
    return model.split("/")[-1]


def _content_tokens(text: str) -> set[str]:
    return {
        word
        for word in _TOKEN.findall(text.lower())
        if word not in _STOPWORDS and len(word) > 1
    }


def _rank_episodes(
    case: memory_scenario.Scenario, budget: int
) -> tuple[memory_scenario.Episode, ...]:
    """Return the case's episodes lexically ranked against the task, bounded.

    The rank is a deterministic, arm-neutral retrieval baseline: episodes whose
    statement shares the most content words with the task come first, ties break
    by episode order, and the selected episodes are returned in sequence order.
    """
    task_tokens = _content_tokens(case.query.task)
    ordered = sorted(
        case.construction.episodes,
        key=lambda episode: (
            -len(_content_tokens(episode.statement) & task_tokens),
            episode.sequence,
        ),
    )
    selected = ordered[:budget]
    return tuple(sorted(selected, key=lambda episode: episode.sequence))


def arm_memory(
    case: memory_scenario.Scenario, arm: str, budget: int = CAUSAL_MEMORY_BUDGET
) -> tuple[str, ...]:
    """Return the persistent memory one causal arm holds at query time.

    ``repository-only`` holds none. ``raw-history`` and ``flat-memory`` both
    retrieve the same bounded public episodes, the former as transcript
    statements and the latter as untyped timestamped notes. ``braintree``
    resolves the case's dependency and decision chain (the episodes the gold
    evidence cites) and holds those raw episodes. ``oracle`` is injected with
    the minimal distilled gold evidence. Every arm is bounded by ``budget``.
    """
    if arm not in CAUSAL_ARMS:
        raise CausalError(f"unknown causal arm: {arm}")
    if budget < 0:
        raise CausalError("memory budget must be non-negative")
    if arm == "repository-only":
        return ()
    if arm == "raw-history":
        return tuple(episode.statement for episode in _rank_episodes(case, budget))
    if arm == "flat-memory":
        return tuple(
            f"note {episode.sequence}: {episode.statement}"
            for episode in _rank_episodes(case, budget)
        )
    if arm == "braintree":
        deciding = {
            source
            for evidence in case.grading.gold_evidence
            for source in evidence.source_episodes
        }
        chain = [episode for episode in case.construction.episodes if episode.id in deciding]
        return tuple(episode.statement for episode in chain[:budget])
    # oracle
    return tuple(evidence.statement for evidence in case.grading.gold_evidence[:budget])


def build_fixture(
    case: memory_scenario.Scenario,
    arm: str,
    root: Path | None = None,
    cache: dict[str, memory_pilot.ObservableFile] | None = None,
) -> memory_pilot.PilotFixture:
    """Build one arm's fixture with identical observable bytes for every arm."""
    if arm not in CAUSAL_ARMS:
        raise CausalError(f"unknown causal arm: {arm}")
    base = _base(root)
    files: list[memory_pilot.ObservableFile] = []
    for path in case.query.observable_paths:
        if cache is not None and path in cache:
            files.append(cache[path])
            continue
        resolved = memory_pilot._resolve_observable(base, path)
        if cache is not None:
            cache[path] = resolved
        files.append(resolved)
    return memory_pilot.PilotFixture(
        case_id=case.case_id,
        family=case.family,
        arm=arm,
        control=memory_corpus.is_control(case),
        task=case.query.task,
        observable=tuple(files),
        memory=arm_memory(case, arm),
        allowed_actions=case.query.allowed_actions,
    )


def render_prompt(fixture: memory_pilot.PilotFixture) -> str:
    """Render the shared arm prompt; delegate to the pilot renderer verbatim."""
    return memory_pilot.render_prompt(fixture)


def fixture_digest(fixture: memory_pilot.PilotFixture) -> str:
    """Return the content address of one causal arm fixture."""
    return memory_pilot.fixture_digest(fixture)


def _fixture_hashes(
    case: memory_scenario.Scenario,
    arm: str,
    root: Path,
    cache: dict[str, memory_pilot.ObservableFile],
) -> tuple[str, str]:
    fixture = build_fixture(case, arm, root, cache)
    return (
        memory_pilot.prompt_digest(render_prompt(fixture)),
        memory_pilot.fixture_digest(fixture),
    )


def held_out_cases(
    corpus: Sequence[memory_corpus.Envelope],
) -> tuple[memory_scenario.Scenario, ...]:
    """Return the whole frozen held-out split, ordered by family then case id.

    The confirmatory set is a pure function of the corpus digest, so no case can
    be included or dropped after an outcome is seen. It spans every family and
    curation group and carries the corpus's held-out controls.
    """
    by_family = {
        envelope.family: sorted(
            (case for case in envelope.cases if case.split == CAUSAL_CONFIRMATORY_SPLIT),
            key=lambda case: case.case_id,
        )
        for envelope in corpus
    }
    return tuple(
        case
        for family in memory_contract.SCENARIO_FAMILIES
        for case in by_family.get(family, [])
    )


def _split_cases(
    corpus: Sequence[memory_corpus.Envelope], split: str
) -> tuple[memory_scenario.Scenario, ...]:
    """Return the deterministic case set for one causal split."""
    if split == "development":
        return memory_corpus.pilot_subset(corpus)
    if split == CAUSAL_CONFIRMATORY_SPLIT:
        return held_out_cases(corpus)
    raise CausalError(f"unknown causal split: {split}")


def _causal_cases(
    root: Path | None = None, split: str = "development"
) -> tuple[memory_scenario.Scenario, ...]:
    """Return the deterministic case set for one causal split.

    The set is a pure function of the frozen corpus, so it cannot be chosen
    after an outcome is seen. Both splits span every family and curation group
    and pair memory-required cases with memory-irrelevant controls.
    """
    return _split_cases(memory_corpus.load_corpus(_base(root)), split)


def _episode_key(case_id: str, arm: str, model: str, repetition: int) -> str:
    return f"{case_id}--{arm}--{_model_slug(model)}--r{repetition}"


def build_plan(
    root: Path | None = None,
    models: Sequence[str] = CAUSAL_MODELS,
    repetitions: int = CAUSAL_REPETITIONS,
    split: str = "development",
) -> tuple[Json, ...]:
    """Return every ``(case, arm, model, repetition)`` episode, batch-ordered."""
    if repetitions < memory_contract.MIN_REPETITIONS:
        raise CausalError(
            f"repetitions {repetitions} below the contract minimum "
            f"{memory_contract.MIN_REPETITIONS}"
        )
    if len(models) < memory_contract.MIN_MODELS:
        raise CausalError(
            f"{len(models)} models below the contract minimum {memory_contract.MIN_MODELS}"
        )
    if split not in CAUSAL_SPLIT_PROTOCOLS:
        raise CausalError(f"unknown causal split: {split}")
    base = _base(root)
    cases = _causal_cases(base, split)
    cache: dict[str, memory_pilot.ObservableFile] = {}
    prompt_cache: dict[tuple[str, str], tuple[str, str]] = {}
    episodes: list[Json] = []
    for case in cases:
        for arm in CAUSAL_ARMS:
            prompt_hash, fixture_hash = _fixture_hashes(case, arm, base, cache)
            prompt_cache[(case.case_id, arm)] = (prompt_hash, fixture_hash)
        for model in models:
            for arm in CAUSAL_ARMS:
                prompt_hash, fixture_hash = prompt_cache[(case.case_id, arm)]
                for repetition in range(1, repetitions + 1):
                    episodes.append(
                        {
                            "key": _episode_key(case.case_id, arm, model, repetition),
                            "batch": len(episodes) // CAUSAL_BATCH_SIZE + 1,
                            "case_id": case.case_id,
                            "family": case.family,
                            "arm": arm,
                            "model": model,
                            "repetition": repetition,
                            "control": memory_corpus.is_control(case),
                            "prompt_digest": prompt_hash,
                            "fixture_digest": fixture_hash,
                            "launch": {
                                "agent": CAUSAL_CHILD_PROFILE,
                                "model": model,
                                "thinking": CAUSAL_REASONING_EFFORT,
                                "context": "fresh",
                            },
                        }
                    )
    return tuple(episodes)


def pin_document(
    corpus_digest: str,
    revision: str,
    models: Sequence[str],
    protocol: str = CAUSAL_PROTOCOL,
) -> Json:
    """Return every contract pin field the causal run must preserve."""
    listed = tuple(models)
    return {
        "protocol": protocol,
        "corpus-digest": corpus_digest,
        "fixture-version": CAUSAL_FIXTURE_VERSION,
        "source-revision": revision,
        "model": ",".join(listed),
        "model-revision": ",".join(_model_slug(model) for model in listed),
        "reasoning-effort": CAUSAL_REASONING_EFFORT,
        "prompt-revision": CAUSAL_PROMPT_REVISION,
        "tool-revision": CAUSAL_TOOL_REVISION,
        "budget": CAUSAL_BUDGET,
        "allowed-commands": list(CAUSAL_ALLOWED_COMMANDS),
        "grader-version": CAUSAL_GRADER_VERSION,
    }


def plan_digest(document: Mapping[str, Any]) -> str:
    """Return the content address of a plan's pins and episode identities."""
    raw_episodes = document.get("episodes")
    episodes = raw_episodes if isinstance(raw_episodes, list) else []
    keys = (
        "key",
        "batch",
        "case_id",
        "arm",
        "model",
        "repetition",
        "prompt_digest",
        "fixture_digest",
    )
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


def plan_document(
    root: Path | None = None,
    models: Sequence[str] = CAUSAL_MODELS,
    repetitions: int = CAUSAL_REPETITIONS,
    split: str = "development",
) -> Json:
    """Return the deterministic five-arm causal plan, including a plan digest."""
    if split not in CAUSAL_SPLIT_PROTOCOLS:
        raise CausalError(f"unknown causal split: {split}")
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    digest = memory_corpus.corpus_digest(corpus)
    listed = tuple(models)
    protocol = CAUSAL_SPLIT_PROTOCOLS[split]
    episodes = build_plan(base, listed, repetitions, split)
    batch_count = (len(episodes) + CAUSAL_BATCH_SIZE - 1) // CAUSAL_BATCH_SIZE
    document: Json = {
        "protocol": protocol,
        "harness": CAUSAL_HARNESS,
        "grader": CAUSAL_GRADER,
        "child_profile": CAUSAL_CHILD_PROFILE,
        "arms": list(CAUSAL_ARMS),
        "models": list(listed),
        "reasoning_effort": CAUSAL_REASONING_EFFORT,
        "corpus_digest": digest,
        "split": split,
        "memory_budget": CAUSAL_MEMORY_BUDGET,
        "pins": pin_document(digest, source_revision(base), listed, protocol),
        "case_count": len({str(episode["case_id"]) for episode in episodes}),
        "arm_count": len(CAUSAL_ARMS),
        "model_count": len(listed),
        "repetitions": repetitions,
        "sample_count": len(episodes),
        "batch_size": CAUSAL_BATCH_SIZE,
        "batch_count": batch_count,
        "episodes": list(episodes),
    }
    document["plan_digest"] = plan_digest(document)
    return document


def plan_problems(
    root: Path | None = None,
    models: Sequence[str] = CAUSAL_MODELS,
    repetitions: int = CAUSAL_REPETITIONS,
    split: str = "development",
) -> list[str]:
    """Return the structural problems that make the generated plan unusable."""
    base = _base(root)
    listed = tuple(models)
    problems: list[str] = []
    if split not in CAUSAL_SPLIT_PROTOCOLS:
        return [f"plan: unknown split {split!r}"]
    if len(listed) < memory_contract.MIN_MODELS:
        problems.append("plan: fewer than three models")
    if repetitions < memory_contract.MIN_REPETITIONS:
        problems.append("plan: fewer than three repetitions")
    if len(set(listed)) != len(listed):
        problems.append("plan: duplicate models")
    cases = _causal_cases(base, split)
    episodes = build_plan(base, listed, repetitions, split)
    expected_keys = {
        _episode_key(case.case_id, arm, model, repetition)
        for case in cases
        for model in listed
        for arm in CAUSAL_ARMS
        for repetition in range(1, repetitions + 1)
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
        if not isinstance(batch, int) or batch < 1:
            problems.append(f"plan: episode {episode.get('key')} has batch {batch!r}")
            continue
        batches[batch] = batches.get(batch, 0) + 1
    expected_count = len(cases) * len(CAUSAL_ARMS) * len(listed) * repetitions
    expected_batch_count = (expected_count + CAUSAL_BATCH_SIZE - 1) // CAUSAL_BATCH_SIZE
    if sum(batches.values()) != expected_count:
        problems.append(f"plan: {sum(batches.values())} episodes is not {expected_count}")
    for batch, count in sorted(batches.items()):
        if count > CAUSAL_BATCH_SIZE:
            problems.append(f"plan: batch {batch} has {count} episodes over the cap")
    if sorted(batches) != list(range(1, expected_batch_count + 1)):
        problems.append(
            f"plan: batches {sorted(batches)} are not 1..{expected_batch_count}"
        )
    cache: dict[str, memory_pilot.ObservableFile] = {}
    cases_by_id = {case.case_id: case for case in cases}
    for episode in episodes:
        case = cases_by_id.get(str(episode["case_id"]))
        if case is None:
            problems.append(f"plan: unknown case {episode['case_id']}")
            continue
        prompt_hash, fixture_hash = _fixture_hashes(case, str(episode["arm"]), base, cache)
        if episode.get("prompt_digest") != prompt_hash:
            problems.append(f"plan: prompt digest drifted for {episode.get('key')}")
        if episode.get("fixture_digest") != fixture_hash:
            problems.append(f"plan: fixture digest drifted for {episode.get('key')}")
    document = plan_document(base, listed, repetitions, split)
    if document["plan_digest"] != plan_digest(document):
        problems.append("plan: plan digest is not a content address of the plan")
    if set(document["pins"]) != set(memory_contract.PIN_FIELDS):
        problems.append("plan: pins do not cover every contract pin field")
    if list(document["arms"]) != list(CAUSAL_ARMS):
        problems.append("plan: arm list does not match the contract")
    return problems


def bootstrap_confidence_interval(
    effects: Sequence[float],
    resamples: int = CAUSAL_BOOTSTRAP_RESAMPLES,
    level: float = CAUSAL_CONFIDENCE_LEVEL,
    seed: int = CAUSAL_BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Return a percentile bootstrap CI for the mean of paired effects.

    The bootstrap unit is whatever the caller passes. The runner passes one
    mean effect per ``(case, model)`` stratum, so repeated draws inside a case do
    not masquerade as independent evidence. Determinism comes from a fixed seed.
    """
    values = [float(effect) for effect in effects]
    if not values:
        raise CausalError("cannot bootstrap an empty effect list")
    if resamples < 1_000:
        raise CausalError("bootstrap resamples are too few for a stable interval")
    rng = random.Random(seed)
    count = len(values)
    means: list[float] = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(count):
            total += values[rng.randrange(count)]
        means.append(total / count)
    means.sort()
    alpha = (1.0 - level) / 2.0
    low_index = max(0, min(count - 1, int(alpha * resamples)))
    high_index = max(0, min(resamples - 1, int((1.0 - alpha) * resamples) - 1))
    return means[low_index], means[high_index]


def _telemetry(raw: Any) -> tuple[Json, list[str]]:
    return memory_pilot._telemetry(raw)


def _latency_ms(started_at: Any, finished_at: Any) -> int:
    return memory_pilot._latency_ms(started_at, finished_at)


def _empty_sample(
    episode: Mapping[str, Any], case: memory_scenario.Scenario, raw: Mapping[str, Any]
) -> Json:
    return {
        "key": episode["key"],
        "case_id": episode["case_id"],
        "family": episode["family"],
        "arm": episode["arm"],
        "model": episode["model"],
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
    episode: Mapping[str, Any], raw: Mapping[str, Any], case: memory_scenario.Scenario
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
    if raw.get("model") != episode["model"]:
        problems.append(f"model is not pinned to {episode['model']}")
    if record["prompt_digest"] != episode["prompt_digest"]:
        problems.append("prompt digest does not match the plan")
    try:
        latency_ms = _latency_ms(record["started_at"], record["finished_at"])
    except memory_pilot.PilotError as error:
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
        action = memory_pilot.parse_action(str(record["raw_output"]), case.query.allowed_actions)
    except memory_pilot.PilotOutputError as error:
        record["parse_error"] = str(error)
        action = ""
    record["action"] = action
    grade = memory_scenario.grade(case, action)
    record["correct"] = grade.correct
    record["credit"] = grade.credit
    record["regret"] = grade.regret
    return record


def _cost_record(samples: Sequence[Mapping[str, Any]]) -> Json:
    admitted = [sample for sample in samples if sample["correct"]]
    totals: Json = {metric: 0 for metric in memory_contract.TOKEN_METRICS}
    interactions: Json = {metric: 0 for metric in memory_contract.INTERACTION_METRICS}
    for sample in admitted:
        telemetry = sample["telemetry"]
        for metric in memory_contract.TOKEN_METRICS:
            totals[metric] += int(telemetry[metric])
        for metric in memory_contract.INTERACTION_METRICS:
            if metric == "monetary_cost":
                interactions[metric] = round(
                    float(interactions[metric]) + float(telemetry[metric]), 6
                )
            else:
                interactions[metric] += int(telemetry[metric])
    return {"admitted": len(admitted), "tokens": totals, "interaction": interactions}


def paired_effects(
    samples: Sequence[Mapping[str, Any]],
    treatment: str,
    baseline: str,
) -> Json:
    """Return the paired treatment-minus-baseline effect within case and model.

    A pair is one ``(case, model, repetition)`` present for both arms. Each
    ``(case, model)`` stratum contributes its mean difference so repetitions
    inside a case are not counted as independent evidence; the overall estimate
    is the mean of those strata with a percentile bootstrap interval.
    """
    indexed: dict[tuple[str, str, str, int], dict[str, Mapping[str, Any]]] = {}
    for sample in samples:
        if sample.get("incomplete"):
            continue
        key = (
            str(sample["case_id"]),
            str(sample["model"]),
            str(sample["arm"]),
            int(sample["repetition"]),
        )
        indexed.setdefault(key, {})[str(sample["arm"])] = sample
    strata: dict[tuple[str, str], list[float]] = {}
    seen: set[tuple[str, str, int]] = set()
    n_pairs = 0
    for (case_id, model, arm, repetition), _pair in indexed.items():
        if arm != treatment:
            continue
        ident = (case_id, model, repetition)
        if ident in seen:
            continue
        seen.add(ident)
        treated = indexed.get((case_id, model, treatment, repetition), {}).get(treatment)
        control = indexed.get((case_id, model, baseline, repetition), {}).get(baseline)
        if treated is None or control is None:
            continue
        difference = float(treated["correct"]) - float(control["correct"])
        strata.setdefault((case_id, model), []).append(difference)
        n_pairs += 1
    stratum_means = [statistics.fmean(values) for values in strata.values()]
    if not stratum_means:
        return {
            "treatment": treatment,
            "baseline": baseline,
            "n_pairs": 0,
            "n_strata": 0,
            "mean_effect": None,
            "ci_low": None,
            "ci_high": None,
        }
    mean_effect = statistics.fmean(stratum_means)
    ci_low, ci_high = bootstrap_confidence_interval(stratum_means)
    return {
        "treatment": treatment,
        "baseline": baseline,
        "n_pairs": n_pairs,
        "n_strata": len(stratum_means),
        "mean_effect": mean_effect,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def _case_records(
    plan: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
) -> list[Json]:
    order: list[str] = []
    raw_episodes = plan.get("episodes")
    episode_rows = raw_episodes if isinstance(raw_episodes, list) else []
    for episode in episode_rows:
        if not isinstance(episode, Mapping):
            continue
        case_id = str(episode["case_id"])
        if case_id not in order:
            order.append(case_id)
    records: list[Json] = []
    for case_id in order:
        models = sorted(
            {
                str(episode["model"])
                for episode in episode_rows
                if episode["case_id"] == case_id
            }
        )
        for model in models:
            members = [
                sample
                for sample in samples
                if sample["case_id"] == case_id and sample["model"] == model
            ]
            arm_correct: Json = {}
            for arm in CAUSAL_ARMS:
                values = [
                    bool(sample["correct"])
                    for sample in members
                    if sample["arm"] == arm and not sample["incomplete"]
                ]
                arm_correct[arm] = values
            records.append(
                {
                    "case_id": case_id,
                    "model": model,
                    "control": any(bool(sample["control"]) for sample in members),
                    "correct_by_arm": arm_correct,
                    "effects": {
                        f"{treatment}-minus-{baseline}": (
                            statistics.fmean(
                                float(a) - float(b)
                                for a, b in zip(
                                    arm_correct[treatment], arm_correct[baseline], strict=False
                                )
                            )
                            if arm_correct[treatment] and arm_correct[baseline]
                            else None
                        )
                        for treatment, baseline in CAUSAL_DECISION_CONTRASTS
                    },
                }
            )
    return records


def _evidence_label(plan: Mapping[str, Any], status: str) -> str:
    if status != "complete":
        return "untested"
    return "confirmatory" if plan.get("split") == "held-out" else "exploratory"


def _decision_label(
    plan: Mapping[str, Any], status: str, contrasts: Sequence[Mapping[str, Any]]
) -> str:
    """Return the contract verdict without overclaiming exploratory evidence."""
    if status != "complete":
        return "untested"
    if plan.get("split") != "held-out":
        return "exploratory"
    by_pair = {(record["treatment"], record["baseline"]): record for record in contrasts}
    for treatment, baseline in CAUSAL_DECISION_CONTRASTS:
        record = by_pair.get((treatment, baseline))
        if record is None or record.get("ci_low") is None or record["ci_low"] <= 0:
            return "rejected"
    return "confirmed"


def _reproduction(
    plan: Mapping[str, Any], plan_path: str, runs_root: str, out_path: str
) -> list[str]:
    """Return the exact offline commands that rebuild and analyze the plan.

    The live fan-out is a separate, authorized step: generate one isolated child
    per planned episode and launch the deterministic batches with pi-subagents,
    then feed the retained outputs to ``record``. The reproduction list keeps the
    plan digest so an analysis can be tied to the exact frozen fixture.
    """
    return [
        f"uv run braintree benchmark causal plan > {plan_path}",
        (
            f"# launch {plan.get('batch_count')} batches of at most "
            f"{plan.get('batch_size')} isolated children from {plan_path} "
            f"(owner authorization required; see the preregistration)"
        ),
        f"# retained async run root: {runs_root}",
        (
            "uv run braintree benchmark causal record "
            f"--input {runs_root}/samples.json --output {out_path}"
        ),
        "uv run braintree benchmark causal dry-run",
        f"# plan digest {plan.get('plan_digest')}",
        f"# corpus digest {plan.get('corpus_digest')}",
    ]


def record(
    plan: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    root: Path | None = None,
    plan_path: str = "plan.json",
    runs_root: str = "$TMPDIR",
    out_path: str = "benchmark/memory-causal-result.json",
) -> Json:
    """Ingest raw causal samples and return the preregistered analysis document."""
    base = _base(root)
    corpus = memory_corpus.load_corpus(base)
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    raw_episodes = plan.get("episodes")
    if not isinstance(raw_episodes, list) or not raw_episodes:
        raise CausalError("plan has no episodes")
    episodes = [episode for episode in raw_episodes if isinstance(episode, Mapping)]
    by_key = {str(episode["key"]): episode for episode in episodes}
    provided: dict[str, Mapping[str, Any]] = {}
    for raw in samples:
        if not isinstance(raw, Mapping):
            raise CausalError("a sample is not a JSON object")
        key = raw.get("key")
        if not isinstance(key, str) or key not in by_key:
            raise CausalError(f"sample key is not in the plan: {key!r}")
        if key in provided:
            raise CausalError(f"duplicate sample key: {key}")
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
    case_records = _case_records(plan, records)
    contrasts: list[Json] = []
    for treatment, baseline in CAUSAL_CONTRASTS:
        effect = paired_effects(records, treatment, baseline)
        effect["decision_contrast"] = (treatment, baseline) in CAUSAL_DECISION_CONTRASTS
        contrasts.append(effect)
    costs = {
        arm: _cost_record([sample for sample in records if sample["arm"] == arm])
        for arm in CAUSAL_ARMS
    }
    failures = []
    for sample in records:
        if sample["incomplete"]:
            kind = "infrastructure"
            detail = sample["infrastructure_error"]
        elif sample["parse_error"]:
            kind = "model-output"
            detail = sample["parse_error"]
        elif not sample["correct"]:
            kind = "incorrect-action"
            detail = f"chose {sample['action']!r}, expected {sample['expected_outcome']!r}"
        else:
            continue
        failures.append(
            {
                "key": sample["key"],
                "case_id": sample["case_id"],
                "arm": sample["arm"],
                "model": sample["model"],
                "repetition": sample["repetition"],
                "kind": kind,
                "detail": detail,
            }
        )
    pins = plan.get("pins")
    revision = pins.get("source-revision") if isinstance(pins, Mapping) else None
    return {
        "protocol": plan.get("protocol", CAUSAL_PROTOCOL),
        "status": status,
        "evidence": _evidence_label(plan, status),
        "decision": _decision_label(plan, status, contrasts),
        "harness": CAUSAL_HARNESS,
        "grader": CAUSAL_GRADER,
        "child_profile": CAUSAL_CHILD_PROFILE,
        "split": plan.get("split"),
        "arms": list(plan.get("arms", CAUSAL_ARMS)),
        "models": list(plan.get("models", [])),
        "reasoning_effort": CAUSAL_REASONING_EFFORT,
        "memory_budget": plan.get("memory_budget", CAUSAL_MEMORY_BUDGET),
        "corpus_digest": plan.get("corpus_digest"),
        "source_revision": revision,
        "pins": pins,
        "plan_digest": plan.get("plan_digest"),
        "case_count": plan.get("case_count"),
        "sample_count": len(records),
        "expected_sample_count": len(episodes),
        "repetitions": plan.get("repetitions"),
        "correctness_gate": {
            "gate": memory_contract.CORRECTNESS_GATE,
            "admitted": sum(1 for sample in records if sample["correct"]),
            "rejected": sum(1 for sample in records if not sample["correct"]),
        },
        "contrasts": contrasts,
        "cases": case_records,
        "costs": costs,
        "failures": failures,
        "samples": records,
        "missing_keys": missing,
        "incomplete_reasons": incomplete,
        "reproduction": _reproduction(plan, plan_path, runs_root, out_path),
    }


def result_problems(result: Mapping[str, Any]) -> list[str]:
    """Return the schema problems that make a recorded causal result unusable."""
    problems: list[str] = []
    for name in (
        "protocol",
        "status",
        "evidence",
        "decision",
        "harness",
        "grader",
        "split",
        "arms",
        "models",
        "corpus_digest",
        "pins",
        "plan_digest",
        "case_count",
        "sample_count",
        "expected_sample_count",
        "contrasts",
        "cases",
        "costs",
        "failures",
        "samples",
        "missing_keys",
        "reproduction",
    ):
        if name not in result:
            problems.append(f"result: missing {name}")
    if problems:
        return problems
    if result["protocol"] not in set(CAUSAL_SPLIT_PROTOCOLS.values()):
        problems.append("result: wrong protocol")
    if result["status"] not in {"complete", "incomplete"}:
        problems.append(f"result: unknown status {result['status']!r}")
    if result["evidence"] not in {"exploratory", "confirmatory", "untested"}:
        problems.append(f"result: unknown evidence {result['evidence']!r}")
    if result["decision"] not in memory_contract.DECISION_VERDICTS:
        problems.append(f"result: unknown decision {result['decision']!r}")
    if result["status"] == "complete":
        if result["missing_keys"]:
            problems.append("result: complete run has missing keys")
        if result["sample_count"] != result["expected_sample_count"]:
            problems.append("result: complete run does not cover every episode")
    elif result["decision"] != "untested":
        problems.append("result: incomplete run must be untested")
    if list(result["arms"]) != list(CAUSAL_ARMS):
        problems.append("result: arms do not match the contract")
    if len(result["models"]) < memory_contract.MIN_MODELS:
        problems.append("result: fewer than three models")
    pins = result["pins"]
    if not isinstance(pins, Mapping) or set(pins) != set(memory_contract.PIN_FIELDS):
        problems.append("result: pins do not cover every contract pin field")
    gate = result["correctness_gate"]
    if not isinstance(gate, Mapping) or gate.get("gate") != memory_contract.CORRECTNESS_GATE:
        problems.append("result: correctness gate drifted from the contract")
    for contrast in result["contrasts"]:
        if not isinstance(contrast, Mapping):
            problems.append("result: a contrast is not an object")
            continue
        for name in ("treatment", "baseline", "n_pairs", "mean_effect", "ci_low", "ci_high"):
            if name not in contrast:
                problems.append(f"result: contrast misses {name}")
        if contrast.get("mean_effect") is not None:
            low = contrast.get("ci_low")
            high = contrast.get("ci_high")
            if low is None or high is None or low > high:
                problems.append("result: contrast interval is not ordered")
    for arm in CAUSAL_ARMS:
        cost = result["costs"].get(arm)
        if not isinstance(cost, Mapping):
            problems.append(f"result: missing cost record for {arm}")
            continue
        for metric in memory_contract.TOKEN_METRICS:
            if metric not in cost.get("tokens", {}):
                problems.append(f"result: cost {arm} misses token {metric}")
        for metric in memory_contract.INTERACTION_METRICS:
            if metric not in cost.get("interaction", {}):
                problems.append(f"result: cost {arm} misses interaction {metric}")
    if not result["reproduction"]:
        problems.append("result: no reproduction commands")
    samples = result["samples"]
    if not isinstance(samples, list):
        problems.append("result: samples must be a list")
    else:
        for sample in samples:
            if not isinstance(sample, Mapping):
                problems.append("result: a sample is not an object")
                continue
            for name in ("key", "case_id", "arm", "model", "repetition"):
                if sample.get(name) in (None, ""):
                    problems.append(f"result: sample {sample.get('key')} misses {name}")
            if sample.get("incomplete"):
                continue
            for name in ("child_run_id", "raw_output_ref", "prompt_digest", "correct"):
                if sample.get(name) in (None, ""):
                    problems.append(f"result: sample {sample.get('key')} misses {name}")
            telemetry = sample.get("telemetry")
            if not isinstance(telemetry, Mapping):
                problems.append(f"result: sample {sample.get('key')} misses telemetry")
                continue
            for name in (*memory_pilot.REQUIRED_TELEMETRY, "latency_ms"):
                if name not in telemetry:
                    problems.append(f"result: sample {sample.get('key')} misses telemetry.{name}")
    return problems


def _synthetic_action(case: memory_scenario.Scenario, arm: str) -> str:
    """Return a zero-live synthetic action that exercises the decision gate.

    A baseline arm answers a memory-required case incorrectly and every arm
    answers a control correctly, so a held-out dry run aggregates to the
    ``confirmed`` verdict while a development dry run stays ``exploratory``.
    """
    if arm in {"repository-only", "raw-history", "flat-memory"} and not memory_corpus.is_control(
        case
    ):
        acceptable = set(case.grading.acceptable_actions)
        for candidate in case.query.allowed_actions:
            if candidate not in acceptable:
                return candidate
    return case.grading.expected_outcome


def _synthetic_samples(plan: Mapping[str, Any], root: Path) -> list[Json]:
    """Return a zero-live synthetic sample set that must aggregate ``complete``."""
    corpus = memory_corpus.load_corpus(root)
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    samples: list[Json] = []
    raw_episodes = plan.get("episodes")
    if not isinstance(raw_episodes, list):
        raise CausalError("plan has no episodes")
    for episode in raw_episodes:
        if not isinstance(episode, Mapping):
            continue
        case = cases[str(episode["case_id"])]
        samples.append(
            {
                "key": episode["key"],
                "child_run_id": f"synthetic-{episode['key']}",
                "raw_output_ref": f"synthetic/{episode['key']}.txt",
                "started_at": "2026-09-13T00:00:00Z",
                "finished_at": "2026-09-13T00:00:12Z",
                "model": episode["model"],
                "prompt_digest": episode["prompt_digest"],
                "raw_output": json.dumps(
                    {"action": _synthetic_action(case, str(episode["arm"]))}
                ),
                "telemetry": {
                    **{
                        metric: 1
                        for metric in memory_pilot.REQUIRED_TELEMETRY
                        if metric != "monetary_cost"
                    },
                    "monetary_cost": 0.0,
                },
            }
        )
    return samples


def dry_run(root: Path | None = None, split: str = "development") -> Json:
    """Build, validate, and synthetically analyze the plan without a live call."""
    base = _base(root)
    plan = plan_document(base, split=split)
    problems = plan_problems(base, split=split)
    if problems:
        raise CausalError("; ".join(problems))
    result = record(plan, _synthetic_samples(plan, base), base)
    problems = result_problems(result)
    if problems:
        raise CausalError("; ".join(problems))
    if result["status"] != "complete":
        raise CausalError(f"dry run did not aggregate complete: {result['status']}")
    expected = _evidence_label(plan, "complete")
    if result["evidence"] != expected:
        raise CausalError(f"{split} dry run is not {expected}: {result['evidence']}")
    return result


def dry_run_problems(root: Path | None = None, split: str = "development") -> list[str]:
    """Return the problems the zero-live dry run finds; empty means it passed."""
    try:
        dry_run(root, split)
    except CausalError as error:
        return str(error).split("; ")
    return []


def verify() -> list[str]:
    """Return the internal inconsistencies that would make the runner unusable."""
    problems: list[str] = []
    if CAUSAL_PROTOCOL != "memory-causal-v1":
        problems.append("protocol literal drifted")
    if CAUSAL_CONFIRMATORY_PROTOCOL != "memory-causal-confirmatory-v1":
        problems.append("confirmatory protocol literal drifted")
    if set(CAUSAL_SPLIT_PROTOCOLS) != set(memory_contract.SPLITS):
        problems.append("protocol map does not cover the contract splits")
    if CAUSAL_SPLIT_PROTOCOLS.get("development") != CAUSAL_PROTOCOL:
        problems.append("development split protocol drifted")
    if tuple(CAUSAL_ARMS) != memory_contract.CANONICAL_ARM_IDS:
        problems.append("arms drifted from the contract")
    if set(CAUSAL_BASELINE_ARMS) | {CAUSAL_TREATMENT_ARM, CAUSAL_CEILING_ARM} != set(CAUSAL_ARMS):
        problems.append("the arm partition does not cover the canonical arms")
    if set(CAUSAL_BASELINE_ARMS) & {CAUSAL_TREATMENT_ARM, CAUSAL_CEILING_ARM}:
        problems.append("baseline and treatment arms overlap")
    if len(CAUSAL_MODELS) < memory_contract.MIN_MODELS:
        problems.append("fewer than three models")
    if len(set(CAUSAL_MODELS)) != len(CAUSAL_MODELS):
        problems.append("duplicate causal models")
    if CAUSAL_REPETITIONS < memory_contract.MIN_REPETITIONS:
        problems.append("repetitions below the contract minimum")
    if CAUSAL_BOOTSTRAP_RESAMPLES < memory_contract.BOOTSTRAP_RESAMPLES:
        problems.append("bootstrap resamples below the contract minimum")
    if CAUSAL_CONFIDENCE_LEVEL != memory_contract.CONFIDENCE_LEVEL:
        problems.append("confidence level drifted from the contract")
    if CAUSAL_BATCH_SIZE * CAUSAL_BATCH_COUNT < len(CAUSAL_MODELS) * len(CAUSAL_ARMS):
        problems.append("batch geometry cannot hold one model's arms")
    if set(pin_document("sha256:x", "rev", CAUSAL_MODELS)) != set(memory_contract.PIN_FIELDS):
        problems.append("pins do not cover every contract pin field")
    if CAUSAL_GRADER != "memory_scenario.grade":
        problems.append("grader literal drifted")
    if not memory_pilot.SYSTEM_PROMPT.strip():
        problems.append("the shared child system prompt is empty")
    return problems


_USAGE = (
    "usage: braintree benchmark causal plan [--split development|held-out]\n"
    "       braintree benchmark causal dry-run [--split development|held-out]\n"
    "       braintree benchmark causal record --input RAW.json [--output RESULT.json]\n"
    "Plan, dry-run, or record the matched five-arm causal memory experiment."
)


def _print_plan(plan: Mapping[str, Any]) -> None:
    print(field("protocol", plan["protocol"]))
    print(field("harness", plan["harness"]))
    print(field("child_profile", plan["child_profile"]))
    print(field("models", ",".join(plan["models"])))
    print(field("reasoning_effort", plan["reasoning_effort"]))
    print(field("split", plan["split"]))
    print(field("corpus_digest", plan["corpus_digest"]))
    print(field("plan_digest", plan["plan_digest"]))
    print(field("cases", plan["case_count"]))
    print(field("arms", plan["arm_count"]))
    print(field("samples", plan["sample_count"]))
    print(field("batches", plan["batch_count"]))
    print(
        table(
            "arms",
            "arm,isolates",
            (
                (arm.id, arm.isolates)
                for arm in memory_contract.ARMS
            ),
        )
    )


def _read_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CausalError(f"cannot read JSON {path}: {error}") from error


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
        raise CausalError(f"unknown argument: {name}")
    if input_path is None:
        raise CausalError("record requires --input")
    document = _read_json(input_path)
    if not isinstance(document, Mapping):
        raise CausalError("record input must be a JSON object")
    samples = document.get("samples")
    if not isinstance(samples, list):
        raise CausalError("record input must carry a samples list")
    result = record(plan_document(), samples, out_path=output_path or "")
    problems = result_problems(result)
    if problems:
        raise CausalError("; ".join(problems))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if output_path is None:
        print(rendered, end="")
    else:
        Path(output_path).write_text(rendered, encoding="utf-8")
    return 0


def _split_argument(arguments: Sequence[str]) -> str:
    """Return the ``--split`` value, defaulting to the development split."""
    values = list(arguments)
    split = "development"
    index = 0
    while index < len(values):
        name = values[index]
        if name == "--split" and index + 1 < len(values):
            split = values[index + 1]
            index += 2
            continue
        raise CausalError(f"unknown argument: {name}")
    if split not in CAUSAL_SPLIT_PROTOCOLS:
        raise CausalError(f"unknown split: {split}")
    return split


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``plan``, ``dry-run``, or ``record`` for the five-arm causal runner."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0 if arguments else 2
    command = arguments[0]
    try:
        if command in {"plan", "dry-run"}:
            split = _split_argument(arguments[1:])
            if command == "plan":
                _print_plan(plan_document(split=split))
                return 0
            result = dry_run(split=split)
            print(field("protocol", result["protocol"]))
            print(field("split", result["split"]))
            print(field("status", result["status"]))
            print(field("evidence", result["evidence"]))
            print(field("decision", result["decision"]))
            print(field("samples", result["sample_count"]))
            print("dry-run: passed")
            return 0
        if command == "record":
            return _record_cli(arguments[1:])
        print(f"error: unknown causal command: {command}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2
    except CausalError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
