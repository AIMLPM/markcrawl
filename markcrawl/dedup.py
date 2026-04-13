"""Cross-crawl content deduplication using a persistent hash set.

Stores content hashes in a simple line-delimited file so duplicate pages
are detected across multiple crawl runs.  Uses xxHash when available for
speed, falling back to SHA-1.

Usage::

    dedup = PersistentDedup("crawl_output/.content_hashes")
    if dedup.is_duplicate(page_content):
        print("Skipping duplicate")
    else:
        dedup.add(page_content)
    dedup.save()  # Persist to disk
"""
from __future__ import annotations

import os
from typing import Optional, Set

try:
    import xxhash

    def _hash_content(text: str) -> str:
        return xxhash.xxh64(text.encode("utf-8")).hexdigest()
except ImportError:
    import hashlib

    def _hash_content(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()


DEDUP_FILENAME = ".content_hashes"


class PersistentDedup:
    """Persistent content hash set for cross-crawl deduplication.

    Loads existing hashes from disk on init, and saves back on ``save()``.
    New hashes are added in-memory and only persisted when ``save()`` is
    called (typically at the end of a crawl or periodically).
    """

    def __init__(self, path: Optional[str] = None):
        self._path = path
        self._hashes: Set[str] = set()
        self._new_hashes: Set[str] = set()
        if path and os.path.isfile(path):
            self._load()

    def _load(self) -> None:
        """Load hashes from the dedup file."""
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                h = line.strip()
                if h:
                    self._hashes.add(h)

    def is_duplicate(self, content: str) -> bool:
        """Check if content has been seen before (in this or prior crawls)."""
        h = _hash_content(content)
        return h in self._hashes

    def add(self, content: str) -> str:
        """Add content hash to the set. Returns the hash."""
        h = _hash_content(content)
        self._hashes.add(h)
        self._new_hashes.add(h)
        return h

    def check_and_add(self, content: str) -> bool:
        """Check if duplicate, and add if not. Returns True if duplicate."""
        h = _hash_content(content)
        if h in self._hashes:
            return True
        self._hashes.add(h)
        self._new_hashes.add(h)
        return False

    def save(self) -> None:
        """Persist new hashes to disk (append-only for speed)."""
        if not self._path or not self._new_hashes:
            return
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            for h in self._new_hashes:
                f.write(h + "\n")
        self._new_hashes.clear()

    @property
    def size(self) -> int:
        """Number of unique content hashes stored."""
        return len(self._hashes)
