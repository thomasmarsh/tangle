"""The native in-process embedding provider behind the semantic seam.

``braintree semantic embed`` is the shipped ``BT_SEMANTIC_PROVIDER`` command:
it reads a JSON array of texts on stdin and writes the protocol's JSON array of
equal-width vectors on stdout, using fastembed on ONNX Runtime, the runtime and
default model chosen for the optional semantic layer (see the model-selection
decision). Fastembed and the rest of the heavy stack are imported lazily inside
the handler, so importing this module from the interactive path costs nothing
and a plain install keeps ``dependencies = []``.

The provider only reads weights the operator already pre-fetched into the
documented offline cache: the online Hub flags are forced off before the runtime
loads, so an absent cache fails the command and the seam degrades to the lexical
baseline instead of downloading at query time. Nothing is written to stdout
except the JSON vector array; every malformed or unavailable result exits
non-zero with a diagnostic on stderr, which is exactly the absence
:func:`braintree.semantic.probe` already treats as capability absent.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from . import semantic

__all__ = [
    "DEFAULT_MODEL",
    "FALLBACK_MODEL",
    "ProviderError",
    "embed",
    "main",
]

# The chosen off-the-shelf default and fallback models, loaded through
# fastembed's ONNX copies. Both are 384-dimensional and read from the local
# cache; only the default is used unless it cannot load.
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FALLBACK_MODEL = "BAAI/bge-small-en-v1.5"
_ENV_MODEL = "BT_EMBEDDING_MODEL"
# Text is embedded in bounded batches so a large vault never makes one unbounded
# runtime call, while a whole request is still served by one model load.
_BATCH_SIZE = 32

_USAGE = (
    "usage: braintree semantic embed [--model NAME]\n"
    "Read a JSON array of texts on stdin and write a JSON array of equal-width\n"
    "vectors on stdout, for use as the BT_SEMANTIC_PROVIDER command. The model\n"
    f"comes from --model, then BT_EMBEDDING_MODEL, then {DEFAULT_MODEL}, with\n"
    f"{FALLBACK_MODEL} as the fallback when the default cannot load. Weights are\n"
    "read offline from the BT_MODEL_CACHE/HF_HOME cache, so nothing downloads at\n"
    "query time and an unpopulated cache exits non-zero.\n"
    "The provider identity used by the sidecar vector cache is this command\n"
    "string, so pin --model in BT_SEMANTIC_PROVIDER when it is not the default."
)

# One loaded model, called with a batch of texts and returning one vector each.
Model = Callable[[Sequence[str]], list[list[float]]]
Loader = Callable[[str, Path], Model]


class ProviderError(Exception):
    """A failure that makes the capability absent: reported and exited non-zero."""


def model_name(requested: str | None = None) -> str:
    """Return the model to load: the argument, then ``BT_EMBEDDING_MODEL``, then the default."""
    if requested and requested.strip():
        return requested.strip()
    configured = os.environ.get(_ENV_MODEL, "").strip()
    return configured or DEFAULT_MODEL


def _load(model: str, cache: Path) -> Model:
    """Import fastembed lazily and load ``model`` once from the offline cache.

    The online Hub flags are set before the runtime imports its Hub client, so
    the load can only succeed against weights already present in ``cache`` and
    never downloads. Fastembed applies its registry's own prompt convention, so
    the text the seam sends is embedded as-is.
    """
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    module = importlib.import_module("fastembed")
    embedding = module.TextEmbedding(
        model_name=model,
        cache_dir=str(cache),
        local_files_only=True,
    )

    def encode(texts: Sequence[str]) -> list[list[float]]:
        return [
            [float(value) for value in vector]
            for vector in embedding.embed(list(texts), batch_size=_BATCH_SIZE)
        ]

    return encode


def _batched(encode: Model, texts: Sequence[str]) -> list[list[float]]:
    """Embed ``texts`` in bounded batches, preserving order."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        vectors.extend(encode(list(texts[start : start + _BATCH_SIZE])))
    return vectors


def _checked(vectors: Sequence[Sequence[float]], count: int) -> list[list[float]]:
    """Return the vectors, or raise when the result cannot be the protocol's.

    The protocol is one vector per text, all the same non-zero width. Anything
    else is a result the seam would have to reject anyway, so it is refused here
    where it can still carry a diagnostic instead of a silent partial answer.
    """
    if len(vectors) != count:
        raise ProviderError(f"model returned {len(vectors)} vectors for {count} texts")
    width = len(vectors[0]) if vectors else 0
    if vectors and width == 0:
        raise ProviderError("model returned an empty vector")
    checked: list[list[float]] = []
    for vector in vectors:
        if len(vector) != width:
            raise ProviderError("model returned vectors of different widths")
        checked.append([float(value) for value in vector])
    return checked


def embed(
    texts: Sequence[str],
    model: str | None = None,
    cache: Path | None = None,
    loader: Loader | None = None,
) -> list[list[float]]:
    """Embed ``texts`` with one model load and return the protocol's vectors.

    ``model`` defaults to :func:`model_name`, ``cache`` to the documented
    offline cache, and ``loader`` to the real fastembed load, which a test
    replaces with a deterministic fake model. The selected default falls back to
    :data:`FALLBACK_MODEL` once when it cannot load; any other failure raises
    :class:`ProviderError` so the caller reports absence.
    """
    selected = model_name(model)
    directory = semantic.model_cache() if cache is None else cache
    load = _load if loader is None else loader
    try:
        encode = load(selected, directory)
    except Exception as error:
        if selected != DEFAULT_MODEL:
            raise ProviderError(f"cannot load {selected}: {error}") from error
        try:
            encode = load(FALLBACK_MODEL, directory)
        except Exception as fallback_error:
            raise ProviderError(
                f"cannot load {selected} or fallback {FALLBACK_MODEL}: {fallback_error}"
            ) from fallback_error
    return _checked(_batched(encode, texts), len(texts))


def _read_texts() -> list[str] | None:
    """Read the protocol's JSON array of texts from stdin, or report a bad request."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"error: invalid JSON on stdin: {error}", file=sys.stderr)
        return None
    if not isinstance(payload, list) or not all(isinstance(text, str) for text in payload):
        print("error: stdin must be a JSON array of strings", file=sys.stderr)
        return None
    return list(payload)


def _usage_error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    print(_USAGE, file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run the provider command and return its exit code."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    model: str | None = None
    position = 0
    while position < len(arguments):
        token = arguments[position]
        if token in {"-h", "--help"}:
            print(_USAGE)
            return 0
        if token == "--model" or token.startswith("--model="):
            value = token.partition("=")[2]
            if not value and token == "--model":
                position += 1
                if position >= len(arguments):
                    return _usage_error("missing value for --model")
                value = arguments[position]
            model = value
            position += 1
            continue
        return _usage_error(f"unknown argument: {token}")
    texts = _read_texts()
    if texts is None:
        return 1
    try:
        vectors = embed(texts, model=model)
    except ProviderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    json.dump(vectors, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
