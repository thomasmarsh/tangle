"""Optional semantic reranking behind the capability boundary.

Semantic retrieval is optional, derived, rebuildable, and never authoritative
(see the settled capability-boundary decision). This module owns the one seam
``braintree similar`` uses: an explicitly enabled external embedding provider is
probed, its vectors are cached in the disposable sidecar keyed by content hash,
and every caller degrades to the lexical baseline in :mod:`braintree.index` when
no provider is configured or a probe or call fails.

The provider is a command string in ``BT_SEMANTIC_PROVIDER``. It reads a JSON
array of texts on stdin and writes a JSON array of numeric vectors, one per
text and all the same length, on stdout. Nothing here is a required dependency:
with no provider configured, no process runs and no vector is read, so the
default answer is the lexical baseline byte for byte.

The inference runtime and the clustering libraries are the optional ``semantic``
extra, which a plain install never has. fastembed on ONNX Runtime is the
shipped runtime: it needs no torch. :func:`extra` reports whether that extra
is importable using ``importlib.util.find_spec`` alone, so probing it never
imports a heavy module, and :func:`model_cache` names the local directory
pre-fetched weights are read from offline.
"""

from __future__ import annotations

import json
import math
import os
import shlex
import sqlite3
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path

__all__ = [
    "SemanticExtra",
    "SemanticProvider",
    "cosine",
    "extra",
    "model_cache",
    "probe",
    "vectors",
]

_ENV_PROVIDER = "BT_SEMANTIC_PROVIDER"
_ENV_MODEL_CACHE = "BT_MODEL_CACHE"
_ENV_HF_HOME = "HF_HOME"
# The optional extra, as the top-level modules a plain install must not need:
# CPU inference through fastembed on ONNX Runtime, with numpy and scikit-learn,
# umap-learn for UMAP, and the hdbscan package for HDBSCAN. sentence-transformers
# and torch were the evaluation baseline and are deliberately not shipped, so
# they are not part of this set.
_EXTRA_MODULES = ("numpy", "sklearn", "umap", "hdbscan", "fastembed")
_PROBE_TEXT = "braintree semantic probe"
_TIMEOUT_SECONDS = 10
# The vector cache is disposable derived state keyed by provider identity and
# the content hash of the embedded text, so it survives an index rebuild and
# never becomes load-bearing for a Markdown-derived answer.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS semantic_cache (
  provider TEXT NOT NULL, content_hash TEXT NOT NULL,
  dimensions INTEGER NOT NULL, vector TEXT NOT NULL,
  PRIMARY KEY(provider, content_hash)
);
"""


@dataclass(frozen=True)
class SemanticProvider:
    """An enabled, probed embedding provider and its cache identity."""

    command: str
    key: str
    dimensions: int


@dataclass(frozen=True)
class SemanticExtra:
    """The installed optional inference extra and the cache it reads."""

    modules: tuple[str, ...]
    model_cache: Path


def model_cache() -> Path:
    """Return the local directory holding the pre-fetched model weights.

    ``BT_MODEL_CACHE`` names it explicitly. Otherwise the Hugging Face cache
    convention applies: ``HF_HOME`` when set, else ``~/.cache/huggingface``,
    with weights under the ``hub`` subdirectory. Inference reads weights from
    here and never downloads at query time, so an operator pre-fetches once
    into this directory and every later command runs offline.
    """
    explicit = os.environ.get(_ENV_MODEL_CACHE, "").strip()
    if explicit:
        return Path(explicit).expanduser()
    hf_home = os.environ.get(_ENV_HF_HOME, "").strip()
    base = Path(hf_home).expanduser() if hf_home else Path.home() / ".cache" / "huggingface"
    return base / "hub"


def extra() -> SemanticExtra | None:
    """Return the installed optional extra, or ``None`` when it is missing.

    Presence is decided with ``importlib.util.find_spec``, which never imports
    the module it locates. A plain install therefore stays free of fastembed and
    every other heavy module, and each interactive verb keeps answering
    byte-identically without loading a model.
    """
    found: list[str] = []
    for name in _EXTRA_MODULES:
        try:
            location = find_spec(name)
        except (ImportError, ValueError):
            location = None
        if location is None:
            return None
        found.append(name)
    return SemanticExtra(modules=tuple(found), model_cache=model_cache())


def _provider_key(command: str) -> str:
    """Return the stable cache identity of a provider command string."""
    return sha256(command.encode("utf-8")).hexdigest()[:16]


def _invoke(command: str, texts: Sequence[str]) -> list[tuple[float, ...]] | None:
    """Run the provider on ``texts`` and return its vectors, or ``None`` on failure.

    The command is split without a shell so a configured provider cannot inject
    shell syntax. Any missing binary, non-zero exit, timeout, or malformed or
    empty vector is reported as absence rather than raised, which is what lets
    the caller fall back to the lexical baseline.
    """
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv:
        return None
    try:
        result = subprocess.run(
            argv,
            input=json.dumps(list(texts)),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    vectors: list[tuple[float, ...]] = []
    for entry in payload:
        if not isinstance(entry, list) or not entry:
            return None
        try:
            vectors.append(tuple(float(value) for value in entry))
        except (TypeError, ValueError):
            return None
    return vectors


def probe(command: str | None = None) -> SemanticProvider | None:
    """Return the configured provider when it answers the probe, else ``None``.

    ``command`` defaults to ``BT_SEMANTIC_PROVIDER``. An unset or blank command
    means the capability is absent, which is the default and needs no process.
    A command that fails, times out, or returns a malformed or empty vector is
    also absent, so an unhealthy provider degrades to the lexical baseline
    instead of failing the command.
    """
    raw = command if command is not None else os.environ.get(_ENV_PROVIDER, "")
    if not raw.strip():
        return None
    produced = _invoke(raw, [_PROBE_TEXT])
    if produced is None or len(produced) != 1 or not produced[0]:
        return None
    return SemanticProvider(
        command=raw, key=_provider_key(raw), dimensions=len(produced[0])
    )


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_SCHEMA)


def _load_cached(
    connection: sqlite3.Connection, key: str, hashes: Sequence[str]
) -> dict[str, tuple[float, ...]]:
    """Return the cached vectors for ``hashes`` under ``key``, skipping bad rows."""
    if not hashes:
        return {}
    placeholders = ",".join("?" for _ in hashes)
    rows = connection.execute(
        f"SELECT content_hash, vector FROM semantic_cache WHERE provider = ? "
        f"AND content_hash IN ({placeholders})",
        [key, *hashes],
    ).fetchall()
    cached: dict[str, tuple[float, ...]] = {}
    for content_hash, vector in rows:
        try:
            values = tuple(float(value) for value in json.loads(str(vector)))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        cached[str(content_hash)] = values
    return cached


def _store_cached(
    connection: sqlite3.Connection,
    key: str,
    items: Sequence[tuple[str, tuple[float, ...]]],
) -> None:
    connection.executemany(
        "INSERT INTO semantic_cache(provider, content_hash, dimensions, vector) "
        "VALUES(?,?,?,?) ON CONFLICT(provider, content_hash) DO UPDATE SET "
        "dimensions=excluded.dimensions, vector=excluded.vector",
        [
            (key, content_hash, len(vector), json.dumps(list(vector)))
            for content_hash, vector in items
        ],
    )


def vectors(
    provider: SemanticProvider,
    connection: sqlite3.Connection,
    items: Sequence[tuple[str, str]],
) -> dict[str, tuple[float, ...]] | None:
    """Return one vector per ``(content_hash, text)`` item, cached in the sidecar.

    Cached vectors are read from the disposable ``semantic_cache`` keyed by
    provider and content hash; only the hashes that miss are embedded, in one
    provider call. A provider failure or a vector of the wrong width returns
    ``None`` so the caller can fall back to the lexical baseline with a single
    consistent metric, rather than mixing semantic and lexical scores.
    """
    _ensure_schema(connection)
    wanted: dict[str, str] = {}
    for content_hash, text in items:
        wanted[content_hash] = text
    cached = _load_cached(connection, provider.key, list(wanted))
    missing = [content_hash for content_hash in wanted if content_hash not in cached]
    if missing:
        produced = _invoke(
            provider.command, [wanted[content_hash] for content_hash in missing]
        )
        if produced is None or len(produced) != len(missing):
            return None
        fresh: list[tuple[str, tuple[float, ...]]] = []
        for content_hash, vector in zip(missing, produced, strict=True):
            if len(vector) != provider.dimensions:
                return None
            fresh.append((content_hash, vector))
        _store_cached(connection, provider.key, fresh)
        cached.update(fresh)
    return cached


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the cosine similarity of two equal-width vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    if dot == 0:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
