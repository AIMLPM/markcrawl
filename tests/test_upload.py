"""Tests for markcrawl.upload — chunking + embedding + Supabase upload with mocked APIs."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

from markcrawl.upload import _insert_with_retry, generate_embeddings, load_pages, upload

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_jsonl(path: str, pages: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")


SAMPLE_PAGES = [
    {
        "url": "https://example.com/",
        "title": "Home",
        "text": " ".join(["word"] * 100),  # 100 words
    },
    {
        "url": "https://example.com/about",
        "title": "About",
        "text": " ".join(["content"] * 50),  # 50 words
    },
]


# ---------------------------------------------------------------------------
# load_pages
# ---------------------------------------------------------------------------

class TestUploadLoadPages:
    def test_loads_pages(self, tmp_path):
        path = str(tmp_path / "pages.jsonl")
        _write_jsonl(path, SAMPLE_PAGES)

        pages = load_pages(path)
        assert len(pages) == 2
        assert pages[0]["url"] == "https://example.com/"

    def test_skips_empty_lines(self, tmp_path):
        path = str(tmp_path / "pages.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps(SAMPLE_PAGES[0]) + "\n")
            f.write("\n")  # empty line
            f.write(json.dumps(SAMPLE_PAGES[1]) + "\n")

        pages = load_pages(path)
        assert len(pages) == 2


# ---------------------------------------------------------------------------
# generate_embeddings
# ---------------------------------------------------------------------------

class TestGenerateEmbeddings:
    def test_routes_through_factory(self):
        # Since v0.10.1 generate_embeddings is a thin wrapper that builds
        # an Embedder via make_embedder(model). Patch the factory and
        # verify texts/kind reach the embedder.
        with patch("markcrawl.upload.make_embedder") as fake_factory:
            fake_emb = MagicMock()
            fake_emb.embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            fake_factory.return_value = fake_emb
            embeddings = generate_embeddings(
                texts=["hello", "world"],
                model="text-embedding-3-small",
            )
        fake_factory.assert_called_once_with("text-embedding-3-small")
        fake_emb.embed.assert_called_once_with(["hello", "world"], kind="document")
        assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    def test_client_arg_is_ignored_for_backward_compat(self):
        # Old call sites passed an `openai_client` positional — the shim
        # accepts it for compat but doesn't use it.
        with patch("markcrawl.upload.make_embedder") as fake_factory:
            fake_emb = MagicMock()
            fake_emb.embed.return_value = [[0.0]]
            fake_factory.return_value = fake_emb
            generate_embeddings(["text"], client=MagicMock(), model="text-embedding-3-small")
        fake_factory.assert_called_once()


# ---------------------------------------------------------------------------
# upload (integration with mocked OpenAI + Supabase)
# ---------------------------------------------------------------------------

def _make_fake_embedder(dim: int = 1024):
    """Build a MagicMock Embedder that returns deterministic dim-sized
    vectors, matching the v0.10.1 default embedder shape."""
    fake = MagicMock()
    fake.model_id = "fake-test-embedder"
    fake.dim = dim
    fake.cost_per_1m_tokens = 0.0
    fake.embed.side_effect = lambda texts, kind="document": [[0.1] * dim for _ in texts]
    return fake


class TestUpload:
    @patch("markcrawl.upload._get_supabase_client")
    @patch("markcrawl.upload.make_default_embedder")
    def test_uploads_chunked_pages(self, mock_embedder_factory, mock_supabase, tmp_path):
        path = str(tmp_path / "pages.jsonl")
        _write_jsonl(path, SAMPLE_PAGES)

        mock_embedder_factory.return_value = _make_fake_embedder()

        # Mock Supabase
        supabase_client = MagicMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_insert.execute.return_value = None
        mock_table.insert.return_value = mock_insert
        supabase_client.table.return_value = mock_table
        mock_supabase.return_value = supabase_client

        inserted = upload(
            jsonl_path=path,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            table="documents",
            max_words=50,
            overlap_words=10,
        )

        assert inserted > 0
        supabase_client.table.assert_called_with("documents")
        mock_table.insert.assert_called()

    @patch("markcrawl.upload._get_supabase_client")
    @patch("markcrawl.upload.make_default_embedder")
    def test_returns_zero_for_empty_input(self, mock_embedder_factory, mock_supabase, tmp_path):
        path = str(tmp_path / "pages.jsonl")
        _write_jsonl(path, [])

        mock_embedder_factory.return_value = _make_fake_embedder()

        inserted = upload(
            jsonl_path=path,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )

        assert inserted == 0

    @patch("markcrawl.upload._get_supabase_client")
    @patch("markcrawl.upload.make_default_embedder")
    def test_chunks_are_correct_size(self, mock_embedder_factory, mock_supabase, tmp_path):
        # Create a page with exactly 200 words
        pages = [{
            "url": "https://example.com/",
            "title": "Test",
            "text": " ".join([f"word{i}" for i in range(200)]),
        }]
        path = str(tmp_path / "pages.jsonl")
        _write_jsonl(path, pages)

        # Track what gets inserted
        inserted_rows = []
        supabase_client = MagicMock()
        mock_table = MagicMock()
        def capture_insert(batch):
            inserted_rows.extend(batch)
            mock_result = MagicMock()
            mock_result.execute.return_value = None
            return mock_result
        mock_table.insert.side_effect = capture_insert
        supabase_client.table.return_value = mock_table
        mock_supabase.return_value = supabase_client

        mock_embedder_factory.return_value = _make_fake_embedder()

        upload(
            jsonl_path=path,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            max_words=100,
            overlap_words=20,
        )

        # 200 words with max_words=100, overlap=20 → should produce multiple chunks
        assert len(inserted_rows) >= 2
        for row in inserted_rows:
            assert "chunk_text" in row
            assert "embedding" in row
            assert "url" in row
            assert row["url"] == "https://example.com/"

    @patch("markcrawl.upload._get_supabase_client")
    @patch("markcrawl.upload.make_default_embedder")
    def test_metadata_includes_source_file(self, mock_embedder_factory, mock_supabase, tmp_path):
        pages = [{"url": "https://example.com/", "title": "T", "text": " ".join(["w"] * 50), "path": "test.md"}]
        path = str(tmp_path / "pages.jsonl")
        _write_jsonl(path, pages)

        inserted_rows = []
        supabase_client = MagicMock()
        mock_table = MagicMock()
        def capture_insert(batch):
            inserted_rows.extend(batch)
            m = MagicMock()
            m.execute.return_value = None
            return m
        mock_table.insert.side_effect = capture_insert
        supabase_client.table.return_value = mock_table
        mock_supabase.return_value = supabase_client

        mock_embedder_factory.return_value = _make_fake_embedder()

        upload(
            jsonl_path=path,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )

        assert len(inserted_rows) > 0
        assert inserted_rows[0]["metadata"]["source_file"] == "test.md"

    @patch("markcrawl.upload._get_supabase_client")
    @patch("markcrawl.upload.make_embedder")
    def test_explicit_embedding_model_routes_through_factory(
        self, mock_make_embedder, mock_supabase, tmp_path
    ):
        # Caller passes embedding_model="text-embedding-3-small" → upload
        # routes through make_embedder, NOT make_default_embedder.
        pages = [{"url": "u", "title": "t", "text": " ".join(["w"] * 50)}]
        path = str(tmp_path / "pages.jsonl")
        _write_jsonl(path, pages)

        mock_make_embedder.return_value = _make_fake_embedder(dim=1536)

        supabase_client = MagicMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_insert.execute.return_value = None
        mock_table.insert.return_value = mock_insert
        supabase_client.table.return_value = mock_table
        mock_supabase.return_value = supabase_client

        upload(
            jsonl_path=path,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            embedding_model="text-embedding-3-small",
        )
        mock_make_embedder.assert_called_once_with("text-embedding-3-small")


# ---------------------------------------------------------------------------
# _insert_with_retry
# ---------------------------------------------------------------------------

class TestInsertWithRetry:
    @patch("markcrawl.upload.time.sleep")
    def test_succeeds_on_first_attempt(self, mock_sleep):
        supabase = MagicMock()
        mock_execute = MagicMock()
        supabase.table.return_value.insert.return_value.execute = mock_execute

        _insert_with_retry(supabase, "docs", [{"key": "val"}])

        supabase.table.return_value.insert.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("markcrawl.upload.time.sleep")
    def test_retries_on_failure_then_succeeds(self, mock_sleep):
        supabase = MagicMock()
        mock_insert = supabase.table.return_value.insert.return_value
        # Fail twice, succeed on third
        mock_insert.execute.side_effect = [Exception("timeout"), Exception("timeout"), None]

        _insert_with_retry(supabase, "docs", [{"key": "val"}], max_retries=3)

        assert mock_insert.execute.call_count == 3
        assert mock_sleep.call_count == 2  # slept between retries

    @patch("markcrawl.upload.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        supabase = MagicMock()
        mock_insert = supabase.table.return_value.insert.return_value
        mock_insert.execute.side_effect = Exception("permanent failure")

        import pytest
        with pytest.raises(Exception, match="permanent failure"):
            _insert_with_retry(supabase, "docs", [{"key": "val"}], max_retries=3)

        assert mock_insert.execute.call_count == 3
