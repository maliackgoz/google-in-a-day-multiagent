from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from storage.file_store import WordStore
from utils import tokenize

SortBy = Literal["relevance", "frequency", "depth"]


@dataclass(frozen=True)
class SearchHit:
    url: str
    origin_url: str
    depth: int
    relevance_score: float
    total_frequency: int


class Searcher:
    """Deterministic ranking; same tokenization as indexer via utils.tokenize."""

    def __init__(self, word_store: WordStore) -> None:
        self._words = word_store

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
        sort_by: SortBy = "relevance",
    ) -> list[SearchHit]:
        terms = tokenize(query)
        if not terms:
            return []

        per_term: list[dict[str, dict[str, Any]]] = []
        for t in terms:
            postings = self._words.read_term_postings_for_search(t)
            per_term.append(postings)

        urls = set(per_term[0].keys())
        for m in per_term[1:]:
            urls &= set(m.keys())
        if not urls:
            return []

        hits: list[SearchHit] = []
        for u in urls:
            total_freq = 0
            max_depth = 0
            origin_url = ""
            for m in per_term:
                meta = m[u]
                total_freq += int(meta["freq"])
                max_depth = max(max_depth, int(meta["depth"]))
                origin_url = str(meta["origin_url"])
            depth_for_score = max_depth
            relevance = self._score(total_freq, depth_for_score)
            hits.append(
                SearchHit(
                    url=u,
                    origin_url=origin_url,
                    depth=depth_for_score,
                    relevance_score=relevance,
                    total_frequency=total_freq,
                )
            )

        if sort_by == "relevance":
            hits.sort(
                key=lambda h: (-h.relevance_score, -h.total_frequency, h.depth, h.url)
            )
        elif sort_by == "frequency":
            hits.sort(
                key=lambda h: (-h.total_frequency, h.depth, h.url)
            )
        else:
            hits.sort(key=lambda h: (h.depth, -h.relevance_score, h.url))

        return hits[offset : offset + limit]

    @staticmethod
    def _score(total_freq: int, depth: int) -> float:
        return float(total_freq) / (1.0 + float(depth))
