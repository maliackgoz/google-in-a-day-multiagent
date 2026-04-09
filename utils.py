"""Shared text-processing utilities for crawl indexing and search.

**Scaffold:** All functions raise `NotImplementedError`. Implement them (stdlib only:
`html.parser`, `urllib.parse`, `re`) per [`product_prd.md`](product_prd.md) and
[`agents/crawler_agent.md`](agents/crawler_agent.md) / [`agents/search_agent.md`](agents/search_agent.md).
"""

from __future__ import annotations

from typing import Tuple


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication (scheme/host case, fragment, trailing slash)."""
    raise NotImplementedError(
        "Implement normalize_url per product_prd.md §FR-3 (visited set consistency)."
    )


def tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens for indexing and search."""
    raise NotImplementedError(
        "Implement tokenize per product_prd.md §FR-7 / §FR-11 (match indexer and searcher)."
    )


def extract_title_and_content(html: str) -> Tuple[str, str]:
    """Return ``(title, body_text)`` from raw HTML using ``html.parser``."""
    raise NotImplementedError(
        "Implement extract_title_and_content with html.parser per product_prd.md §FR-5 / §FR-7."
    )
