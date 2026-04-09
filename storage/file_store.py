"""
Thread-safe file stores for crawl + search.

Lock ordering (when multiple stores are used in one flow):
  1. VisitedUrlsStore — acquire only around try_add / persistence; release before I/O fetch.
  2. WordStore — acquire per-letter locks in alphabetical order of bucket id when touching
     multiple buckets in one call (add_document sorts buckets).

Do not hold a WordStore letter lock while acquiring VisitedUrlsStore.lock.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any


def _bucket_id_for_word(word: str) -> str:
    if not word:
        return "_"
    c = word[0].lower()
    if c.isalpha():
        return c
    if c.isdigit():
        return c
    return "_"


class VisitedUrlsStore:
    """Persistent normalized URL set with process-wide lock."""

    def __init__(self, data_dir: str) -> None:
        self._path = os.path.join(data_dir, "visited_urls.json")
        self._lock = threading.Lock()
        os.makedirs(data_dir, exist_ok=True)
        if not os.path.isfile(self._path):
            self._write_urls(set())

    def _read_urls(self) -> set[str]:
        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("urls", []))

    def _write_urls(self, urls: set[str]) -> None:
        tmp = self._path + ".tmp"
        payload = {"urls": sorted(urls)}
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=0)
        os.replace(tmp, self._path)

    def try_add(self, url: str) -> bool:
        """Return True if url was newly added; False if already visited."""
        with self._lock:
            urls = self._read_urls()
            if url in urls:
                return False
            urls.add(url)
            self._write_urls(urls)
            return True

    def __contains__(self, url: str) -> bool:
        with self._lock:
            return url in self._read_urls()

    def reset_empty(self) -> None:
        """Replace persisted set with an empty one (e.g. after wiping data/)."""
        with self._lock:
            self._write_urls(set())


class WordStore:
    """
    Per-letter JSON buckets under data/index/<letter>.json.
    Each bucket: { word: { url: {origin_url, depth, freq} } }.
    """

    def __init__(self, data_dir: str) -> None:
        self._index_dir = os.path.join(data_dir, "index")
        os.makedirs(self._index_dir, exist_ok=True)
        self._letter_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _lock_for_letter(self, letter: str) -> threading.Lock:
        with self._locks_guard:
            if letter not in self._letter_locks:
                self._letter_locks[letter] = threading.Lock()
            return self._letter_locks[letter]

    def _bucket_path(self, letter: str) -> str:
        safe = letter if len(letter) == 1 else "_"
        return os.path.join(self._index_dir, f"{safe}.json")

    def _load_bucket(self, letter: str) -> dict[str, Any]:
        path = self._bucket_path(letter)
        if not os.path.isfile(path):
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_bucket(self, letter: str, data: dict[str, Any]) -> None:
        path = self._bucket_path(letter)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=0, sort_keys=True)
        os.replace(tmp, path)

    def add_document(
        self,
        url: str,
        origin_url: str,
        depth: int,
        word_counts: dict[str, int],
    ) -> None:
        """Merge word frequencies for this URL; thread-safe; multi-bucket order is sorted."""
        by_letter: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for word, freq in word_counts.items():
            if freq <= 0:
                continue
            letter = _bucket_id_for_word(word)
            by_letter.setdefault(letter, {}).setdefault(word, {})[url] = {
                "origin_url": origin_url,
                "depth": depth,
                "freq": int(freq),
            }

        for letter in sorted(by_letter.keys()):
            with self._lock_for_letter(letter):
                bucket = self._load_bucket(letter)
                for word, url_map in by_letter[letter].items():
                    bucket.setdefault(word, {})
                    for u, meta in url_map.items():
                        if u in bucket[word]:
                            prev = bucket[word][u]
                            bucket[word][u] = {
                                "origin_url": meta["origin_url"],
                                "depth": min(int(prev["depth"]), int(meta["depth"])),
                                "freq": int(prev["freq"]) + int(meta["freq"]),
                            }
                        else:
                            bucket[word][u] = dict(meta)
                self._save_bucket(letter, bucket)

    def resolve_term(self, term: str) -> dict[str, dict[str, Any]]:
        """
        Exact key in bucket, else longest indexed key k such that term.startswith(k)
        and len(k) >= 3. Returns {url: {origin_url, depth, freq}}.
        """
        if not term:
            return {}
        letter = _bucket_id_for_word(term)
        with self._lock_for_letter(letter):
            bucket = self._load_bucket(letter)
            if term in bucket:
                return dict(bucket[term])
            candidates = [k for k in bucket if term.startswith(k) and len(k) >= 3]
            if not candidates:
                return {}
            best = max(candidates, key=len)
            return dict(bucket[best])

    def read_term_postings_for_search(self, term: str) -> dict[str, dict[str, Any]]:
        """Alias for resolve_term; separate name for search layer clarity."""
        return self.resolve_term(term)


class CrawlerDataStore:
    """Per-job JSON under data/jobs/<job_id>.json."""

    def __init__(self, data_dir: str) -> None:
        self._jobs_dir = os.path.join(data_dir, "jobs")
        os.makedirs(self._jobs_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in job_id)
        return os.path.join(self._jobs_dir, f"{safe}.json")

    def read(self, job_id: str) -> dict[str, Any] | None:
        p = self._path(job_id)
        if not os.path.isfile(p):
            return None
        with self._lock:
            with open(p, encoding="utf-8") as f:
                return json.load(f)

    def write(self, job_id: str, state: dict[str, Any]) -> None:
        p = self._path(job_id)
        with self._lock:
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=0, sort_keys=True)
            os.replace(tmp, p)

    def merge_patch(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        p = self._path(job_id)
        with self._lock:
            cur: dict[str, Any] = {}
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as f:
                    cur = json.load(f)
            cur.update(patch)
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cur, f, indent=0, sort_keys=True)
            os.replace(tmp, p)
            return cur
