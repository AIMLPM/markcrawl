"""Link prioritization using a lightweight scoring heuristic.

Inspired by the "sleeping bandits" approach: score discovered URLs by
predicted content yield based on URL structure and crawl history, then
prioritize high-yield links in the crawl queue.

This is NOT full RL — it uses a simple multi-armed bandit with feature-based
scoring.  Each URL path segment gets a running average of content yield
(word count of extracted content), and new URLs are scored by their path
prefix match to high-yield segments.

Usage::

    scorer = LinkScorer()
    # After processing a page, record its yield
    scorer.record(url, word_count=len(content.split()))
    # When adding new URLs to the queue, sort by predicted yield
    scored_urls = scorer.score_batch(new_urls)
    # scored_urls is a list of (url, score) sorted by score desc
"""
from __future__ import annotations

import urllib.parse as up
from collections import defaultdict
from typing import Dict, List, Tuple


class LinkScorer:
    """Score URLs by predicted content yield using path-segment statistics.

    Tracks the average content yield (word count) per first path segment.
    New URLs are scored based on their path prefix match to segments with
    known yields.  Unknown segments get a neutral score.
    """

    def __init__(self):
        # segment → (total_words, page_count)
        self._stats: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
        # Bonus signals
        self._depth_penalty: float = 0.05  # Per-depth penalty
        self._doc_bonus_patterns = frozenset({
            "docs", "doc", "api", "reference", "guide", "tutorial",
            "manual", "blog", "post", "article", "learn", "getting-started",
        })

    def record(self, url: str, word_count: int) -> None:
        """Record the content yield of a crawled page."""
        segment = self._first_segment(url)
        total, count = self._stats[segment]
        self._stats[segment] = (total + word_count, count + 1)

    def score(self, url: str) -> float:
        """Predict the content yield score for an uncrawled URL.

        Higher = more likely to have good content.
        """
        segment = self._first_segment(url)
        path = up.urlsplit(url).path.strip("/")
        depth = len(path.split("/")) if path else 0

        # Base score from segment history
        total, count = self._stats[segment]
        if count > 0:
            avg_yield = total / count
        else:
            avg_yield = 200.0  # Neutral prior for unknown segments

        # Depth penalty — very deep URLs are less likely to be valuable
        depth_factor = max(0.3, 1.0 - depth * self._depth_penalty)

        # Doc-like path bonus
        doc_bonus = 1.0
        segments = path.lower().split("/")
        for seg in segments:
            if seg in self._doc_bonus_patterns:
                doc_bonus = 1.3
                break

        # File extension penalty — non-HTML file paths score lower
        if path and "." in path.split("/")[-1]:
            ext = path.rsplit(".", 1)[-1].lower()
            if ext not in ("html", "htm", "php", "asp", "aspx", "jsp", ""):
                return avg_yield * 0.1  # Likely non-content

        return avg_yield * depth_factor * doc_bonus

    def score_batch(self, urls: List[str]) -> List[Tuple[str, float]]:
        """Score a batch of URLs and return sorted by score (descending)."""
        scored = [(url, self.score(url)) for url in urls]
        scored.sort(key=lambda x: -x[1])
        return scored

    def prioritize(self, urls: List[str]) -> List[str]:
        """Return URLs sorted by predicted yield (best first)."""
        return [url for url, _ in self.score_batch(urls)]

    @staticmethod
    def _first_segment(url: str) -> str:
        """Extract the first path segment for bucketing."""
        path = up.urlsplit(url).path.strip("/")
        if not path:
            return "/"
        return "/" + path.split("/")[0]

    @property
    def stats_summary(self) -> Dict[str, Dict[str, float]]:
        """Return human-readable stats per segment."""
        result = {}
        for segment, (total, count) in sorted(self._stats.items()):
            if count > 0:
                result[segment] = {
                    "avg_words": round(total / count, 1),
                    "pages": count,
                    "total_words": total,
                }
        return result
