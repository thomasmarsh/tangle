"""Opt-in Codex token benchmark.

Typed Python port of the historical ``token-benchmark`` harness. The measured
work is a fresh generated repository, never this checkout. Only usage telemetry
is read from sessions. Every option surface, output line, fixture, and
correctness gate is preserved so the tracked baselines and the zero-live-call
recording checks keep working.

The report also names round trips alongside tokens: the tool-call and
shell-invocation counts the session stream exposes. Fewer round trips is the
goal the direct-answer verbs serve, so a session that exposes no tool-call event
reports the documented fallback instead of a fabricated zero.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["main"]

FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
MAX_REPETITIONS = 3
FIXTURE_VERSION = "graph-retrieval-v3"
FIXTURE_SEED = "tas-020-2026-09-10"
SCALES = {"small": 32, "large": 320}
REPRESENTATIONS = ("graph", "plan")
MUTATION_ANSWER = "Routine mutation complete."
# A Codex session records each model tool call as a ``response_item`` whose
# payload type is a tool-call kind; ``payload.name`` names the executable tool,
# and the ``exec`` tool runs a shell command. Only these observed kinds count as
# a round trip, and a stream that exposes none reports the fallback below.
_TOOL_CALL_TYPES = frozenset(
    {
        "custom_tool_call",
        "function_call",
        "local_shell_call",
        "computer_call",
        "web_search_call",
    }
)
_SHELL_TOOL_NAMES = frozenset({"exec", "shell", "local_shell", "bash", "terminal"})
ROUND_TRIP_FALLBACK = "session stream exposes no tool-call events"
_ACTIVE_NODE = "nodes/active/TAS-201-validate-schema.md"
_RESOLVED_NODE = "nodes/resolved/TAS-201-validate-schema.md"
_UPDATED_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

Json = dict[str, Any]


class _BenchError(Exception):
    """An argument, fixture, or session error that maps to exit code 2."""


class _TimeoutError(Exception):
    """A live Codex session exceeded its bounded timeout."""


@dataclass(frozen=True)
class _Case:
    expected: Json
    fixture_version: str


CASES: dict[str, _Case] = {
    "composite": _Case(
        expected={
            "frontier": "TAS-041",
            "current_decision": "DEC-031",
            "stale_dependents": ["TAS-052", "TAS-053"],
            "orphan": "TAS-060",
        },
        fixture_version="graph-retrieval-v3",
    ),
    "cold-resume": _Case(
        expected={
            "frontier": "TAS-101",
            "next": "Apply the reversible schema migration.",
        },
        fixture_version="cold-resume-frontier-v1",
    ),
    "routine-mutation": _Case(expected={}, fixture_version="routine-mutation-status-v1"),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


# The frozen install snapshots make a committed sample reproducible from the
# revision it was recorded at. ``current`` is a frozen byte copy of revision
# 726cb43, not a view of the live tree: a frozen snapshot never tracks live
# source, so refresh it deliberately with a re-record when the measured
# installed bytes change.
_SNAPSHOT_ROOT = "research/fixtures/token-install"
_DEFAULT_SNAPSHOT = "current"


def _snapshots() -> Json:
    with open(_repo_root() / _SNAPSHOT_ROOT / "manifest.json", "rb") as handle:
        value = json.loads(handle.read())
    if not isinstance(value, dict):
        raise _BenchError("install snapshot manifest is not a JSON object")
    return value


def _snapshot(key: str = _DEFAULT_SNAPSHOT) -> Json:
    snapshots = _snapshots().get("snapshots")
    if not isinstance(snapshots, list):
        raise _BenchError("install snapshot manifest has no snapshot list")
    for entry in snapshots:
        if isinstance(entry, dict) and entry.get("key") == key:
            return entry
    raise _BenchError(f"unknown install snapshot {key!r}")


def _installed_skill_files(snapshot_key: str = _DEFAULT_SNAPSHOT) -> dict[str, bytes]:
    """Map installed-skill relative paths to their frozen snapshot bytes.

    The installed skill is a ``uv`` project, so a fixture copy mirrors the
    installer's distributable tree exactly. The bytes come from
    ``research/fixtures/token-install/<snapshot_key>`` rather than the live
    checkout, so a committed sample reproduces from its recording revision.
    """
    root = _repo_root() / _SNAPSHOT_ROOT / snapshot_key
    return {
        record["path"]: (root / record["path"]).read_bytes()
        for record in _snapshot(snapshot_key)["files"]
    }


def _run_graph_check(nodes_dir: str, *graph_args: str) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "tangle.graph_check", *graph_args, nodes_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode


def _write(path: str, data: str | bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = data.encode("utf-8") if isinstance(data, str) else data
    with open(path, "wb") as handle:
        handle.write(payload)


def _node(
    *,
    summary: str,
    extra: str = "",
    next_action: str | None = None,
    area: str | None = "IDX-001-import",
) -> str:
    header = [
        "---",
        "context_rev: 1",
        "updated: 2026-01-01T00:00:00Z",
        f"summary: {summary}",
    ]
    if next_action is not None:
        header.append(f"next: {next_action}")
    header.append("---")
    parts = ["\n".join(header)]
    if area is not None:
        parts.append(f"Area [[{area}]].")
    if extra:
        parts.append(extra)
    return "\n".join(parts) + "\n"


def _output_schema(expected: Json) -> Json:
    properties: Json = {
        "frontier": {"type": "string"},
        "current_decision": {"type": "string"},
        "stale_dependents": {"type": "array", "items": {"type": "string"}},
        "orphan": {"type": "string"},
        "next": {"type": "string"},
    }
    selected = {key: properties[key] for key in expected}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(expected),
        "properties": selected,
    }


def _compact(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _pretty(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _parse_lines(text: str) -> list[str]:
    return text.splitlines()


def _load_event(line: str) -> Json:
    value = json.loads(line)
    if not isinstance(value, dict):
        raise _BenchError("session event is not a JSON object")
    return value


def _completed_answer(stream: str, answer_path: str, expected: Json) -> None:
    lines = _parse_lines(stream)
    # Codex CLI 0.154.0 emitted this exact progress line before its --json
    # stream in the final cold-resume invocations. It is the sole tolerated
    # non-event line; every remaining line is parsed strictly below.
    if lines and lines[0] == "Reading":
        lines.pop(0)
    completed = any(_load_event(line).get("type") == "turn.completed" for line in lines)
    if not completed:
        raise _BenchError("live Codex stream ended without turn.completed")
    if not os.path.isfile(answer_path):
        raise _BenchError("live Codex stream completed without an answer artifact")
    with open(answer_path, "rb") as handle:
        answer = json.loads(handle.read())
    if answer != expected:
        raise _BenchError("fixture correctness gate failed")


def _completed_mutation(stream: str, answer_path: str, root: str, before: dict[str, bytes]) -> None:
    lines = _parse_lines(stream)
    if lines and lines[0] == "Reading":
        lines.pop(0)
    completed = any(_load_event(line).get("type") == "turn.completed" for line in lines)
    if not completed:
        raise _BenchError("live Codex stream ended without turn.completed")
    if not os.path.isfile(answer_path):
        raise _BenchError("live Codex stream completed without an exact answer artifact")
    with open(answer_path, "rb") as handle:
        answer_text = handle.read().decode("utf-8").strip()
    if answer_text != MUTATION_ANSWER:
        raise _BenchError("live Codex stream completed without an exact answer artifact")

    after = {
        os.path.relpath(path, root): Path(path).read_bytes()
        for path in _fixture_files(root)
        if path != answer_path
    }
    expected_paths = [key for key in before if key != _ACTIVE_NODE] + [_RESOLVED_NODE]
    if sorted(after) != sorted(expected_paths):
        raise _BenchError("mutation changed an unexpected fixture path")
    for path in before:
        if path == _ACTIVE_NODE:
            continue
        if after[path] != before[path]:
            raise _BenchError(f"mutation changed unrelated fixture content: {path}")
    node = after[_RESOLVED_NODE].decode("utf-8")
    if re.search(r"^context_rev: 4$", node, re.MULTILINE) is None:
        raise _BenchError("mutation did not set the required semantic revision")
    updated_match = re.search(r"^updated: ([^\n]+)$", node, re.MULTILINE)
    updated = updated_match.group(1) if updated_match else None
    if updated is None or _UPDATED_STAMP.fullmatch(updated) is None:
        raise _BenchError("mutation timestamp is not a newer UTC ISO-8601 value")
    if datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ") <= datetime(2026, 1, 1):
        raise _BenchError("mutation timestamp is not a newer UTC ISO-8601 value")
    if re.search(r"^summary: Schema validation is complete\.$", node, re.MULTILINE) is None:
        raise _BenchError("mutation did not apply the requested summary")
    if re.search(r"^next:", node, re.MULTILINE):
        raise _BenchError("resolved mutation retained next")
    if "Area [[IDX-001-import]]." not in node:
        raise _BenchError("mutation did not preserve its area link")
    if "Depends on [[DEF-020-import-contract]] at context_rev 4." not in node:
        raise _BenchError("mutation did not preserve its dependency pin")
    if "# Result\n\nValidated the signed schema contract.\n" not in node:
        raise _BenchError("mutation did not record exact completion evidence")
    if _run_graph_check(os.path.join(root, "nodes")) != 0:
        raise _BenchError("mutated graph is invalid")


def _fixture_prompt(
    representation: str, benchmark_case: str, install_root: str, prompt_verb: str
) -> str:
    skill_path = f"{install_root}/SKILL.md"
    verb = f"${prompt_verb}"
    if benchmark_case == "routine-mutation":
        return (
            "Complete one routine Markdown execution-graph mutation. First explicitly "
            f"invoke {verb} and follow {skill_path}.\n"
            "\n"
            "The signed-schema validation task is complete. Move its existing node to "
            "resolved and make only the necessary node mutation: set its summary exactly "
            'to "Schema validation is complete.", record exactly "Validated the signed '
            'schema contract." under # Result, refresh updated to the current UTC ISO-8601 '
            "time, and apply the correct semantic context revision behavior. Preserve its "
            "Area and dependency pin. Do not modify any other fixture file. Respond exactly: "
            "Routine mutation complete.\n"
        )
    if benchmark_case == "cold-resume":
        return (
            "You are resuming a cold engineering session. Inspect this repository's "
            "Markdown execution graph; do not guess from filenames alone.\n"
            "\n"
            "First explicitly invoke "
            f"{verb} and follow the project skill at "
            f"{skill_path} before inspecting the graph.\n"
            "\n"
            "Return exactly one compact JSON object with these keys and no others:\n"
            '{"frontier":"ID","next":"exact next action"}\n'
            "\n"
            "`frontier` is the one currently executable active task deliberately selected "
            "by the index's Focus route. Exclude resolved history, blocked work, proposed "
            "work, and active work not selected by Focus. `next` is that task's exact "
            "frontmatter next action. Do not edit files.\n"
        )
    control = (
        "Markdown execution graph"
        if representation == "graph"
        else "conventional plan documents"
    )
    instruction = (
        "First explicitly invoke "
        f"{verb} and follow the project skill at "
        f"{skill_path} before inspecting the graph."
        if representation == "graph"
        else "Use the conventional plan as the control representation; it expresses "
        "the same current work facts and historical distractors but does not supply "
        "graph-skill instructions."
    )
    return (
        "You have been asked to resume the active data-import hardening work. "
        f"Inspect this repository's {control}; do not guess from filenames alone.\n"
        "\n"
        f"{instruction}\n"
        "\n"
        "Return exactly one compact JSON object with these keys and no others:\n"
        '{"frontier":"ID","current_decision":"ID","stale_dependents":["ID"],'
        '"orphan":"ID"}\n'
        "\n"
        "`frontier` is the currently executable active task selected by the active "
        "coordinator's next route. `current_decision` is the decision that remains in "
        "force, not a superseded decision. `stale_dependents` contains every task whose "
        "pinned dependency revision is older than the definition's current revision, "
        "sorted lexicographically. `orphan` is the unfinished actionable task with no "
        "primary route to any root hub. Do not edit files.\n"
    )


def _fixture_files(root: str) -> list[str]:
    files: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            relative = os.path.relpath(path, root)
            if relative == ".git" or relative.startswith(".git" + os.sep):
                continue
            files.append(path)
    files.sort()
    return files


def _fixture_hash(root: str) -> str:
    digest = hashlib.sha256()
    for path in _fixture_files(root):
        relative = os.path.relpath(path, root)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def _generate_fixture(
    root: str,
    representation: str,
    scale: str,
    benchmark_case: str,
    snapshot_key: str = _DEFAULT_SNAPSHOT,
) -> Json:
    case = CASES[benchmark_case]
    expected = case.expected
    count = SCALES[scale]
    snapshot = _snapshot(snapshot_key)
    _output, success = _capture_merged(["git", "init", "-q", root])
    if not success:
        raise _BenchError("could not initialize isolated fixture repository")
    _write(os.path.join(root, ".gitignore"), "*\n!.gitignore\n")
    if representation == "graph":
        skill_root = os.path.join(root, snapshot["install_root"])
        for relative, data in _installed_skill_files(snapshot_key).items():
            _write(os.path.join(skill_root, relative), data)
        if benchmark_case == "routine-mutation":
            _write(
                os.path.join(root, "nodes/index-map.md"),
                "# Routes\n\n- Indexes [[IDX-001-import]]\n",
            )
            _write(
                os.path.join(root, "nodes/resolved/IDX-001-import.md"),
                "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\n"
                "summary: Data import hardening area.\n---\n",
            )
            definition = _node(
                summary="Signed schema contract.",
                extra="# Invariant\n\nSigned schemas are required.",
            ).replace("context_rev: 1", "context_rev: 4", 1)
            _write(os.path.join(root, "nodes/resolved/DEF-020-import-contract.md"), definition)
            task = _node(
                summary="Validate the signed schema contract.",
                next_action="Run signed schema validation.",
                extra="Depends on [[DEF-020-import-contract]] at context_rev 4.",
            ).replace("context_rev: 1", "context_rev: 3", 1)
            _write(os.path.join(root, "nodes/active/TAS-201-validate-schema.md"), task)
        elif benchmark_case == "cold-resume":
            _write(
                os.path.join(root, "nodes/index-map.md"),
                "# Focus\n\n- [[TAS-101-apply-schema-migration]]\n\n"
                "# Routes\n\n- Indexes [[IDX-001-import]]\n",
            )
            _write(
                os.path.join(root, "nodes/resolved/IDX-001-import.md"),
                "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\n"
                "summary: Data import hardening area.\n---\n",
            )
            _write(
                os.path.join(root, "nodes/active/TAS-101-apply-schema-migration.md"),
                _node(
                    summary="Apply the resumable schema migration.",
                    next_action="Apply the reversible schema migration.",
                ),
            )
            _write(
                os.path.join(root, "nodes/blocked/TAS-102-vendor-access.md"),
                _node(
                    summary="Wait for vendor credentials.",
                    next_action="Request vendor credentials.",
                    extra="# Blocked\n\nBlocked by missing vendor credentials. "
                    "Unblocks when the vendor issues credentials.",
                ),
            )
            _write(
                os.path.join(root, "nodes/proposed/TAS-103-follow-up-cleanup.md"),
                _node(
                    summary="Plan post-migration cleanup.",
                    next_action="Draft the cleanup plan.",
                ),
            )
            _write(
                os.path.join(root, "nodes/active/TAS-104-unselected-investigation.md"),
                _node(
                    summary="Investigate an unrelated warning.",
                    next_action="Inspect unrelated warning logs.",
                ),
            )
            for index in range(count):
                node_id = f"TAS-{200 + index:03d}"
                _write(
                    os.path.join(root, f"nodes/resolved/{node_id}-historical.md"),
                    _node(summary=f"Resolved historical import item {index}."),
                )
        else:
            _write(
                os.path.join(root, "nodes/index-map.md"),
                "# Routes\n\n- Indexes [[IDX-001-import]]\n",
            )
            _write(
                os.path.join(root, "nodes/resolved/IDX-001-import.md"),
                "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\n"
                "summary: Data import hardening area.\n---\n",
            )
            definition = _node(
                summary="Import contract now rejects unsigned manifests.",
                extra="# Invariant\n\nRevision 4 requires signed manifests.",
            ).replace("context_rev: 1", "context_rev: 4", 1)
            _write(os.path.join(root, "nodes/resolved/DEF-020-import-contract.md"), definition)
            old_decision = _node(
                summary="Use the legacy routing branch.",
                extra="Superseded by [[DEC-031-current-routing]].",
            ).replace(
                "updated: 2026-01-01T00:00:00Z",
                "updated: 2026-01-01T00:00:00Z\ndisposition: superseded",
                1,
            )
            _write(os.path.join(root, "nodes/resolved/DEC-030-old-routing.md"), old_decision)
            _write(
                os.path.join(root, "nodes/resolved/DEC-031-current-routing.md"),
                _node(
                    summary="Use manifest-first routing.",
                    extra="# Decision\n\nManifest-first routing is current.",
                ),
            )
            _write(
                os.path.join(root, "nodes/active/TAS-040-import-coordinator.md"),
                _node(
                    summary="Coordinate data-import hardening.",
                    next_action='"[[TAS-041-validate-manifests]]"',
                ),
            )
            _write(
                os.path.join(root, "nodes/active/TAS-041-validate-manifests.md"),
                _node(
                    summary="Validate signed manifests.",
                    next_action="Run the signed-manifest validation.",
                    area=None,
                    extra="Parent [[TAS-040-import-coordinator]].",
                ),
            )
            for number in ("052", "053"):
                _write(
                    os.path.join(root, f"nodes/active/TAS-{number}-stale-consumer.md"),
                    _node(
                        summary="Reconcile import contract consumer.",
                        next_action="Reconcile the pinned import-contract revision.",
                        extra="Depends on [[DEF-020-import-contract]] at context_rev 3.",
                    ),
                )
            _write(
                os.path.join(root, "nodes/active/TAS-060-unrouted-cleanup.md"),
                "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-01-01T00:00:00Z\n"
                "summary: Remove obsolete import staging files.\n"
                "next: Delete obsolete staging files.\n---\n",
            )
            for index in range(count):
                node_id = f"TAS-{100 + index:03d}"
                _write(
                    os.path.join(root, f"nodes/resolved/{node_id}-historical.md"),
                    _node(summary=f"Historical import note {index}."),
                )
    else:
        if benchmark_case == "cold-resume":
            raise _BenchError("cold-resume benchmark has no plan representation")
        text = (
            "# Data import hardening plan\n\n"
            "## Current work\n\n"
            "TAS-040 is the coordinator; its one active execution frontier is TAS-041.\n"
            "DEC-031 is the current routing decision; DEC-030 is superseded.\n"
            "DEF-020 is revision 4; TAS-052 and TAS-053 remain pinned to revision 3.\n"
            "TAS-060 is the one actionable unfinished cleanup task not routed to the "
            "import area hub.\n\n"
            "## Historical completed items\n"
        )
        for index in range(count):
            text += f"Historical completed item TAS-{100 + index:03d}.\n"
        _write(os.path.join(root, "plans/data-import.md"), text)
    _write(
        os.path.join(root, "TASK.txt"),
        _fixture_prompt(
            representation, benchmark_case, snapshot["install_root"], snapshot["prompt_verb"]
        ),
    )
    if benchmark_case != "routine-mutation":
        _write(os.path.join(root, "answer.schema.json"), _pretty(_output_schema(expected)) + "\n")
    metadata: Json = {
        "benchmark_case": benchmark_case,
        "fixture_version": case.fixture_version,
        "fixture_seed": FIXTURE_SEED,
        "fixture_sha256": _fixture_hash(root),
    }
    if representation == "graph":
        metadata["skill_sha256"] = snapshot["skill_sha256"]
    return metadata


def _usage_hash(value: object) -> Json | None:
    if not isinstance(value, dict):
        return None
    normalized = {str(key): item for key, item in value.items()}
    for key in FIELDS:
        item = normalized.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            return None
    result = {key: int(normalized[key]) for key in FIELDS}
    uncached = result["input_tokens"] - result["cached_input_tokens"]
    if uncached < 0:
        raise _BenchError("cached input tokens exceed input tokens")
    if result["total_tokens"] != result["input_tokens"] + result["output_tokens"]:
        raise _BenchError("total tokens is not input plus output")
    result["uncached_input_tokens"] = uncached
    return result


def _turn_id(payload: Json) -> str:
    turn_id = payload.get("turn_id")
    if not isinstance(turn_id, str) or not turn_id.strip():
        raise _BenchError("token_usage_record lacks payload.turn_id")
    return turn_id


def _cumulative_snapshot(previous: Json, current: Json, turn_id: str) -> None:
    for field in FIELDS:
        if current[field] < previous[field]:
            raise _BenchError(f"turn {turn_id!r} token usage regresses {field}")


def _has_turn_usage(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if "turn_token_usage" not in line:
                    continue
                try:
                    event = _load_event(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload")
                if (
                    event.get("type") == "token_usage_record"
                    and isinstance(payload, dict)
                    and "turn_token_usage" in payload
                ):
                    return True
    except OSError:
        return False
    return False


def _wait_for_session_usage(
    path: str, timeout_seconds: float = 15.0, quiet_seconds: float = 1.0
) -> None:
    """Wait for a fresh Codex session to finish flushing its usage records.

    ``codex exec`` can return before its session JSONL is fully written, which
    previously aborted a valid run with "no token_usage_record". Poll until the
    file has been stable for ``quiet_seconds`` and contains turn usage.
    """
    deadline = time.monotonic() + timeout_seconds
    last_size = -1
    last_change = time.monotonic()
    while time.monotonic() < deadline:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1
        now = time.monotonic()
        if size != last_size:
            last_size = size
            last_change = now
        elif now - last_change >= quiet_seconds and _has_turn_usage(path):
            return
        time.sleep(0.1)
    if not _has_turn_usage(path):
        raise _BenchError(f"no token_usage_record.turn_token_usage in {path}")


def _session_usage(path: str) -> list[Json]:
    final_snapshots: dict[str, Json] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            event = _load_event(line)
            payload = event.get("payload")
            if event.get("type") != "token_usage_record" or not isinstance(payload, dict):
                continue
            if "turn_token_usage" not in payload:
                continue
            usage = _usage_hash(payload["turn_token_usage"])
            if usage is None:
                raise _BenchError("token_usage_record has malformed turn_token_usage")
            turn_id = _turn_id(payload)
            previous = final_snapshots.get(turn_id)
            if previous is not None:
                _cumulative_snapshot(previous, usage, turn_id)
            # Codex emits cumulative snapshots for a turn. Keep its last valid
            # record; different turn IDs are independently additive.
            final_snapshots[turn_id] = usage
    if not final_snapshots:
        raise _BenchError(f"no token_usage_record.turn_token_usage in {path}")
    return list(final_snapshots.values())


def _session_round_trips(path: str) -> Json | None:
    """Count the tool calls and shell invocations the session stream exposes.

    A Codex session records each model tool call as a ``response_item`` whose
    payload type is one of :data:`_TOOL_CALL_TYPES`; ``payload.name`` names the
    executable tool and ``exec`` runs a shell command. A session that exposes no
    tool-call event cannot report round trips, so it returns ``None`` for the
    caller to report as :data:`ROUND_TRIP_FALLBACK` rather than a fake zero.
    """
    tool_calls = 0
    shell_calls = 0
    exposed = False
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            event = _load_event(line)
            if event.get("type") != "response_item":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            kind = payload.get("type")
            if not isinstance(kind, str) or kind not in _TOOL_CALL_TYPES:
                continue
            exposed = True
            tool_calls += 1
            if kind == "local_shell_call" or payload.get("name") in _SHELL_TOOL_NAMES:
                shell_calls += 1
    if not exposed:
        return None
    return {"tool_calls": tool_calls, "shell_calls": shell_calls}


def _graph_fixture_facts(root: str) -> Json:
    definition = Path(root, "nodes/resolved/DEF-020-import-contract.md").read_text(encoding="utf-8")
    match = re.search(r"^context_rev: (\d+)$", definition, re.MULTILINE)
    if match is None:
        raise _BenchError("graph fixture definition has no context_rev")
    revision = int(match.group(1))
    stale: list[str] = []
    for path in glob.glob(os.path.join(root, "nodes", "*", "*.md")):
        text = Path(path).read_text(encoding="utf-8")
        pin = re.search(r"Depends on \[\[DEF-020-import-contract\]\] at context_rev (\d+)\.", text)
        if pin and int(pin.group(1)) < revision:
            name = os.path.basename(path)[:-3]
            id_match = re.match(r"TAS-\d+", name)
            if id_match:
                stale.append(id_match.group(0))
    return {"stale_dependents": sorted(stale)}


def _session_shapes(path: str) -> dict[str, int]:
    shapes: dict[str, int] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            event = _load_event(line)
            payload = event.get("payload")
            if event.get("type") != "token_usage_record" or not isinstance(payload, dict):
                continue
            shape = ",".join(sorted(str(key) for key in payload))
            shapes[shape] = shapes.get(shape, 0) + 1
    if not shapes:
        raise _BenchError(f"no token_usage_record in {path}")
    return shapes


def _scalar_values(events: list[Json], event_type: str, field: str) -> list[str]:
    values: list[str] = []
    for event in events:
        payload = event.get("payload")
        if event.get("type") != event_type or not isinstance(payload, dict):
            continue
        value = payload.get(field)
        if value is None:
            continue
        text = str(value)
        if text not in values:
            values.append(text)
    return values


def _session_observations(path: str) -> Json:
    events: list[Json] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                events.append(_load_event(stripped))
            except json.JSONDecodeError:
                # A live session JSONL can be observed while still being written.
                continue
    return {
        "observed_agent_path": _scalar_values(events, "session_meta", "agent_path"),
        "observed_cli_version": _scalar_values(events, "session_meta", "cli_version"),
        "observed_session_cwd": _scalar_values(events, "session_meta", "cwd"),
        "observed_turn_cwd": _scalar_values(events, "turn_context", "cwd"),
        "observed_model": _scalar_values(events, "turn_context", "model"),
        "observed_reasoning_effort": _scalar_values(events, "turn_context", "effort"),
        "token_usage_payload_shapes": _session_shapes(path),
    }


def _exactly_one_observation(observed: Json, field: str) -> str:
    values = observed.get(field)
    if not isinstance(values, list) or not values:
        raise _BenchError(f"session telemetry lacks {field}")
    if len(values) != 1:
        raise _BenchError(f"session telemetry has ambiguous {field}")
    return str(values[0])


def _historical_session_provenance(path: str, expected: Json) -> Json:
    observed = _session_observations(path)
    provenance: Json = {
        "task_path": _exactly_one_observation(observed, "observed_agent_path"),
        "cli_version": _exactly_one_observation(observed, "observed_cli_version"),
        "model": _exactly_one_observation(observed, "observed_model"),
        "reasoning_effort": _exactly_one_observation(observed, "observed_reasoning_effort"),
    }
    field_map = {
        "model": "model",
        "effort": "reasoning_effort",
        "task_path": "task_path",
    }
    for option, field in field_map.items():
        requested = expected.get(option)
        if requested is None:
            continue
        if provenance[field] != requested:
            raise _BenchError(f"session telemetry {field} mismatch")
    return provenance


def _assert_live_observations(
    path: str, requested: Json, fixture_dir: str, cli_version: str
) -> Json:
    observed = _session_observations(path)
    required = {
        "observed_cli_version": [re.sub(r"^codex-cli\s+", "", cli_version)],
        "observed_session_cwd": [fixture_dir],
        "observed_turn_cwd": [fixture_dir],
        "observed_model": [requested["model"]],
        "observed_reasoning_effort": [requested["effort"]],
    }
    for field, expected in required.items():
        actual = observed.get(field)
        if not isinstance(actual, list) or not actual:
            raise _BenchError(f"session telemetry lacks {field}")
        if actual != expected:
            raise _BenchError(f"session telemetry {field} mismatch")
    return observed


def _totals(usages: list[Json]) -> Json:
    fields = list(FIELDS) + ["uncached_input_tokens"]
    return {field: sum(usage[field] for usage in usages) for field in fields}


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _emit_record(
    runs: list[list[Json]],
    round_trips: list[Json | None],
    metadata: Json,
    output_path: str | None,
) -> None:
    sample_totals = [_totals(run) for run in runs]
    fields = list(FIELDS) + ["uncached_input_tokens"]
    medians = {field: _median([run[field] for run in sample_totals]) for field in fields}
    exposed = [trip for trip in round_trips if trip is not None]
    if exposed:
        median: Json = {
            "tool_calls": _median([trip["tool_calls"] for trip in exposed]),
            "shell_calls": _median([trip["shell_calls"] for trip in exposed]),
        }
        round_trip_median: Json | None = median
        round_trip_summary = f"{median['tool_calls']},{median['shell_calls']}"
    else:
        round_trip_median = None
        round_trip_summary = "n/a,n/a"
    record = {
        "protocol": "codex-session-token-v2",
        "correctness": True,
        "samples": sample_totals,
        "median": medians,
        "round_trips": {
            "samples": round_trips,
            "median": round_trip_median,
            "fallback": None if exposed else ROUND_TRIP_FALLBACK,
        },
        "metadata": metadata,
    }
    print(
        "token_benchmark"
        "{runs,input_tokens,cached_input_tokens,uncached_input_tokens,output_tokens,"
        "reasoning_output_tokens,total_tokens,correct,tool_calls,shell_calls}: "
        f"{len(runs)},{medians['input_tokens']},{medians['cached_input_tokens']},"
        f"{medians['uncached_input_tokens']},{medians['output_tokens']},"
        f"{medians['reasoning_output_tokens']},{medians['total_tokens']},true,"
        f"{round_trip_summary}"
    )
    print(_compact(record))
    if output_path:
        _write(output_path, _pretty(record) + "\n")


def _emit_historical_accounting(runs: list[list[Json]], provenance: list[Json]) -> None:
    samples = [_totals(run) for run in runs]
    fields = list(FIELDS) + ["uncached_input_tokens"]
    aggregate = {field: sum(sample[field] for sample in samples) for field in fields}
    record = {
        "protocol": "codex-session-token-v2",
        "classification": "historical-implementation-cost",
        "samples": samples,
        "aggregate": aggregate,
        "provenance": provenance,
    }
    print(
        "historical_token_accounting"
        "{sessions,input_tokens,cached_input_tokens,uncached_input_tokens,output_tokens,"
        "reasoning_output_tokens,total_tokens}: "
        f"{len(samples)},{aggregate['input_tokens']},{aggregate['cached_input_tokens']},"
        f"{aggregate['uncached_input_tokens']},{aggregate['output_tokens']},"
        f"{aggregate['reasoning_output_tokens']},{aggregate['total_tokens']}"
    )
    print(_compact(record))


def _protocol() -> None:
    print("token_benchmark{status,live_calls,baseline}: ready,0,absent")
    print(
        "round trips: reports tool_calls and shell_calls from session tool-call "
        "events, or n/a when the stream exposes none"
    )
    print(
        "record: tangle benchmark token --record --model MODEL "
        "--reasoning-effort low --representation graph --scale small "
        "--repetitions 3 --output benchmark/token-baseline.json"
    )
    print(
        "control: tangle benchmark token --record --model MODEL "
        "--reasoning-effort low --representation plan --scale small "
        "--repetitions 3 --output benchmark/token-plan-control.json"
    )
    print(
        "historical accounting: tangle benchmark token --session PATH "
        "[--task-path /root/task]"
    )


def _session_root() -> str:
    configured = os.environ.get("TANGLE_TOKEN_BENCHMARK_SESSIONS_DIR", "~/.codex/sessions")
    return os.path.abspath(os.path.expanduser(configured))


def _codex_command() -> str:
    return os.environ.get("TANGLE_TOKEN_BENCHMARK_CODEX", "codex")


def _capture_merged(command: Sequence[str], timeout: int | None = None) -> tuple[str, bool]:
    try:
        result = subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise _TimeoutError("execution expired") from error
    return result.stdout or "", result.returncode == 0


def _newest_session(before: Sequence[str], fixture_dir: str) -> str:
    candidates = [
        path
        for path in glob.glob(os.path.join(_session_root(), "**", "*.jsonl"), recursive=True)
        if path not in before
    ]
    matching = [
        path
        for path in candidates
        if fixture_dir in _session_observations(path).get("observed_session_cwd", [])
    ]
    if len(matching) != 1:
        raise _BenchError("Codex did not create exactly one fresh fixture session")
    return matching[0]


def _check_fixture(benchmark_case: str, snapshot_key: str = _DEFAULT_SNAPSHOT) -> int:
    representations = (
        ["graph"]
        if benchmark_case in {"cold-resume", "routine-mutation"}
        else list(REPRESENTATIONS)
    )
    expected = CASES[benchmark_case].expected
    snapshot = _snapshot(snapshot_key)
    installed = _installed_skill_files(snapshot_key)
    variants: list[Json] = []
    for representation in representations:
        for scale in SCALES:
            with tempfile.TemporaryDirectory(prefix="tangle-token-fixture-") as directory:
                metadata = _generate_fixture(
                    directory, representation, scale, benchmark_case, snapshot_key
                )
                task_text = Path(directory, "TASK.txt").read_text(encoding="utf-8")
                if expected and any(
                    isinstance(value, str) and value in task_text
                    for value in _flatten(expected.values())
                ):
                    raise _BenchError("fixture prompt leaks expected answer")
                if representation == "graph":
                    graph_args = (
                        ["--allow-stale", "--allow-orphan", "TAS-060-unrouted-cleanup"]
                        if benchmark_case == "composite"
                        else []
                    )
                    if _run_graph_check(os.path.join(directory, "nodes"), *graph_args) != 0:
                        raise _BenchError("graph fixture structural check failed")
                    copy_root = os.path.join(directory, snapshot["install_root"])
                    skill_bytes = installed.get("SKILL.md")
                    if skill_bytes is None or (
                        Path(copy_root, "SKILL.md").read_bytes() != skill_bytes
                    ):
                        raise _BenchError(
                            "graph fixture does not copy the exact repository skill"
                        )
                    metadata_bytes = installed.get("agents/openai.yaml")
                    if metadata_bytes is None or (
                        Path(copy_root, "agents/openai.yaml").read_bytes() != metadata_bytes
                    ):
                        raise _BenchError(
                            "graph fixture does not install the exact skill metadata"
                        )
                    for relative, data in installed.items():
                        if Path(copy_root, relative).read_bytes() != data:
                            raise _BenchError(
                                "graph fixture does not copy the exact installed file: "
                                f"{relative}"
                            )
                    if "stale_dependents" in expected:
                        facts = _graph_fixture_facts(directory)
                        if facts["stale_dependents"] != expected["stale_dependents"]:
                            raise _BenchError(
                                "graph fixture has unexpected stale dependencies"
                            )
                files = len(_fixture_files(directory))
                variants.append(
                    {
                        "representation": representation,
                        "scale": scale,
                        "files": files,
                        **metadata,
                    }
                )
    print(
        _compact(
            {
                "protocol": "codex-session-token-v2",
                "fixture_variants": variants,
            }
        )
    )
    return 0


def _flatten(values: object) -> list[object]:
    if isinstance(values, dict):
        return _flatten(list(values.values()))
    if isinstance(values, (list, tuple)):
        flat: list[object] = []
        for value in values:
            flat.extend(_flatten(value))
        return flat
    return [values]


def _inspect_session(path: str) -> int:
    with open(path, encoding="utf-8") as handle:
        events = [_load_event(line) for line in handle]
    safe_shapes: Json = {}
    for event_type in ("session_meta", "turn_context"):
        fields: list[str] = []
        for event in events:
            payload = event.get("payload")
            if event.get("type") != event_type or not isinstance(payload, dict):
                continue
            for key in payload:
                text = str(key)
                if text not in fields:
                    fields.append(text)
        safe_shapes[event_type] = sorted(fields)
    print(
        _compact(
            {
                "token_usage_record_payload_shapes": _session_shapes(path),
                "session_telemetry_fields": safe_shapes,
            }
        )
    )
    return 0


def _run_record(options: argparse.Namespace) -> int:
    if options.task_path:
        raise _BenchError("--task-path is only valid with --session")
    if not options.model or not options.reasoning_effort:
        raise _BenchError("--model and --reasoning-effort are required with --record")
    version_result = subprocess.run(
        [_codex_command(), "--version"],
        capture_output=True,
        text=True,
    )
    if version_result.returncode != 0:
        raise _BenchError("could not determine Codex CLI version")
    cli_version = version_result.stdout.strip()
    metadata: Json = {
        "requested_model": options.model,
        "requested_reasoning_effort": options.reasoning_effort,
        "representation": options.representation,
        "scale": options.scale,
        "benchmark_case": options.benchmark_case,
        "requested_codex_version": cli_version,
    }
    repetitions = options.repetitions or MAX_REPETITIONS
    if not 1 <= repetitions <= MAX_REPETITIONS:
        raise _BenchError(f"repetitions must be 1 through {MAX_REPETITIONS}")
    timeout_seconds = options.timeout_seconds or 300
    if not 1 <= timeout_seconds <= 600:
        raise _BenchError("timeout must be 1 through 600 seconds")
    expected = CASES[options.benchmark_case].expected
    runs: list[list[Json]] = []
    round_trips: list[Json | None] = []
    for _ in range(repetitions):
        sessions_before = glob.glob(
            os.path.join(_session_root(), "**", "*.jsonl"), recursive=True
        )
        with tempfile.TemporaryDirectory(prefix="tangle-token-benchmark-") as directory:
            fixture = _generate_fixture(
                directory, options.representation, options.scale, options.benchmark_case
            )
            answer_path = os.path.join(directory, "answer.json")
            schema_path = os.path.join(directory, "answer.schema.json")
            fixture_before = {
                os.path.relpath(path, directory): Path(path).read_bytes()
                for path in _fixture_files(directory)
            }
            command = [
                _codex_command(),
                "exec",
                "--json",
                "--ignore-user-config",
                "--ignore-rules",
                "-C",
                directory,
                "--model",
                options.model,
                "-c",
                f"model_reasoning_effort={options.reasoning_effort}",
                "--sandbox",
                "workspace-write"
                if options.benchmark_case == "routine-mutation"
                else "read-only",
            ]
            if options.benchmark_case != "routine-mutation":
                command += ["--output-schema", schema_path]
            command += [
                "--output-last-message",
                answer_path,
                "--",
                Path(directory, "TASK.txt").read_text(encoding="utf-8"),
            ]
            stdout, success = _capture_merged(command, timeout_seconds)
            if not success:
                tail = stdout.splitlines()[-1].strip() if stdout.splitlines() else ""
                raise _BenchError(f"live Codex run failed: {tail}")
            if options.benchmark_case == "routine-mutation":
                _completed_mutation(stdout, answer_path, directory, fixture_before)
            else:
                _completed_answer(stdout, answer_path, expected)
            metadata.update(fixture)
            session_path = _newest_session(sessions_before, directory)
            _wait_for_session_usage(session_path)
            observations = _assert_live_observations(
                session_path,
                requested={"model": options.model, "effort": options.reasoning_effort},
                fixture_dir=directory,
                cli_version=cli_version,
            )
            metadata["observed_session_telemetry"] = observations
            runs.append(_session_usage(session_path))
            round_trips.append(_session_round_trips(session_path))
    _emit_record(
        runs,
        round_trips,
        {**metadata, "source": "fresh-codex-session"},
        options.output,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tangle benchmark token",
        description="Opt-in Codex token benchmark with a zero-live-call protocol.",
    )
    parser.add_argument("--protocol", action="store_true", help="Print the no-live-call protocol")
    parser.add_argument(
        "--check-fixture",
        action="store_true",
        help="Generate each fixture variant and verify its fixed metadata",
    )
    parser.add_argument("--session", action="append", default=[], help="Parse one session JSONL")
    parser.add_argument(
        "--inspect-session",
        help="Print token-record key shapes only; never session content",
    )
    parser.add_argument(
        "--check-recording",
        help="Zero-live check of a canned Codex JSON stream; requires --answer PATH",
    )
    parser.add_argument("--answer", help="Answer artifact for --check-recording")
    parser.add_argument(
        "--check-output-schema",
        action="store_true",
        help="Print the generated output schema without making a live call",
    )
    parser.add_argument("--task-path", help="Validate observed session task path")
    parser.add_argument("--model", help="Record setting, or validate observed session model")
    parser.add_argument(
        "--reasoning-effort",
        help="Record setting, or validate observed session effort",
    )
    parser.add_argument("--record", action="store_true", help="Opt in to bounded live sessions")
    parser.add_argument("--case", dest="benchmark_case", choices=list(CASES), default="composite")
    parser.add_argument("--representation", choices=list(REPRESENTATIONS), default="graph")
    parser.add_argument("--scale", choices=list(SCALES), default="small")
    parser.add_argument("--repetitions", type=int, help=f"Live samples (1..{MAX_REPETITIONS})")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        help="Per-live-session timeout (1..600; default 300)",
    )
    parser.add_argument("--output", help="Write a reviewable JSON artifact")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the token benchmark and return the process exit code."""
    parser = _build_parser()
    options = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        if options.check_output_schema:
            if options.record or options.session or options.check_recording or options.answer:
                raise _BenchError("--check-output-schema cannot be combined")
            print(_compact(_output_schema(CASES[options.benchmark_case].expected)))
            return 0
        if options.check_recording:
            if not options.answer:
                raise _BenchError("--check-recording requires --answer PATH")
            if options.record or options.session:
                raise _BenchError("--check-recording cannot be combined")
            with open(options.check_recording, "rb") as handle:
                stream = handle.read().decode("utf-8")
            _completed_answer(
                stream, options.answer, CASES[options.benchmark_case].expected
            )
            print("recording_check{status,live_calls}: valid,0")
            return 0
        if options.check_fixture:
            if options.record or options.session:
                raise _BenchError("--check-fixture cannot be combined")
            return _check_fixture(options.benchmark_case)
        if options.inspect_session:
            if options.record or options.session:
                raise _BenchError("--inspect-session cannot be combined")
            return _inspect_session(options.inspect_session)
        if options.protocol:
            if options.record or options.session:
                raise _BenchError("--protocol cannot be combined")
            _protocol()
            return 0
        if options.output and not options.record:
            raise _BenchError("--output is only valid with --record")
        if options.timeout_seconds and not options.record:
            raise _BenchError("--timeout-seconds is only valid with --record")
        if options.record:
            if options.session:
                raise _BenchError("--session is not valid with --record")
            return _run_record(options)
        if not options.session:
            raise _BenchError("provide --session or --record")
        if options.repetitions:
            raise _BenchError("--repetitions is only valid with --record")
        provenance = [
            _historical_session_provenance(
                path,
                expected={
                    "model": options.model,
                    "effort": options.reasoning_effort,
                    "task_path": options.task_path,
                },
            )
            for path in options.session
        ]
        _emit_historical_accounting([_session_usage(path) for path in options.session], provenance)
        return 0
    except (
        _BenchError,
        _TimeoutError,
        json.JSONDecodeError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
