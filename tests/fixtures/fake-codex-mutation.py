#!/usr/bin/env python3
"""Deterministic fake Codex CLI for the zero-live-call mutation recorder test.

Python port of ``tests/fixtures/fake-codex-mutation.rb``. It performs the one
expected node mutation, records the event stream the real CLI would emit, and
honors ``BT_FAKE_MUTATION_EXTRA_EDIT`` to exercise the unrelated-edit gate.
"""

from __future__ import annotations

import json
import os
import re
import sys


def _arg_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def main(argv: list[str]) -> int:
    if argv == ["--version"]:
        print("codex-cli fake-mutation-1")
        return 0

    root = _arg_value(argv, "-C")
    model = _arg_value(argv, "--model")
    effort = _arg_value(argv, "-c").removeprefix("model_reasoning_effort=")
    answer = _arg_value(argv, "--output-last-message")

    active = os.path.join(root, "nodes/active/TAS-201-validate-schema.md")
    resolved = os.path.join(root, "nodes/resolved/TAS-201-validate-schema.md")
    with open(active, "rb") as handle:
        text = handle.read().decode("utf-8")
    text = text.replace("context_rev: 3", "context_rev: 4")
    text = text.replace("updated: 2026-01-01T00:00:00Z", "updated: 2026-01-02T00:00:00Z")
    text = text.replace(
        "summary: Validate the signed schema contract.",
        "summary: Schema validation is complete.",
    )
    text = re.sub(r"^next: .*\n", "", text, count=1, flags=re.MULTILINE)
    text += "\n# Result\n\nValidated the signed schema contract.\n"
    with open(active, "wb") as handle:
        handle.write(text.encode("utf-8"))
    os.replace(active, resolved)
    with open(answer, "wb") as handle:
        handle.write(b"Routine mutation complete.\n")
    if os.environ.get("BT_FAKE_MUTATION_EXTRA_EDIT"):
        with open(os.path.join(root, "unexpected.txt"), "wb") as handle:
            handle.write(b"unexpected\n")

    sessions = os.environ["BT_TOKEN_BENCHMARK_SESSIONS_DIR"]
    path = os.path.join(sessions, "fake", "mutation.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    events = [
        {
            "type": "session_meta",
            "payload": {
                "cli_version": "fake-mutation-1",
                "cwd": root,
                "agent_path": "/fake/mutation",
            },
        },
        {
            "type": "turn_context",
            "payload": {"cwd": root, "model": model, "effort": effort},
        },
        {
            "type": "token_usage_record",
            "payload": {
                "turn_id": "fake-turn",
                "turn_token_usage": {
                    "input_tokens": 11,
                    "cached_input_tokens": 3,
                    "output_tokens": 5,
                    "reasoning_output_tokens": 2,
                    "total_tokens": 16,
                },
            },
        },
        {"type": "turn.completed", "turn_id": "fake-turn"},
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(event, separators=(",", ":")) for event in events) + "\n")
    print(json.dumps({"type": "turn.completed", "turn_id": "fake-turn"}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
