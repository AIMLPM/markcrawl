"""Tests for markcrawl.embedder — embedder abstraction."""

from __future__ import annotations

import pytest

from markcrawl.embedder import (
    Embedder,
    LocalSentenceTransformerEmbedder,
    OpenAIEmbedder,
    make_embedder,
)
from markcrawl.exceptions import MarkcrawlConfigError, MarkcrawlDependencyError


# ---------------------------------------------------------------------------
# OpenAIEmbedder — uses a fake client so tests don't hit the network.
# ---------------------------------------------------------------------------


class FakeOpenAIResponse:
    def __init__(self, vectors):
        self.data = [type("D", (), {"embedding": v})() for v in vectors]


class FakeOpenAIEmbeddings:
    def __init__(self, dim: int = 1536):
        self.dim = dim
        self.calls: list[dict] = []

    def create(self, input, model):
        # Deterministic vector per input: hash → bytes → floats. Just for tests.
        self.calls.append({"input": list(input), "model": model})
        vectors = []
        for s in input:
            base = hash(s) & 0xFFFF
            vectors.append([float(base % 7) / 7.0] * self.dim)
        return FakeOpenAIResponse(vectors)


class FakeOpenAIClient:
    def __init__(self, dim: int = 1536):
        self.embeddings = FakeOpenAIEmbeddings(dim=dim)


class TestOpenAIEmbedder:
    def test_known_model_pricing(self):
        e = OpenAIEmbedder("text-embedding-3-small")
        assert e.model_id == "text-embedding-3-small"
        assert e.dim == 1536
        assert e.cost_per_1m_tokens == 0.02

    def test_3_large(self):
        e = OpenAIEmbedder("text-embedding-3-large")
        assert e.dim == 3072
        assert e.cost_per_1m_tokens == 0.13

    def test_unknown_model_raises_config_error(self):
        with pytest.raises(MarkcrawlConfigError, match="Unknown OpenAI embedder"):
            OpenAIEmbedder("nonexistent-model")

    def test_embed_empty_returns_empty_without_client(self):
        e = OpenAIEmbedder("text-embedding-3-small")
        assert e.embed([]) == []
        assert e._client is None  # no client initialized

    def test_embed_batches_correctly(self):
        e = OpenAIEmbedder("text-embedding-3-small", batch_size=3)
        e._client = FakeOpenAIClient()
        texts = [f"text-{i}" for i in range(7)]
        result = e.embed(texts)
        # 7 results across 3 batches: [3, 3, 1]
        assert len(result) == 7
        calls = e._client.embeddings.calls
        assert len(calls) == 3
        assert [len(c["input"]) for c in calls] == [3, 3, 1]
        assert all(c["model"] == "text-embedding-3-small" for c in calls)

    def test_embed_returns_dim_correct_vectors(self):
        e = OpenAIEmbedder("text-embedding-3-small", batch_size=10)
        e._client = FakeOpenAIClient(dim=1536)
        result = e.embed(["a", "b"])
        assert len(result) == 2
        assert all(len(v) == 1536 for v in result)

    def test_missing_api_key_raises(self, monkeypatch):
        # Drop OPENAI_API_KEY from env if present; force the client path.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Also stop _load() from reading .env-style fallbacks if any future
        # logic adds them — we assert the error message is helpful.
        e = OpenAIEmbedder("text-embedding-3-small")
        # Patch the OpenAI import so we don't trip the dependency error first.
        with pytest.raises(MarkcrawlConfigError, match="OPENAI_API_KEY"):
            e.embed(["any"])


# ---------------------------------------------------------------------------
# LocalSentenceTransformerEmbedder — fake the SentenceTransformer model.
# ---------------------------------------------------------------------------


class FakeSentenceTransformer:
    def __init__(self, model_id, **kwargs):
        self.model_id = model_id
        self.kwargs = kwargs
        # Encode returns a deterministic ndarray-like.
        import numpy as np
        self._np = np
        self._dim = 1024 if "large" in model_id else 768

    def get_sentence_embedding_dimension(self):
        return self._dim

    def encode(self, texts, batch_size=64, show_progress_bar=False,
               normalize_embeddings=False, convert_to_numpy=True):
        # Stable per-text vector from hash.
        import numpy as np
        out = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, t in enumerate(texts):
            out[i, 0] = (hash(t) & 0xFFFF) / 65536.0
        return out


class TestLocalSentenceTransformerEmbedder:
    def test_known_model_dim_set_eagerly(self):
        e = LocalSentenceTransformerEmbedder("BAAI/bge-large-en-v1.5")
        assert e.dim == 1024
        assert e.cost_per_1m_tokens == 0.0
        assert e._model is None

    def test_unknown_model_dim_inferred_on_load(self, monkeypatch):
        # Monkey-patch the import inside _load() so we don't hit HuggingFace.
        import markcrawl.embedder as emb_mod

        # Replace the import target by injecting a fake SentenceTransformer
        # via sys.modules.
        import sys
        import types
        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = FakeSentenceTransformer
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("some/unknown-model")
        assert e.dim == -1
        e._load()
        assert e.dim == 768  # FakeSentenceTransformer's dim for non-"large" model

    def test_embed_empty_returns_empty_without_load(self):
        e = LocalSentenceTransformerEmbedder("BAAI/bge-large-en-v1.5")
        assert e.embed([]) == []
        assert e._model is None

    def test_embed_returns_dim_correct_vectors(self, monkeypatch):
        import sys
        import types
        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = FakeSentenceTransformer
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("BAAI/bge-large-en-v1.5")
        result = e.embed(["foo", "bar", "baz"])
        assert len(result) == 3
        assert all(len(v) == 1024 for v in result)

    def test_trust_remote_code_for_nomic(self, monkeypatch):
        import sys
        import types
        captured: list[dict] = []

        class CapturingFakeST(FakeSentenceTransformer):
            def __init__(self, model_id, **kwargs):
                captured.append({"model_id": model_id, **kwargs})
                super().__init__(model_id, **kwargs)

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = CapturingFakeST
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("nomic-ai/nomic-embed-text-v1.5")
        e._load()
        assert captured[0]["trust_remote_code"] is True

    def test_no_trust_remote_for_bge(self, monkeypatch):
        import sys
        import types
        captured: list[dict] = []

        class CapturingFakeST(FakeSentenceTransformer):
            def __init__(self, model_id, **kwargs):
                captured.append({"model_id": model_id, **kwargs})
                super().__init__(model_id, **kwargs)

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = CapturingFakeST
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("BAAI/bge-large-en-v1.5")
        e._load()
        assert "trust_remote_code" not in captured[0]

    def test_nomic_applies_search_document_prefix(self, monkeypatch):
        import sys
        import types
        captured_inputs: list[list[str]] = []

        class CapturingFakeST(FakeSentenceTransformer):
            def encode(self, texts, **kwargs):
                captured_inputs.append(list(texts))
                return super().encode(texts, **kwargs)

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = CapturingFakeST
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("nomic-ai/nomic-embed-text-v1.5")
        e.embed(["doc one", "doc two"], kind="document")
        e.embed(["a query"], kind="query")

        assert captured_inputs[0] == ["search_document: doc one", "search_document: doc two"]
        assert captured_inputs[1] == ["search_query: a query"]

    def test_bge_applies_query_prefix_only(self, monkeypatch):
        import sys
        import types
        captured_inputs: list[list[str]] = []

        class CapturingFakeST(FakeSentenceTransformer):
            def encode(self, texts, **kwargs):
                captured_inputs.append(list(texts))
                return super().encode(texts, **kwargs)

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = CapturingFakeST
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("BAAI/bge-large-en-v1.5")
        e.embed(["doc one"], kind="document")
        e.embed(["a query"], kind="query")
        # Document text passed through as-is.
        assert captured_inputs[0] == ["doc one"]
        # Query gets the BGE instruction prefix.
        assert captured_inputs[1] == [
            "Represent this sentence for searching relevant passages: a query"
        ]

    def test_unknown_local_model_no_prefix(self, monkeypatch):
        import sys
        import types
        captured_inputs: list[list[str]] = []

        class CapturingFakeST(FakeSentenceTransformer):
            def encode(self, texts, **kwargs):
                captured_inputs.append(list(texts))
                return super().encode(texts, **kwargs)

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.SentenceTransformer = CapturingFakeST
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        e = LocalSentenceTransformerEmbedder("sentence-transformers/all-MiniLM-L6-v2")
        e.embed(["doc"], kind="document")
        e.embed(["q"], kind="query")
        assert captured_inputs[0] == ["doc"]
        assert captured_inputs[1] == ["q"]


# ---------------------------------------------------------------------------
# make_embedder dispatch
# ---------------------------------------------------------------------------


class TestMakeEmbedder:
    def test_openai_3_small_auto_detected(self):
        e = make_embedder("text-embedding-3-small")
        assert isinstance(e, OpenAIEmbedder)
        assert e.model_id == "text-embedding-3-small"

    def test_openai_3_large_auto_detected(self):
        e = make_embedder("text-embedding-3-large")
        assert isinstance(e, OpenAIEmbedder)

    def test_openai_explicit_prefix(self):
        e = make_embedder("openai:text-embedding-3-small")
        assert isinstance(e, OpenAIEmbedder)
        assert e.model_id == "text-embedding-3-small"

    def test_local_auto_detected_from_hf_id(self):
        e = make_embedder("BAAI/bge-large-en-v1.5")
        assert isinstance(e, LocalSentenceTransformerEmbedder)
        assert e.model_id == "BAAI/bge-large-en-v1.5"

    def test_local_explicit_prefix(self):
        e = make_embedder("local:nomic-ai/nomic-embed-text-v1.5")
        assert isinstance(e, LocalSentenceTransformerEmbedder)
        assert e.model_id == "nomic-ai/nomic-embed-text-v1.5"


class TestPolymorphism:
    def test_both_subclass_embedder_base(self):
        assert issubclass(OpenAIEmbedder, Embedder)
        assert issubclass(LocalSentenceTransformerEmbedder, Embedder)

    def test_both_have_required_attrs(self):
        e1 = OpenAIEmbedder("text-embedding-3-small")
        e2 = LocalSentenceTransformerEmbedder("BAAI/bge-large-en-v1.5")
        for e in (e1, e2):
            assert hasattr(e, "model_id")
            assert hasattr(e, "dim")
            assert hasattr(e, "cost_per_1m_tokens")
            assert callable(e.embed)
