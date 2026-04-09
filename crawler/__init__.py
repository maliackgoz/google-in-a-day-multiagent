"""Crawler package: multi-job web crawler engine (scaffold — extend per PRD)."""

from .indexer import CrawlerManager, CrawlTask, UrlQueue  # noqa: F401

__all__ = [
    "CrawlerManager",
    "CrawlTask",
    "UrlQueue",
]
