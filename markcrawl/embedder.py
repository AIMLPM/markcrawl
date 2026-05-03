"""Embedder abstraction for chunk and query embedding.

Two backends out of the box:

- :class:`OpenAIEmbedder` — wraps the OpenAI ``text-embedding-3-*``
  family. Sends batched HTTP requests; cost is per million input tokens.
- :class:`LocalSentenceTransformerEmbedder` — wraps any
  ``sentence-transformers`` model by HuggingFace ID. Runs on
  CPU/MPS/CUDA per ``torch``. Cost is wallclock + electricity, not API
  dollars, so :attr:`cost_per_1m_tokens` is ``0.0``.

Use :func:`make_embedder` to construct from a string spec — the same
form accepted by ``--embedder`` in ``bench/local_replica/run.py``.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import List

from .exceptions import MarkcrawlConfigError, MarkcrawlDependencyError


class Embedder(ABC):
    """Embeds a list of texts into fixed-dimensional vectors.

    Concrete classes set :attr:`model_id`, :attr:`dim`, and
    :attr:`cost_per_1m_tokens` at construction. ``dim`` may be inferred
    on first ``embed`` call for backends that don't expose it directly
    (e.g. some sentence-transformers models).

    The ``kind`` arg on :meth:`embed` (``"document"`` or ``"query"``)
    lets implementations apply model-specific instruction prefixes —
    BGE-family and nomic require these for full quality on retrieval
    workloads. Defaults to ``"document"`` so existing callers that
    don't distinguish are bias-neutral toward the document path.
    """

    model_id: str
    dim: int
    cost_per_1m_tokens: float

    @abstractmethod
    def embed(self, texts: List[str], kind: str = "document") -> List[List[float]]:
        """Return one vector per input text, in the same order.

        Parameters
        ----------
        texts:
            Input strings.
        kind:
            ``"document"`` for passages (the chunks being indexed) or
            ``"query"`` for user queries. Models that benefit from
            instruction-prefix conditioning use this to dispatch.
        """


# OpenAI text-embedding pricing as of 2026-04. Update as pricing changes.
# (dim, $/1M input tokens). Source: openai.com/api/pricing.
_OPENAI_PRICING = {
    "text-embedding-3-small": (1536, 0.02),
    "text-embedding-3-large": (3072, 0.13),
    "text-embedding-ada-002": (1536, 0.10),
}


class OpenAIEmbedder(Embedder):
    """OpenAI embedder. Reads ``OPENAI_API_KEY`` from env on first call."""

    def __init__(self, model: str = "text-embedding-3-small", batch_size: int = 96):
        if model not in _OPENAI_PRICING:
            raise MarkcrawlConfigError(
                f"Unknown OpenAI embedder: {model!r}. "
                f"Supported: {sorted(_OPENAI_PRICING)}"
            )
        self.model_id = model
        self.dim, self.cost_per_1m_tokens = _OPENAI_PRICING[model]
        self.batch_size = batch_size
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise MarkcrawlDependencyError(
                    "OpenAI embedder requires the openai SDK. Install with:\n"
                    "  pip install markcrawl[upload]"
                ) from exc
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise MarkcrawlConfigError(
                    "OPENAI_API_KEY environment variable is required for OpenAIEmbedder"
                )
            self._client = OpenAI(api_key=api_key)
        return self._client

    def embed(self, texts: List[str], kind: str = "document") -> List[List[float]]:
        # OpenAI text-embedding-3-* are symmetric — query and document
        # vectors live in the same space without instruction prefixes.
        if not texts:
            return []
        client = self._get_client()
        out: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = client.embeddings.create(input=batch, model=self.model_id)
            out.extend([d.embedding for d in resp.data])
        return out


# Local sentence-transformers models we know the dimension for upfront.
# Models not listed here are still supported — the dim is read from the
# model on first .embed() call.
_LOCAL_KNOWN_DIM = {
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-small-en-v1.5": 384,
    "mixedbread-ai/mxbai-embed-large-v1": 1024,
    "nomic-ai/nomic-embed-text-v1.5": 768,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
}

# Models that need ``trust_remote_code=True`` because they ship custom
# modeling code (not standard transformers architectures).
_LOCAL_TRUST_REMOTE_CODE = {
    "nomic-ai/nomic-embed-text-v1.5",
}

# Model-specific instruction prefixes for asymmetric retrieval. Format:
#   model_id -> (doc_prefix, query_prefix)
# Models not listed get empty prefixes (treated as symmetric — fine for
# OpenAI 3-* and st-mini family).
_LOCAL_PREFIXES: dict[str, tuple[str, str]] = {
    # Nomic uses task-prefixed inputs throughout — this is built into the
    # model's training, not optional.
    "nomic-ai/nomic-embed-text-v1.5": (
        "search_document: ",
        "search_query: ",
    ),
    # BGE family: only queries get the instruction; documents are raw.
    "BAAI/bge-large-en-v1.5": (
        "",
        "Represent this sentence for searching relevant passages: ",
    ),
    "BAAI/bge-base-en-v1.5": (
        "",
        "Represent this sentence for searching relevant passages: ",
    ),
    "BAAI/bge-small-en-v1.5": (
        "",
        "Represent this sentence for searching relevant passages: ",
    ),
    # Mixedbread reuses BGE's prompt convention.
    "mixedbread-ai/mxbai-embed-large-v1": (
        "",
        "Represent this sentence for searching relevant passages: ",
    ),
}


class LocalSentenceTransformerEmbedder(Embedder):
    """Sentence-transformers backend. ``model_id`` is a HuggingFace ID."""

    def __init__(self, model_id: str, batch_size: int = 64,
                 device: str | None = None):
        self.model_id = model_id
        self.dim = _LOCAL_KNOWN_DIM.get(model_id, -1)  # filled in on load
        self.cost_per_1m_tokens = 0.0
        self.batch_size = batch_size
        self.device = device  # None → sentence-transformers auto-picks
        self.doc_prefix, self.query_prefix = _LOCAL_PREFIXES.get(model_id, ("", ""))
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise MarkcrawlDependencyError(
                    "Local embedder requires sentence-transformers, which ships in the\n"
                    "default `pip install markcrawl` since v0.10.1. If it's missing you\n"
                    "likely installed with --no-deps; add it back with:\n"
                    "  pip install sentence-transformers torch transformers sentencepiece"
                ) from exc
            kwargs = {}
            if self.model_id in _LOCAL_TRUST_REMOTE_CODE:
                kwargs["trust_remote_code"] = True
            if self.device is not None:
                kwargs["device"] = self.device
            self._model = SentenceTransformer(self.model_id, **kwargs)
            if self.dim < 0:
                self.dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    def embed(self, texts: List[str], kind: str = "document") -> List[List[float]]:
        if not texts:
            return []
        prefix = self.query_prefix if kind == "query" else self.doc_prefix
        if prefix:
            texts = [prefix + t for t in texts]
        model = self._load()
        embs = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=False,
            convert_to_numpy=True,
        )
        return embs.tolist()


_OPENAI_PREFIXES = ("text-embedding-3-", "text-embedding-ada-")


def make_embedder(spec: str) -> Embedder:
    """Build an :class:`Embedder` from a string spec.

    Recognised forms::

        make_embedder("text-embedding-3-small")        # OpenAI auto-detected
        make_embedder("openai:text-embedding-3-large") # explicit prefix
        make_embedder("BAAI/bge-large-en-v1.5")        # local auto-detected (HF ID)
        make_embedder("local:nomic-ai/nomic-embed-text-v1.5")
    """
    if spec.startswith("openai:"):
        return OpenAIEmbedder(spec[len("openai:") :])
    if spec.startswith("local:"):
        return LocalSentenceTransformerEmbedder(spec[len("local:") :])
    if any(spec.startswith(p) for p in _OPENAI_PREFIXES):
        return OpenAIEmbedder(spec)
    return LocalSentenceTransformerEmbedder(spec)


# The default embedder shipped in v0.10.1+. Local sentence-transformers
# model, $0/yr cost-at-scale, MRR-neutral vs OpenAI 3-small (Δ −0.018
# within ±0.020 SC-B2 band per the v0.10 bake-off). Pinning here so
# callers and tests share one source of truth.
DEFAULT_EMBEDDER_SPEC = "mixedbread-ai/mxbai-embed-large-v1"


def make_default_embedder() -> Embedder:
    """Return the default :class:`Embedder` for production callers.

    Picks ``mxbai-embed-large-v1`` (local, $0/yr) when
    ``sentence_transformers`` is importable. Falls back to
    ``OpenAIEmbedder("text-embedding-3-small")`` only when someone
    installed markcrawl with ``--no-deps`` and didn't add the ml stack
    back in — at which point an ``OPENAI_API_KEY`` is required at
    embed time.

    Since v0.10.1 the ml stack ships in the base install, so the
    fallback path is rare. Override globally with the ``MARKCRAWL_EMBEDDER``
    env var (any string that :func:`make_embedder` accepts).
    """
    import os
    spec = os.environ.get("MARKCRAWL_EMBEDDER")
    if spec:
        return make_embedder(spec)
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return OpenAIEmbedder("text-embedding-3-small")
    return LocalSentenceTransformerEmbedder(DEFAULT_EMBEDDER_SPEC)
