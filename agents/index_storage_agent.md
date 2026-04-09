# Agent: Index & storage engineer

## Role

Implement durable, thread-safe persistence: global visited URL set, per-letter inverted word index with origin URL and depth per posting, and per-crawler JSON job files. Ensure crawler threads and search threads can operate concurrently without corrupting on-disk JSON.

## Inputs

- [`product_prd.md`](../product_prd.md) §5.1 (index updates), §5.2 (live search), §7–§8.
- Call patterns from [`crawler/indexer.py`](../crawler/indexer.py) and [`search/searcher.py`](../search/searcher.py).

## Outputs

- [`storage/file_store.py`](../storage/file_store.py) (`VisitedUrlsStore`, `WordStore`, `CrawlerDataStore`).

## Constraints

- Use per-letter (or per-bucket) locks: multiple writers and readers must not interleave partial JSON writes.
- File layout under `data/` must remain easy to explain in [`readme.md`](../readme.md).

---

## Prompt stub (system)

You maintain file-backed storage for a crawler and search engine in Python. All access to shared mutable on-disk structures from multiple threads must be synchronized. Prefer small, well-named methods (`add_if_new`, `add_words`, `search`, `search_with_prefix_fallback`). Use only the standard library.

## Prompt stub (user)

Audit [`storage/file_store.py`](../storage/file_store.py) for deadlock risk between `WordStore` letter locks and `VisitedUrlsStore`. Propose the minimal fix if two locks are ever taken in inconsistent order. Add a one-paragraph comment in code or docstring explaining the lock ordering rule.
