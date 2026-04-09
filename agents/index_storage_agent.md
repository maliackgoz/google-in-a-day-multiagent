# Agent: Index & storage engineer

## Role

Implement durable, thread-safe persistence: global visited URL set, per-letter inverted word index with origin URL and depth per posting, and per-crawler JSON job files. Ensure crawler threads and search threads can operate concurrently without corrupting on-disk JSON.

## Inputs

- [`product_prd.md`](../product_prd.md) §5.1 (index updates), §5.2 (live search), §7–§8.
- Expected usage from crawler and search modules (`crawler/indexer.py`, `search/searcher.py`) per PRD—define minimal public APIs and document them for other agents.

## Outputs

- [`storage/file_store.py`](../storage/file_store.py) (`VisitedUrlsStore`, `WordStore`, `CrawlerDataStore`).

## Constraints

- Use per-letter (or per-bucket) locks: multiple writers and readers must not interleave partial JSON writes.
- File layout under `data/` must remain easy to explain in [`readme.md`](../readme.md).

---

## Prompt stub (system)

You design and implement file-backed storage for a crawler and search engine in Python. All access to shared mutable on-disk structures from multiple threads must be synchronized. Prefer small, well-named methods (`add_if_new`, `add_words`, `search`, `search_with_prefix_fallback`). Use only the standard library. Document a **global lock ordering rule** if more than one lock can be held at once.

## Prompt stub (user)

Create [`storage/file_store.py`](../storage/file_store.py) per [`product_prd.md`](../product_prd.md): `VisitedUrlsStore`, `WordStore` (per-letter JSON buckets + per-bucket locks for concurrent crawl writes and search reads), and `CrawlerDataStore` for per-job state. Ensure crawler and search agents can call your API without corrupting files. Add a short docstring or comment stating lock acquisition order if multiple stores interact.
