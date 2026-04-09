"""Persistent storage for visited URLs, word index, and crawler job metadata.

**Scaffold:** In-memory or no-op behavior where noted. Replace with thread-safe,
on-disk persistence per [`product_prd.md`](product_prd.md) and
[`agents/index_storage_agent.md`](agents/index_storage_agent.md).
"""

from __future__ import annotations

import os
import threading
from collections import Counter
from typing import Any, Optional


class VisitedUrlsStore:
    """Thread-safe in-memory stand-in until real persistence is implemented."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()
        self._urls: set[str] = set()

    def add_if_new(self, url: str) -> bool:
        with self._lock:
            if url in self._urls:
                return False
            self._urls.add(url)
            return True

    def __len__(self) -> int:
        with self._lock:
            return len(self._urls)

    def save(self) -> None:
        """Persist visited set to ``visited_urls.data`` (no-op in scaffold)."""
        os.makedirs(self._data_dir, exist_ok=True)
        # Agents: write one normalized URL per line per product_prd.md §FR-15.

    def clear(self) -> None:
        with self._lock:
            self._urls.clear()


class WordStore:
    """Inverted index stand-in. Implement per-letter JSON files and locking."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()
        os.makedirs(os.path.join(data_dir, "storage"), exist_ok=True)

    def add_words(
        self,
        word_counts: Counter[str],
        url: str,
        origin_url: str,
        depth: int,
    ) -> None:
        raise NotImplementedError(
            "Implement add_words with per-bucket locks per product_prd.md §FR-10."
        )

    def search(self, word: str) -> list[dict[str, Any]]:
        return []

    def search_with_prefix_fallback(self, word: str) -> tuple[list[dict[str, Any]], Optional[str]]:
        return [], None

    def total_words(self) -> int:
        return 0

    def clear(self) -> None:
        """No-op until on-disk letter files exist."""


class CrawlerDataStore:
    """Per-job JSON state (scaffold: no files written)."""

    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self._lock = threading.Lock()
        self._memory: dict[str, dict[str, Any]] = {}

    def save(self, crawler_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._memory[crawler_id] = dict(data)

    def read(self, crawler_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            d = self._memory.get(crawler_id)
            return dict(d) if d else None

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(d) for d in self._memory.values()]

    def clear_all(self) -> list[str]:
        with self._lock:
            self._memory.clear()
        return []
