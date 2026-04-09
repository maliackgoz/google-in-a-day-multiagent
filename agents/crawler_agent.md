# Agent: Crawler engineer

## Role

Implement the crawl frontier: URL normalization, depth limit \(k\), visited coordination, worker pool, bounded task queue with blocking back-pressure, HTTP fetch with timeouts and robust error handling, HTML link extraction, and job controls (pause, resume, stop, optional queue snapshot on stop).

## Inputs

- [`product_prd.md`](../product_prd.md) §5.1, §8.
- Storage APIs from [`storage/file_store.py`](../storage/file_store.py) (`VisitedUrlsStore`, `WordStore`, `CrawlerDataStore`) once defined—coordinate signatures with the Index & storage agent if both are active.
- [`utils.py`](../utils.py) for `normalize_url`, `extract_title_and_content`, `tokenize` (implement or consume as those modules appear).

## Outputs

- [`crawler/indexer.py`](../crawler/indexer.py) and package `__init__.py` if needed.

## Constraints

- Use `html.parser` (or equivalent stdlib) for link extraction; no BeautifulSoup.
- Producers must respect queue capacity (block or defined policy per PRD).
- Never fetch the same normalized URL twice (coordinate with `VisitedUrlsStore`).

---

## Prompt stub (system)

You are implementing a multi-threaded web crawler in Python using only the standard library. You must use bounded queues so that enqueue operations block when full (back-pressure). Fetch with `urllib.request` or `http.client`. Parse HTML with `html.parser`. Handle SSL and HTTP errors gracefully. Establish clear, readable structure in `crawler/indexer.py` and match conventions you set elsewhere in the repo as it grows.

## Prompt stub (user)

From [`product_prd.md`](../product_prd.md) §5.1 and §8, design and implement `crawler/indexer.py`: bounded `UrlQueue` with blocking producers; worker pool; depth \(k\) per PRD; integration with `VisitedUrlsStore` and `WordStore` for dedup and indexing; job controls (pause, resume, stop). On **stop**, persist pending tasks in NDJSON form compatible with resume. Expose queue depth and capacity for the dashboard. Do not change `WordStore` public API without updating all call sites.
