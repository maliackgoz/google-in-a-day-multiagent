# Agent: Crawler engineer

## Role

Implement the crawl frontier: URL normalization, depth limit \(k\), visited coordination, worker pool, bounded task queue with blocking back-pressure, HTTP fetch with timeouts and robust error handling, HTML link extraction, and job controls (pause, resume, stop, optional queue snapshot on stop).

## Inputs

- [`product_prd.md`](../product_prd.md) §5.1, §8.
- [`storage/file_store.py`](../storage/file_store.py) APIs for visited set, word index, crawler state.
- [`utils.py`](../utils.py) for `normalize_url`, `extract_title_and_content`, `tokenize`.

## Outputs

- [`crawler/indexer.py`](../crawler/indexer.py) and package `__init__.py` if needed.

## Constraints

- Use `html.parser` (or equivalent stdlib) for link extraction; no BeautifulSoup.
- Producers must respect queue capacity (block or defined policy per PRD).
- Never fetch the same normalized URL twice (coordinate with `VisitedUrlsStore`).

---

## Prompt stub (system)

You are implementing a multi-threaded web crawler in Python using only the standard library. You must use bounded queues so that enqueue operations block when full (back-pressure). Fetch with `urllib.request` or `http.client`. Parse HTML with `html.parser`. Handle SSL errors gracefully where the existing code does. Match the style of the current [`crawler/indexer.py`](../crawler/indexer.py).

## Prompt stub (user)

Implement or adjust `CrawlerJob` so that: (1) max depth \(k\) matches PRD definition; (2) `UrlQueue` exposes current depth and max capacity for the dashboard; (3) on **stop**, pending tasks are persisted in NDJSON form compatible with resume. Do not change `WordStore` public API without listing call sites.
