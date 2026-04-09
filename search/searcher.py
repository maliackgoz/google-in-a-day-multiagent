"""Search over the word index (triples: url, origin_url, depth).

**Scaffold:** Returns empty results. Implement against ``WordStore`` per
[`product_prd.md`](../product_prd.md) §5.2 and [`agents/search_agent.md`](../agents/search_agent.md).
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Literal

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if TYPE_CHECKING:
    from storage.file_store import WordStore

SortBy = Literal["relevance", "frequency", "depth"]


class Searcher:
    """Query engine (scaffold)."""

    def __init__(self, word_store: "WordStore") -> None:
        self._word_store = word_store

    def search(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        sort_by: SortBy = "relevance",
    ) -> dict:
        """Return paginated results; implement per product_prd.md §FR-8–FR-11."""
        if sort_by not in ("relevance", "frequency", "depth"):
            sort_by = "relevance"
        return {
            "results": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0,
            "sort_by": sort_by,
        }
