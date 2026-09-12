"""Capability-boundary tests for the optional semantic retrieval layer.

``braintree similar`` is the lexical baseline by default. With an explicitly
enabled embedding provider it reranks by the provider's cosine and caches the
node vectors in the disposable sidecar keyed by content hash; when the provider
is absent or fails, the answer is the lexical baseline byte for byte. A small
deterministic stub provider stands in for a real embedding model so the tests
are hermetic and never touch the network.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shlex
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from braintree import semantic

RunBt = Callable[..., subprocess.CompletedProcess[str]]

# A deterministic stand-in for an embedding provider: it canonicalizes a few
# synonyms and projects each canonical token onto a small fixed vocabulary, so a
# paraphrase that shares no surface tokens with a node still matches it. The
# optional second argument is a call log so the tests can count provider calls.
_PROVIDER = """\
import json
import sys

CANONICAL = {
    "lapsed": "expired",
    "auth": "authentication",
    "grant": "grant",
    "grants": "grant",
    "rejection": "reject",
    "rejected": "reject",
    "rejects": "reject",
}
VOCABULARY = {
    "expired": 0,
    "authentication": 1,
    "grant": 2,
    "reject": 3,
    "cache": 4,
    "eviction": 5,
    "policy": 6,
    "session": 7,
}
DIMENSIONS = len(VOCABULARY)


def vector(text):
    values = [0.0] * DIMENSIONS
    for token in text.lower().split():
        slot = VOCABULARY.get(CANONICAL.get(token, token))
        if slot is not None:
            values[slot] += 1.0
    return values


texts = json.load(sys.stdin)
if len(sys.argv) > 1:
    with open(sys.argv[1], "a", encoding="utf-8") as log:
        log.write(json.dumps(texts) + chr(10))
print(json.dumps([vector(text) for text in texts]))
"""

# A provider that answers the single-text probe but fails on the batch call, so
# the probe succeeds and the rerank must still degrade to the lexical baseline.
_FLAKY_PROVIDER = """\
import json
import sys

payload = json.load(sys.stdin)
if len(payload) != 1:
    sys.exit(3)
print(json.dumps([[1.0, 0.0, 0.0]]))
"""


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "BT_PROJECT_ID": "semantic-test",
        "BT_NODES_DIR": str(vault),
    }


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _provider_command(tmp_path: Path, source: str, log: Path | None = None) -> str:
    """Install a stub provider script and return the ``BT_SEMANTIC_PROVIDER`` command."""
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:8]
    script = tmp_path / f"provider-{digest}.py"
    script.write_text(source, encoding="utf-8")
    argv = [sys.executable, str(script)]
    if log is not None:
        argv.append(str(log))
    return shlex.join(argv)


def _toon_rows(output: str, name: str) -> list[list[str]]:
    """Parse the indented TOON rows that follow a ``name[n]{...}:`` header line."""
    lines = output.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"{name}["))
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if not line.startswith("  "):
            break
        rows.append([cell.strip() for cell in next(csv.reader([line.strip()], escapechar="\\"))])
    return rows


def _seed_similar(vault: Path) -> None:
    """Seed a paraphrase target, its near-duplicate, and an unrelated node."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "proposed").mkdir()
    _write(
        vault / "resolved" / "DEF-001-grant-contract.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Reject expired authentication grants.\n---\n\n# Invariant\n\n"
        "Reject expired authentication grants before issuing a session.\n",
    )
    _write(
        vault / "proposed" / "TAS-001-reject-grants.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Reject expired authentication grants.\nnext: Implement it.\n---\n\n"
        "# Outcome\n\nReject expired authentication grants.\n",
    )
    _write(
        vault / "resolved" / "DEF-002-cache-policy.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Cache eviction policy.\n---\n\n# Invariant\n\n"
        "The cache evicts cold entries.\n",
    )


_PARAPHRASE = "lapsed auth grant rejection"


def _database(tmp_path: Path) -> Path:
    return tmp_path / "sidecar" / "projects" / "semantic-test" / "graph.sqlite3"


def test_provider_reranks_a_paraphrase_the_lexical_baseline_misses(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """A synonym paraphrase scores zero lexically and tops the semantic ranking."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    env = _env(tmp_path, vault)
    lexical = run_bt("similar", _PARAPHRASE, env=env)
    assert lexical.returncode == 0
    assert lexical.stdout.strip() == "similar: 0 matching nodes"

    env["BT_SEMANTIC_PROVIDER"] = _provider_command(tmp_path, _PROVIDER)
    reranked = run_bt("similar", _PARAPHRASE, env=env)
    assert reranked.returncode == 0
    rows = _toon_rows(reranked.stdout, "similar")
    assert sorted(row[0] for row in rows) == ["DEF-001", "TAS-001"]
    assert all(float(row[2]) > 0.5 for row in rows)
    assert "DEF-002" not in reranked.stdout


def test_probe_failure_degrades_to_the_lexical_baseline(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """An unconfigured or missing provider leaves the lexical answer unchanged."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    env = _env(tmp_path, vault)
    lexical = run_bt("similar", _PARAPHRASE, env=env)
    env["BT_SEMANTIC_PROVIDER"] = "definitely-not-a-provider-command"
    degraded = run_bt("similar", _PARAPHRASE, env=env)
    assert degraded.returncode == 0
    assert degraded.stdout == lexical.stdout


def test_batch_failure_degrades_to_the_lexical_baseline(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """A provider that passes the probe but fails the batch still degrades cleanly."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    env = _env(tmp_path, vault)
    lexical = run_bt("similar", _PARAPHRASE, env=env)
    env["BT_SEMANTIC_PROVIDER"] = _provider_command(tmp_path, _FLAKY_PROVIDER)
    degraded = run_bt("similar", _PARAPHRASE, env=env)
    assert degraded.returncode == 0
    assert degraded.stdout == lexical.stdout


def test_vectors_are_cached_by_content_hash(tmp_path: Path, run_bt: RunBt) -> None:
    """A warm run embeds nothing new, and a changed node is the only re-embed."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    log = tmp_path / "calls.jsonl"
    env = _env(tmp_path, vault)
    env["BT_SEMANTIC_PROVIDER"] = _provider_command(tmp_path, _PROVIDER, log)

    first = run_bt("similar", _PARAPHRASE, env=env)
    assert first.returncode == 0
    calls = log.read_text(encoding="utf-8").splitlines()
    # One probe call, then one batch call carrying every node plus the query.
    assert len(calls) == 2
    assert _PARAPHRASE in json.loads(calls[1])

    second = run_bt("similar", _PARAPHRASE, env=env)
    assert second.returncode == 0
    assert second.stdout == first.stdout
    # Only the probe ran: every vector came from the content-hash cache.
    assert len(log.read_text(encoding="utf-8").splitlines()) == 3

    _write(
        vault / "resolved" / "DEF-002-cache-policy.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-12T00:00:00Z\n"
        "summary: Cache warming policy.\n---\n\n# Invariant\n\n"
        "The cache warms cold entries.\n",
    )
    third = run_bt("similar", _PARAPHRASE, env=env)
    assert third.returncode == 0
    calls = log.read_text(encoding="utf-8").splitlines()
    # Probe plus one batch for the single changed content hash.
    assert len(calls) == 5
    assert len(json.loads(calls[4])) == 1


def test_cache_rows_are_keyed_by_provider_and_content_hash(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """The sidecar cache stores one row per provider and embedded content hash."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    env = _env(tmp_path, vault)
    command = _provider_command(tmp_path, _PROVIDER)
    env["BT_SEMANTIC_PROVIDER"] = command
    assert run_bt("similar", _PARAPHRASE, env=env).returncode == 0

    provider = semantic.probe(command)
    assert provider is not None
    connection = sqlite3.connect(_database(tmp_path))
    try:
        rows = connection.execute(
            "SELECT provider, content_hash, dimensions FROM semantic_cache"
        ).fetchall()
    finally:
        connection.close()
    # Three node texts plus the query text, all under the one provider identity.
    assert len(rows) == 4
    assert {row[0] for row in rows} == {provider.key}
    assert {row[2] for row in rows} == {provider.dimensions}
    assert len({row[1] for row in rows}) == 4
