"""Protocol, offline, and cache tests for the native embedding provider.

``braintree semantic embed`` is the shipped ``BT_SEMANTIC_PROVIDER`` command for
the optional semantic seam in :mod:`braintree.semantic`. These tests drive it
with a deterministic injected fake model, so they never import fastembed, never
download weights, and stay fast; the real runtime is the opt-in ``semantic``
extra and needs a populated offline cache the suite must not depend on.

What the fake model proves: the command speaks the protocol exactly (a JSON
array of equal-width vectors on stdout and nothing else), it loads the selected
model once per process and batches texts, an absent extra, missing cache, or a
malformed, empty, or wrong-width result is capability absent, the default falls
back to the chosen fallback model, and the seam's sidecar content-hash cache
holds when the native command serves it (unchanged nodes are not re-embedded and
one changed node triggers exactly one new embedding call). The provider command
string is the sidecar cache identity, so the model has to be pinnable in it.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from braintree import provider, semantic

RunBt = Callable[..., subprocess.CompletedProcess[str]]

_ROOT = Path(__file__).resolve().parents[1]

# The heavy modules only the opt-in ``semantic`` extra provides. Importing the
# provider and running its help must never pull one of them in a plain install.
_HEAVY_MODULES = ("numpy", "sklearn", "fastembed", "onnxruntime")

# Driving the provider entry point in a fresh interpreter is the only way to
# observe the real import graph. The help path answers without reading stdin,
# then the probe reports every heavy module it loaded, which must be none.
_IMPORT_PROBE = """\
import sys
from braintree import main, provider

assert provider.main(["--help"]) == 0
assert main.main(["semantic", "embed", "--help"]) == 0
print("heavy:" + ",".join(name for name in sys.argv[1:] if name in sys.modules))
"""

# A deterministic stand-in for the real fastembed model, installed over the
# provider's one heavy load seam. It canonicalizes a few synonyms and projects
# each canonical token onto a small fixed vocabulary, so a paraphrase sharing no
# surface tokens with a node still matches it, and it appends one JSON line per
# model load and per batch to ``BT_FAKE_MODEL_LOG`` so a test can count calls.
# ``BT_FAKE_MODEL_MODE=unavailable`` makes the load fail like an unpopulated
# cache; ``empty`` returns an empty vector like a broken runtime.
_FAKE_MODEL = """\
import json
import os
import sys

from braintree import provider

MODE = os.environ.get("BT_FAKE_MODEL_MODE", "ok")
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


def log(event):
    with open(os.environ["BT_FAKE_MODEL_LOG"], "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + chr(10))


def fake_load(model, cache):
    if MODE == "unavailable":
        raise OSError("no cached weights for " + model)
    log("load")

    def encode(texts):
        log(list(texts))
        if MODE == "empty":
            return [[] for _ in texts]
        return [vector(text) for text in texts]

    return encode


provider._load = fake_load
raise SystemExit(provider.main(sys.argv[1:]))
"""

_QUERY = "lapsed auth grant rejection"


class _FakeModel:
    """A deterministic fake model that records each load and each batch."""

    def __init__(self, fail: tuple[str, ...] = (), width: int = 4) -> None:
        self.fail = fail
        self.width = width
        self.loads: list[tuple[str, str]] = []
        self.batches: list[list[str]] = []

    def load(self, model: str, cache: Path) -> provider.Model:
        if model in self.fail:
            raise OSError(f"no cached weights for {model}")
        self.loads.append((model, str(cache)))

        def encode(texts: Sequence[str]) -> list[list[float]]:
            self.batches.append(list(texts))
            return [
                [float(len(text)), float(index)] + [1.0] * (self.width - 2)
                for index, text in enumerate(texts)
            ]

        return encode


def _raw_loader(output: list[list[float]]) -> provider.Loader:
    """Return a loader whose model returns ``output`` for every batch."""

    def load(model: str, cache: Path) -> provider.Model:
        return lambda texts: output

    return load


def _lines(path: Path) -> list[object]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _fake_command(tmp_path: Path) -> str:
    """Install the fake-model provider script and return its command string."""
    digest = hashlib.sha256(_FAKE_MODEL.encode("utf-8")).hexdigest()[:8]
    script = tmp_path / f"fake-model-{digest}.py"
    script.write_text(_FAKE_MODEL, encoding="utf-8")
    return shlex.join([sys.executable, str(script)])


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


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


# --- The provider protocol ---------------------------------------------------


def test_command_writes_only_the_protocol_vector_array(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Texts on stdin become a JSON array of equal-width vectors and nothing else."""
    fake = _FakeModel()
    monkeypatch.setattr(provider, "_load", fake.load)
    monkeypatch.setattr("sys.stdin", io.StringIO('["one text", "another text"]'))

    code = provider.main([])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    vectors = json.loads(captured.out)
    assert len(vectors) == 2
    assert [len(vector) for vector in vectors] == [4, 4]
    # One process, one request, one model load.
    assert [model for model, _cache in fake.loads] == [provider.DEFAULT_MODEL]


def test_command_model_flag_overrides_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--model`` wins over ``BT_EMBEDDING_MODEL``, which wins over the default."""
    monkeypatch.setenv("BT_EMBEDDING_MODEL", provider.DEFAULT_MODEL)
    assert provider.model_name() == provider.DEFAULT_MODEL
    monkeypatch.setenv("BT_EMBEDDING_MODEL", provider.FALLBACK_MODEL)
    assert provider.model_name() == provider.FALLBACK_MODEL
    assert provider.model_name("custom/model") == "custom/model"

    fake = _FakeModel()
    monkeypatch.setattr(provider, "_load", fake.load)
    monkeypatch.setattr("sys.stdin", io.StringIO('["one text"]'))
    assert provider.main(["--model", provider.FALLBACK_MODEL]) == 0
    capsys.readouterr()
    assert [model for model, _cache in fake.loads] == [provider.FALLBACK_MODEL]


def test_model_loads_once_per_process_and_batches_texts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Seventy texts are one model load and bounded batches, in order."""
    fake = _FakeModel()
    texts = [f"text {index}" for index in range(70)]

    vectors = provider.embed(texts, cache=tmp_path, loader=fake.load)

    assert len(vectors) == 70
    assert fake.loads == [(provider.DEFAULT_MODEL, str(tmp_path))]
    assert [len(batch) for batch in fake.batches] == [32, 32, 6]
    assert [text for batch in fake.batches for text in batch] == texts


def test_default_falls_back_to_the_chosen_fallback_model(tmp_path: Path) -> None:
    """An unloadable default loads ``BAAI/bge-small-en-v1.5`` once; nothing else falls back."""
    fake = _FakeModel(fail=(provider.DEFAULT_MODEL,))
    assert len(provider.embed(["text"], cache=tmp_path, loader=fake.load)) == 1
    assert fake.loads == [(provider.FALLBACK_MODEL, str(tmp_path))]

    explicit = _FakeModel(fail=(provider.FALLBACK_MODEL,))
    with pytest.raises(provider.ProviderError):
        provider.embed(
            ["text"], model=provider.FALLBACK_MODEL, cache=tmp_path, loader=explicit.load
        )
    assert explicit.loads == []


def test_malformed_empty_and_wrong_width_results_are_refused(tmp_path: Path) -> None:
    """A result the seam would have to reject is refused instead of printed."""
    cases: tuple[tuple[list[list[float]], list[str]], ...] = (
        ([], ["a", "b"]),  # wrong count
        ([[]], ["a"]),  # empty vector
        ([[1.0, 2.0], [1.0, 2.0, 3.0]], ["a", "b"]),  # wrong width
    )
    for output, texts in cases:
        with pytest.raises(provider.ProviderError):
            provider.embed(texts, cache=tmp_path, loader=_raw_loader(output))


def test_missing_extra_or_empty_cache_exits_non_zero_with_empty_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unpopulated cache or absent extra is a non-zero exit, not a bad answer."""
    fake = _FakeModel(fail=(provider.DEFAULT_MODEL, provider.FALLBACK_MODEL))
    monkeypatch.setattr(provider, "_load", fake.load)
    monkeypatch.setattr("sys.stdin", io.StringIO('["one text"]'))

    code = provider.main([])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "cannot load" in captured.err


def test_importing_and_running_the_provider_loads_no_heavy_module() -> None:
    """The registered verb and its help path stay on the plain install."""
    env = os.environ.copy()
    env.pop("BT_SEMANTIC_PROVIDER", None)
    probe = subprocess.run(
        [sys.executable, "-c", _IMPORT_PROBE, *_HEAVY_MODULES],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr
    report = [line for line in probe.stdout.splitlines() if line.startswith("heavy:")]
    assert report == ["heavy:"]


# --- The native command behind the seam --------------------------------------


def _seam_env(tmp_path: Path, vault: Path, command: str) -> dict[str, str]:
    return {
        "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "BT_PROJECT_ID": "provider-test",
        "BT_NODES_DIR": str(vault),
        "BT_SEMANTIC_PROVIDER": command,
        "BT_FAKE_MODEL_LOG": str(tmp_path / "calls.jsonl"),
    }


def _lexical(tmp_path: Path, vault: Path, run_bt: RunBt) -> str:
    """Return the lexical baseline answer with no provider configured."""
    result = run_bt(
        "similar",
        _QUERY,
        env={
            "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
            "BT_PROJECT_ID": "provider-test",
            "BT_NODES_DIR": str(vault),
            "BT_SEMANTIC_PROVIDER": None,
        },
    )
    assert result.returncode == 0
    return result.stdout


def test_native_command_reranks_a_paraphrase_and_caches_by_content_hash(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """The seam serves real reranking from the native command, cached by content hash."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    command = _fake_command(tmp_path)
    env = _seam_env(tmp_path, vault, command)
    log = tmp_path / "calls.jsonl"

    lexical = _lexical(tmp_path, vault, run_bt)
    assert lexical.strip() == "similar: 0 matching nodes"

    first = run_bt("similar", _QUERY, env=env)
    assert first.returncode == 0
    rows = _toon_rows(first.stdout, "similar")
    assert sorted(row[0] for row in rows) == ["DEF-001", "TAS-001"]
    assert "DEF-002" not in first.stdout
    # One process for the probe, one for the batch: each loads the model once,
    # and the batch carries every node plus the query in a single call.
    calls = _lines(log)
    assert calls[0] == "load"
    assert calls[1] == ["braintree semantic probe"]
    assert calls[2] == "load"
    assert isinstance(calls[3], list) and len(calls[3]) == 4 and _QUERY in calls[3]
    assert len(calls) == 4

    second = run_bt("similar", _QUERY, env=env)
    assert second.returncode == 0
    assert second.stdout == first.stdout
    # Only the probe process ran: every vector came from the content-hash cache,
    # so no node and not even the query was re-embedded.
    assert _lines(log)[4:] == ["load", ["braintree semantic probe"]]

    _write(
        vault / "resolved" / "DEF-002-cache-policy.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-12T00:00:00Z\n"
        "summary: Cache warming policy.\n---\n\n# Invariant\n\n"
        "The cache warms cold entries.\n",
    )
    third = run_bt("similar", _QUERY, env=env)
    assert third.returncode == 0
    calls = _lines(log)
    # Probe plus exactly one embedding call, carrying the one changed node.
    assert calls[6:8] == ["load", ["braintree semantic probe"]]
    assert calls[8] == "load"
    assert isinstance(calls[9], list) and len(calls[9]) == 1
    assert "cache warms" in calls[9][0]
    assert len(calls) == 10


def test_provider_identity_is_the_command_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sidecar cache key follows the command string, so the model is pinnable."""
    monkeypatch.setenv("BT_FAKE_MODEL_LOG", str(tmp_path / "calls.jsonl"))
    command = _fake_command(tmp_path)

    default = semantic.probe(command)
    pinned = semantic.probe(f"{command} --model {provider.FALLBACK_MODEL}")

    assert default is not None
    assert pinned is not None
    assert default.dimensions == pinned.dimensions == 8
    assert default.key != pinned.key


@pytest.mark.parametrize("mode", ["unavailable", "empty"])
def test_absent_or_broken_native_command_degrades_to_the_lexical_baseline(
    tmp_path: Path, run_bt: RunBt, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """A cold cache or a malformed result is capability absent, not a failed verb."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    monkeypatch.setenv("BT_FAKE_MODEL_MODE", mode)
    lexical = _lexical(tmp_path, vault, run_bt)

    degraded = run_bt("similar", _QUERY, env=_seam_env(tmp_path, vault, _fake_command(tmp_path)))

    assert degraded.returncode == 0
    assert degraded.stdout == lexical
