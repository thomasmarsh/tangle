#!/usr/bin/env python3
"""Generate and collect the isolated memory-pilot-v2 live run.

The live run is a pi-subagents fan-out: three deterministic 24-child batches of
the 72 planned episodes, each child the isolated ``memory-pilot-child`` profile.
This script only builds the batch workflows and, after they run, reconstructs
the recorder samples from the retained async run directories. It makes no model
call itself.

    uv run python scripts/memory_pilot_v2_run.py generate [RUNDIR]
    uv run python scripts/memory_pilot_v2_run.py collect RUNDIR \\
        [--runs-root DIR] [--out PATH]

``collect`` scans ``*_/status.json`` under the pi-subagents async run root for
runs whose ``workflowKey`` is a planned episode key, keeps the latest run per
key, and writes a ``{"samples": [...]}`` document plus the recorded result.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from braintree import memory_pilot as mp  # noqa: E402

DEFAULT_RUN_DIR = Path(tempfile.gettempdir()) / "memory-pilot-v2"
_REASONING = re.compile(r'"reasoning":(\d+)')


def _write_batch(run_dir: Path, episodes: list[dict], index: int) -> int:
    tasks = []
    for episode in episodes:
        prompt = (run_dir / "prompts" / f"{episode['key']}.txt").read_text(encoding="utf-8")
        tasks.append({"key": episode["key"], "task": prompt})
    script = [
        "const tasks = " + json.dumps(tasks, ensure_ascii=True) + ";",
        "const results = await runs.all(tasks.map(function (t) {",
        "  return { key: t.key, agent: 'memory-pilot-child', task: t.task, context: 'fresh' };",
        "}));",
        "return JSON.stringify(results.map(function (r) {",
        "  const step = (r.results && r.results[0]) || {};",
        "  return { key: r.key, runId: r.runId, output: r.output, model: step.model,",
        "    usage: step.usage, asyncDir: (r.artifactPaths && r.artifactPaths[0]) || null };",
        "}));",
        "",
    ]
    (run_dir / f"batch{index + 1}.js").write_text("\n".join(script), encoding="utf-8")
    return len(tasks)


def generate(run_dir: Path) -> int:
    plan = mp.plan_document()
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompts").mkdir(exist_ok=True)
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    from braintree import memory_corpus

    corpus = memory_corpus.load_corpus(Path("."))
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    cache: dict = {}
    for episode in plan["episodes"]:
        fixture = mp.build_fixture(cases[episode["case_id"]], episode["arm"], Path("."), cache)
        prompt = mp.render_prompt(fixture)
        if mp.prompt_digest(prompt) != episode["prompt_digest"]:
            raise SystemExit(f"prompt digest drift for {episode['key']}")
        (run_dir / "prompts" / f"{episode['key']}.txt").write_text(prompt, encoding="utf-8")
    for index in range(mp.PILOT_V2_BATCHES):
        start = index * mp.PILOT_V2_BATCH_SIZE
        chunk = plan["episodes"][start : start + mp.PILOT_V2_BATCH_SIZE]
        count = _write_batch(run_dir, chunk, index)
        print(f"batch{index + 1}.js: {count} children")
    print(f"plan: {plan['plan_digest']}  run dir: {run_dir}")
    return 0


def _iso(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=UTC).isoformat().replace("+00:00", "Z")


def _reasoning(run_dir: Path) -> int:
    best = 0
    events = run_dir / "events.jsonl"
    if events.is_file():
        for value in _REASONING.findall(events.read_text(encoding="utf-8", errors="ignore")):
            best = max(best, int(value))
    return best


def _status_roots(runs_root: str | None) -> list[Path]:
    roots = (
        glob.glob(os.path.join(tempfile.gettempdir(), "pi-subagents-uid-*", "async-subagent-runs"))
        if runs_root is None
        else [runs_root]
    )
    return [Path(root) for root in roots]


def collect(run_dir: Path, runs_root: str | None, out_path: str | None) -> int:
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    keys = {episode["key"]: episode for episode in plan["episodes"]}
    latest: dict[str, tuple[float, Path, dict]] = {}
    for root in _status_roots(runs_root):
        for status_path in root.glob("*/status.json"):
            try:
                status = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            key = status.get("workflowKey")
            if key not in keys:
                continue
            steps = status.get("steps") or []
            if not steps:
                continue
            ended = float(status.get("endedAt") or steps[0].get("endedAt") or 0)
            if key not in latest or ended > latest[key][0]:
                latest[key] = (ended, status_path, status)
    samples = []
    for key, (_ended, status_path, status) in latest.items():
        step = status["steps"][0]
        attempt = (step.get("modelAttempts") or [{}])[0]
        usage = attempt.get("usage") or step.get("tokens") or {}
        recent = step.get("recentOutput") or []
        output = recent[-1] if recent else ""
        started = step.get("startedAt")
        ended = step.get("endedAt")
        input_tokens = int(usage.get("input") or 0)
        cached = int(usage.get("cacheRead") or 0)
        output_tokens = int(usage.get("output") or 0)
        actual_model = str(step.get("model") or attempt.get("model") or "")
        actual_model = actual_model.split(":", 1)[0]
        samples.append(
            {
                "key": key,
                "child_run_id": status_path.parent.name,
                "raw_output_ref": status.get("outputFile") or str(status_path.parent),
                "raw_output": output,
                "prompt_digest": keys[key]["prompt_digest"],
                "model": actual_model or mp.PILOT_V2_MODEL,
                "started_at": _iso(started),
                "finished_at": _iso(ended),
                "telemetry": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached,
                    "uncached_input_tokens": max(input_tokens - cached, 0),
                    "output_tokens": output_tokens,
                    "reasoning_output_tokens": _reasoning(status_path.parent),
                    "total_tokens": input_tokens + output_tokens,
                    "tool_calls": 0,
                    "shell_calls": 0,
                    "model_turns": int(usage.get("turns") or step.get("turnCount") or 1),
                    "files_opened": 0,
                    "nodes_opened": 0,
                    "monetary_cost": float(usage.get("cost") or 0.0),
                },
            }
        )
    samples_path = run_dir / "samples.json"
    samples_path.write_text(json.dumps({"samples": samples}, indent=2), encoding="utf-8")
    result = mp.record(plan, samples)
    problems = mp.result_problems(result)
    if problems:
        raise SystemExit("result problems: " + "; ".join(problems))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if out_path:
        Path(out_path).write_text(rendered, encoding="utf-8")
        print(f"recorded {len(samples)}/{len(keys)} samples -> {out_path}")
    else:
        print("recorded", len(samples), "of", len(keys), "samples; status", result["status"])
    print("status:", result["status"], "verdict:", result["verdict"])
    return 0 if result["status"] == "complete" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("run_dir", nargs="?", type=Path, default=DEFAULT_RUN_DIR)
    col = sub.add_parser("collect")
    col.add_argument("run_dir", nargs="?", type=Path, default=DEFAULT_RUN_DIR)
    col.add_argument("--runs-root", default=None)
    col.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.command == "generate":
        return generate(args.run_dir)
    return collect(args.run_dir, args.runs_root, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
