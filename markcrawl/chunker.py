"""Split text into chunks for embedding and vector search.

Three strategies are available:

- :func:`chunk_text` — simple word-count splitting with overlap (fast, works
  on any text).
- :func:`chunk_markdown` — section-aware splitting that respects Markdown
  headings, then falls back to paragraph and word boundaries.  Produces
  more coherent chunks for RAG retrieval.
- :func:`chunk_semantic` — embedding-based splitting that detects topic
  boundaries by measuring similarity drops between sentences.  Requires
  ``pip install markcrawl[ml]`` (sentence-transformers).  Falls back to
  :func:`chunk_markdown` when the model is unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Chunk:
    text: str
    index: int
    total: int


# ---------------------------------------------------------------------------
# Word-based chunking (original, simple)
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    max_words: int = 400,
    overlap_words: int = 50,
) -> List[Chunk]:
    """Split *text* into word-based chunks with overlap.

    This is a simple, fast splitter that works on any text.  It does not
    respect semantic boundaries — it may split mid-sentence or mid-code-block.
    For Markdown content, prefer :func:`chunk_markdown`.

    Parameters
    ----------
    text:
        The source text to split.
    max_words:
        Target maximum words per chunk.
    overlap_words:
        Number of words to repeat at the start of each subsequent chunk
        so that context is not lost at boundaries.

    Returns
    -------
    List[Chunk]
        Ordered chunks with their index and the total count.
    """
    words = text.split()
    if not words:
        return []

    if len(words) <= max_words:
        return [Chunk(text=text.strip(), index=0, total=1)]

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        hit_sentence = False
        if end < len(words):
            # Snap to the nearest sentence boundary (search back up to 20% of chunk)
            window = max(max_words // 5, 10)
            adjusted = _find_sentence_boundary(words, end, window=window, min_pos=start + 1)
            if adjusted > start:
                hit_sentence = (adjusted != end)
                end = adjusted
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        # Skip overlap when the split landed on a sentence boundary —
        # the semantic break makes overlap redundant and reduces chunk count.
        start = end if hit_sentence else end - overlap_words

    total = len(chunks)
    return [Chunk(text=c, index=i, total=total) for i, c in enumerate(chunks)]


# ---------------------------------------------------------------------------
# Section-aware Markdown chunking
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)
_SENTENCE_ENDERS = frozenset(".!?")


def _find_sentence_boundary(words: list[str], target: int, window: int = 50, min_pos: int = 1) -> int:
    """Find the nearest sentence-ending word, searching backward from *target*.

    Looks for words ending in ``.``, ``!``, or ``?`` (ignoring trailing
    quotes/brackets).  Returns the split-point index (one past the
    sentence-ending word) so that ``words[:result]`` ends on a complete
    sentence.  Falls back to *target* if no boundary is found within
    *window* words or if the result would be before *min_pos*.
    """
    earliest = max(target - window, min_pos)
    for i in range(target, earliest - 1, -1):
        word = words[i - 1]
        stripped = word.rstrip("\"')]}>")
        if stripped and stripped[-1] in _SENTENCE_ENDERS:
            return i
    return target


_LIST_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s", re.MULTILINE)


def _estimate_adaptive_max_words(text: str, base: int = 400) -> int:
    """Estimate optimal chunk size based on content density.

    Dense technical content (code blocks, many headings, lists) gets
    smaller chunks for more precise retrieval.  Narrative prose gets
    larger chunks for better context preservation.

    Returns an adjusted *max_words* in the range ``[0.75*base, 1.25*base]``.
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)
    total_words = max(len(text.split()), 1)

    # Code density: fraction of lines inside fenced code blocks
    in_code = False
    code_lines = 0
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines += 1
    code_ratio = code_lines / total_lines

    # Heading density: headings per 100 words
    heading_count = len(_HEADING_RE.findall(text))
    heading_density = heading_count / (total_words / 100) if total_words >= 100 else heading_count

    # List density: fraction of lines that are list items
    list_lines = len(_LIST_RE.findall(text))
    list_ratio = list_lines / total_lines

    # Density score: higher → more technical → smaller chunks
    # Amplify each signal so that moderately dense content is detected
    density_score = (
        min(code_ratio * 2.0, 1.0) * 0.4
        + min(heading_density / 2.0, 1.0) * 0.3
        + min(list_ratio * 1.5, 1.0) * 0.3
    )

    # Map [0, 1] → multiplier [1.25, 0.65]
    multiplier = 1.25 - density_score * 0.6
    return max(int(base * multiplier), 100)


def _extract_section_heading(text: str) -> str:
    """Return the first heading line from *text*, or ``""``."""
    m = _HEADING_RE.match(text)
    if not m:
        return ""
    nl = text.find("\n", m.start())
    return text[:nl].strip() if nl >= 0 else text.strip()


def _heading_positions(text: str) -> List[int]:
    """Return start offsets of heading lines that are NOT inside a fenced code block.

    A line like ``# foo`` inside a ``` fenced block is a code comment
    (e.g. Python), not a Markdown heading — splitting on it shreds the
    code example.
    """
    positions: List[int] = []
    in_fence = False
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            offset += len(line)
            continue
        if not in_fence and _HEADING_RE.match(line):
            positions.append(offset)
        offset += len(line)
    return positions


def _split_on_headings(text: str) -> List[str]:
    """Split Markdown text on heading boundaries (# through ######).

    Each returned section starts with its heading line (except possibly
    the first section if the text begins without a heading).  Headings
    inside fenced code blocks are ignored.
    """
    positions = _heading_positions(text)
    if not positions:
        return [text]

    sections: List[str] = []
    # Content before the first heading (if any)
    if positions[0] > 0:
        preamble = text[: positions[0]].strip()
        if preamble:
            sections.append(preamble)

    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        section = text[pos:end].strip()
        if section:
            sections.append(section)

    return sections


def _split_on_paragraphs(text: str) -> List[str]:
    """Split text on blank-line paragraph boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _word_count(text: str) -> int:
    return len(text.split())


def chunk_markdown(
    text: str,
    max_words: int = 400,
    overlap_words: int = 50,
    page_title: str | None = None,
    adaptive: bool = False,
) -> List[Chunk]:
    """Split Markdown text into semantically coherent chunks.

    Splitting strategy (in order of preference):

    1. **Headings** — split on ``#`` through ``######`` boundaries so each
       section stays together.
    2. **Paragraphs** — if a section exceeds *max_words*, split on blank
       lines (paragraph boundaries).
    3. **Word count** — if a single paragraph still exceeds *max_words*,
       fall back to :func:`chunk_text` word-count splitting with overlap.

    When *adaptive* is ``True``, *max_words* is automatically adjusted
    based on content density: code-heavy and reference-style content
    gets smaller chunks, narrative prose gets larger chunks.

    When a section is split into multiple chunks, the section heading is
    carried forward to each subsequent chunk so that retrieval context is
    preserved.

    Parameters
    ----------
    text:
        Markdown source text.
    max_words:
        Target maximum words per chunk.
    overlap_words:
        Overlap words used when falling back to word-count splitting.
    page_title:
        Optional page title to prepend to each chunk for embedding context.

    Returns
    -------
    List[Chunk]
        Ordered chunks with their index and the total count.
    """
    text = text.strip()
    if not text:
        return []

    if adaptive:
        max_words = _estimate_adaptive_max_words(text, base=max_words)

    if _word_count(text) <= max_words:
        chunk_text_val = text
        if page_title and not chunk_text_val.lstrip().startswith("# "):
            chunk_text_val = f"[Page: {page_title}]\n\n{chunk_text_val}"
        return [Chunk(text=chunk_text_val, index=0, total=1)]

    # Step 1: split on headings
    sections = _split_on_headings(text)

    # Step 2: for oversized sections, split on paragraphs.
    # Carry the section heading forward to each split fragment.
    fragments: List[str] = []
    for section in sections:
        if _word_count(section) <= max_words:
            fragments.append(section)
        else:
            heading_line = _extract_section_heading(section)
            paragraphs = _split_on_paragraphs(section)
            current = ""
            first_flushed = False
            for para in paragraphs:
                if current and _word_count(current + "\n\n" + para) > max_words:
                    if first_flushed and heading_line and not current.lstrip().startswith("#"):
                        current = heading_line + "\n\n" + current
                    fragments.append(current)
                    first_flushed = True
                    current = para
                else:
                    current = (current + "\n\n" + para) if current else para
            if current:
                if first_flushed and heading_line and not current.lstrip().startswith("#"):
                    current = heading_line + "\n\n" + current
                fragments.append(current)

    # Step 3: for oversized fragments, fall back to word-count splitting
    final_chunks: List[str] = []
    for fragment in fragments:
        if _word_count(fragment) <= max_words:
            final_chunks.append(fragment)
        else:
            heading_line = _extract_section_heading(fragment)
            sub_chunks = chunk_text(fragment, max_words=max_words, overlap_words=overlap_words)
            for i, sc in enumerate(sub_chunks):
                sc_text = sc.text
                if i > 0 and heading_line and not sc_text.lstrip().startswith("#"):
                    sc_text = heading_line + "\n\n" + sc_text
                final_chunks.append(sc_text)

    # Prepend page title context if provided — but skip chunks that already
    # start with an H1 (redundant, and it inflates similarity on generic
    # page-topic queries, pushing the intro chunk above more specific ones).
    if page_title:
        prefix = f"[Page: {page_title}]\n\n"
        final_chunks = [
            c if c.lstrip().startswith("# ") else prefix + c
            for c in final_chunks
        ]

    total = len(final_chunks)
    return [Chunk(text=c, index=i, total=total) for i, c in enumerate(final_chunks)]


# ---------------------------------------------------------------------------
# Semantic chunking (embedding-based boundary detection)
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using punctuation + capital letter heuristic."""
    # Also split on blank lines (paragraph boundaries)
    paragraphs = re.split(r"\n\s*\n", text)
    sentences: List[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        parts = _SENTENCE_SPLIT_RE.split(para)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences


def chunk_semantic(
    text: str,
    max_words: int = 400,
    min_words: int = 50,
    similarity_threshold: float = 0.5,
    page_title: Optional[str] = None,
    model_name: str = "all-MiniLM-L6-v2",
) -> List[Chunk]:
    """Split text by detecting topic boundaries via embedding similarity.

    Uses Projected Similarity Chunking: encode each sentence, compute cosine
    similarity between consecutive sentences, and split where similarity
    drops below the threshold.  Chunks are then merged or split to respect
    the word count limits.

    Falls back to :func:`chunk_markdown` when sentence-transformers is not
    installed.

    Parameters
    ----------
    text:
        Source text to split.
    max_words:
        Maximum words per chunk.
    min_words:
        Minimum words per chunk — short chunks are merged with the previous.
    similarity_threshold:
        Cosine similarity below which a split is created (0–1).  Lower values
        create fewer, larger chunks.
    page_title:
        Optional page title to prepend to each chunk.
    model_name:
        Sentence-transformers model name.

    Returns
    -------
    List[Chunk]
        Ordered chunks with index and total count.
    """
    text = text.strip()
    if not text:
        return []

    if _word_count(text) <= max_words:
        chunk_text_val = text
        if page_title and not chunk_text_val.lstrip().startswith("# "):
            chunk_text_val = f"[Page: {page_title}]\n\n{chunk_text_val}"
        return [Chunk(text=chunk_text_val, index=0, total=1)]

    try:
        import numpy as np
        import sentence_transformers  # noqa: F401
    except ImportError:
        return chunk_markdown(text, max_words=max_words, page_title=page_title)

    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return chunk_markdown(text, max_words=max_words, page_title=page_title)

    # Encode all sentences
    model = _get_sentence_model(model_name)
    embeddings = model.encode(sentences, show_progress_bar=False)

    # Compute cosine similarity between consecutive sentences
    similarities = []
    for i in range(len(embeddings) - 1):
        a = embeddings[i]
        b = embeddings[i + 1]
        cos_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
        similarities.append(cos_sim)

    # Find split points: where similarity drops below threshold
    split_indices = []
    for i, sim in enumerate(similarities):
        if sim < similarity_threshold:
            split_indices.append(i + 1)  # Split after sentence i

    # Build chunks from split points
    raw_chunks: List[str] = []
    prev = 0
    for idx in split_indices:
        chunk = " ".join(sentences[prev:idx])
        if chunk.strip():
            raw_chunks.append(chunk.strip())
        prev = idx
    # Last chunk
    if prev < len(sentences):
        chunk = " ".join(sentences[prev:])
        if chunk.strip():
            raw_chunks.append(chunk.strip())

    # Merge small chunks with the previous one
    merged: List[str] = []
    for chunk in raw_chunks:
        if merged and _word_count(merged[-1]) + _word_count(chunk) <= max_words:
            if _word_count(chunk) < min_words:
                merged[-1] = merged[-1] + "\n\n" + chunk
                continue
        merged.append(chunk)

    # Split oversized chunks using word-count fallback
    final_chunks: List[str] = []
    for chunk in merged:
        if _word_count(chunk) <= max_words:
            final_chunks.append(chunk)
        else:
            sub = chunk_text(chunk, max_words=max_words, overlap_words=50)
            final_chunks.extend(sc.text for sc in sub)

    if page_title:
        prefix = f"[Page: {page_title}]\n\n"
        final_chunks = [prefix + c for c in final_chunks]

    total = len(final_chunks)
    return [Chunk(text=c, index=i, total=total) for i, c in enumerate(final_chunks)]


# Lazy-loaded sentence model cache
_sentence_model_cache: dict = {}


def _get_sentence_model(model_name: str):
    """Get or load a sentence-transformers model (cached)."""
    if model_name not in _sentence_model_cache:
        from sentence_transformers import SentenceTransformer
        _sentence_model_cache[model_name] = SentenceTransformer(model_name)
    return _sentence_model_cache[model_name]
