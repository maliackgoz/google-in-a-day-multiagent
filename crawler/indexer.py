"""Crawler: frontier, workers, depth limit, back-pressure.

**Scaffold:** `CrawlerManager` wires storage and exposes the API shape expected by
[`web/server.py`](../web/server.py). Crawl execution is not implemented — replace this
module per [`product_prd.md`](../product_prd.md) and [`agents/crawler_agent.md`](../agents/crawler_agent.md).
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from storage.file_store import CrawlerDataStore, VisitedUrlsStore, WordStore


@dataclass(frozen=True)
class CrawlTask:
    """One URL scheduled for fetch (depth relative to job origin)."""

    url: str
    origin_url: str
    depth: int


class UrlQueue:
    """Bounded URL queue with back-pressure (scaffold: API only).

    Implement with ``queue.Queue`` per product_prd.md §FR-4.
    """

    def __init__(self, maxsize: int = 0) -> None:
        self._maxsize = max(0, maxsize)

    @property
    def maxsize(self) -> int:
        return self._maxsize

    def qsize(self) -> int:
        raise NotImplementedError

    def is_at_capacity(self) -> bool:
        raise NotImplementedError


class CrawlerManager:
    """Coordinates jobs and shared storage (scaffold: no real crawls)."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        os.makedirs(os.path.join(data_dir, "storage"), exist_ok=True)

        self.visited_store = VisitedUrlsStore(data_dir)
        self.word_store = WordStore(data_dir)
        self.crawler_store = CrawlerDataStore(data_dir)

        self._lock = threading.Lock()
        self._stub_jobs: dict[str, dict] = {}

    def create_job(
        self,
        origin_url: str,
        max_depth: int = 2,
        max_workers: int = 4,
        max_queue_size: int = 1000,
        max_pages: Optional[int] = 500,
        hit_rate: float = 0.0,
        http_timeout: float = 10.0,
    ) -> str:
        """Register a placeholder job. Real implementation starts worker threads."""
        cid = f"{int(time.time())}_{uuid.uuid4().hex[:10]}"
        record = {
            "id": cid,
            "origin_url": origin_url,
            "max_depth": max_depth,
            "max_workers": max_workers,
            "queue_capacity": max_queue_size,
            "max_pages": max_pages,
            "hit_rate": hit_rate,
            "http_timeout": http_timeout,
            "status": "stub",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "pages_processed": 0,
            "urls_discovered": 0,
            "logs": [
                {
                    "timestamp": int(time.time()),
                    "message": "Scaffold: implement CrawlerJob / workers per product_prd.md §5.1.",
                }
            ],
        }
        with self._lock:
            self._stub_jobs[cid] = record
        self.crawler_store.save(cid, record)
        return cid

    def get_job_status(self, crawler_id: str) -> Optional[dict]:
        with self._lock:
            live = self._stub_jobs.get(crawler_id)
        if live:
            return dict(live)
        return self.crawler_store.read(crawler_id)

    def list_jobs(self) -> list[dict]:
        with self._lock:
            merged = {cid: dict(d) for cid, d in self._stub_jobs.items()}
        for d in self.crawler_store.list_all():
            cid = d.get("id", "")
            if cid and cid not in merged:
                merged[cid] = dict(d)
        return sorted(merged.values(), key=lambda x: x.get("created_at", 0), reverse=True)

    def stop_job(self, crawler_id: str) -> bool:
        return False

    def pause_job(self, crawler_id: str) -> bool:
        return False

    def resume_job(self, crawler_id: str) -> bool:
        return False

    def resume_job_from_disk(self, crawler_id: str) -> bool:
        return False

    def get_statistics(self) -> dict:
        jobs = self.list_jobs()
        active = sum(1 for j in jobs if j.get("status") in ("running", "paused"))
        total_pages = sum(j.get("pages_processed", 0) for j in jobs)
        return {
            "total_crawlers": len(jobs),
            "active_crawlers": active,
            "total_visited_urls": len(self.visited_store),
            "total_pages_processed": total_pages,
            "total_words_indexed": self.word_store.total_words(),
        }

    def clear_data(self) -> dict:
        with self._lock:
            self._stub_jobs.clear()
        removed = self.crawler_store.clear_all()
        self.visited_store.clear()
        self.word_store.clear()
        return {"cleared": True, "files_removed": removed}

    def shutdown(self) -> None:
        try:
            self.visited_store.save()
        except Exception:
            pass


__all__ = [
    "CrawlTask",
    "CrawlerManager",
    "UrlQueue",
]
