"""Read crawl output and upload chunked + embedded rows to Supabase."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .chunker import chunk_markdown, chunk_text
from .embedder import DEFAULT_EMBEDDER_SPEC, Embedder, make_default_embedder, make_embedder
from .exceptions import MarkcrawlConfigError, MarkcrawlDependencyError
from .utils import load_pages

logger = logging.getLogger(__name__)

# Embedding defaults — kept as module constants for callers that import them.
# Since v0.10.1 the default is the local mxbai-embed-large-v1 (zero API
# cost). Pass ``embedding_model="text-embedding-3-small"`` (or any other
# spec :func:`markcrawl.embedder.make_embedder` accepts) to override.
DEFAULT_EMBEDDING_MODEL = DEFAULT_EMBEDDER_SPEC
EMBED_BATCH_SIZE = 64  # used by the legacy generate_embeddings shim only


def _get_supabase_client(url: str, key: str) -> Any:
    try:
        from supabase import create_client  # noqa: F811
    except ImportError:
        raise MarkcrawlDependencyError(
            "The 'supabase' package is required for uploading.\n"
            "Install it with:  pip install supabase"
        )
    return create_client(url, key)


def generate_embeddings(
    texts: List[str],
    client: Any = None,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> List[List[float]]:
    """Generate embeddings for a batch of texts.

    Routes through :func:`markcrawl.embedder.make_embedder` so the same
    spec strings used by ``upload(embedding_model=...)`` work here. The
    ``client`` arg is accepted for backward compatibility but ignored
    — embedders manage their own clients/models.
    """
    embedder = make_embedder(model)
    return embedder.embed(texts, kind="document")


def upload(
    jsonl_path: str,
    supabase_url: str,
    supabase_key: str,
    table: str = "documents",
    max_words: int = 400,
    overlap_words: int = 50,
    embedding_model: Optional[str] = None,
    embedder: Optional[Embedder] = None,
    show_progress: bool = False,
    batch_size: int = 50,
) -> int:
    """Chunk, embed, and upload crawl output to Supabase.

    By default uses the local mxbai-embed-large-v1 embedder (zero API
    cost, ships in the base install since v0.10.1). Override with one
    of:

    - ``embedder=...`` — pass any :class:`Embedder` instance.
    - ``embedding_model="text-embedding-3-small"`` — string spec routed
      through :func:`markcrawl.embedder.make_embedder` (e.g.
      ``"text-embedding-3-large"``, ``"BAAI/bge-large-en-v1.5"``,
      ``"local:nomic-ai/nomic-embed-text-v1.5"``).
    - ``MARKCRAWL_EMBEDDER`` env var (read by
      :func:`make_default_embedder` when neither kwarg is set).

    Returns the number of rows inserted.
    """
    if not supabase_url:
        raise MarkcrawlConfigError("SUPABASE_URL is required")
    if not supabase_key:
        raise MarkcrawlConfigError("SUPABASE_KEY is required")
    if embedder is not None and embedding_model is not None:
        raise MarkcrawlConfigError("pass either embedder or embedding_model, not both")

    pages = load_pages(jsonl_path)
    if not pages:
        logger.warning("No pages found in %s", jsonl_path)
        return 0

    if embedder is None:
        embedder = make_embedder(embedding_model) if embedding_model else make_default_embedder()
    supabase = _get_supabase_client(supabase_url, supabase_key)

    # Build all rows with chunked text
    rows: List[Dict[str, Any]] = []
    for page in pages:
        # Use section-aware chunking for Markdown, word-count for plain text
        page_text = page.get("text", "")
        page_title = page.get("title", "") or None
        if page.get("path", "").endswith(".md") or page_text.startswith("#"):
            chunks = chunk_markdown(page_text, max_words=max_words, overlap_words=overlap_words, page_title=page_title, adaptive=True)
        else:
            chunks = chunk_text(page_text, max_words=max_words, overlap_words=overlap_words)
        for chunk in chunks:
            rows.append(
                {
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "chunk_text": chunk.text,
                    "chunk_index": chunk.index,
                    "chunk_total": chunk.total,
                    "metadata": {
                        "source_file": page.get("path", ""),
                    },
                }
            )

    if not rows:
        logger.warning("No chunks produced from %s", jsonl_path)
        return 0

    if show_progress:
        print(f"[info] {len(pages)} page(s) -> {len(rows)} chunk(s)")
        print(f"[info] generating embeddings with {embedder.model_id} ...")

    # Generate embeddings for all chunks
    texts = [r["chunk_text"] for r in rows]
    embeddings = embedder.embed(texts, kind="document")

    for row, embedding in zip(rows, embeddings):
        row["embedding"] = embedding

    # Insert in batches with retry
    inserted = 0
    total_batches = (len(rows) + batch_size - 1) // batch_size
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        try:
            _insert_with_retry(supabase, table, batch)
        except Exception as exc:
            logger.error(
                "Failed at batch %d/%d (%d rows inserted so far): %s",
                i // batch_size + 1, total_batches, inserted, exc,
            )
            raise
        inserted += len(batch)
        if show_progress:
            print(f"[prog] inserted {inserted}/{len(rows)} row(s)")

    return inserted


_RETRY_MAX = 3
_RETRY_BASE_DELAY = 1.0


def _insert_with_retry(supabase, table: str, batch: list, max_retries: int = _RETRY_MAX) -> None:
    """Insert a batch into Supabase with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            supabase.table(table).insert(batch).execute()
            return
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Insert failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, max_retries, delay, exc,
            )
            time.sleep(delay)
