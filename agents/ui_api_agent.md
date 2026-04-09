# Agent: UI / API engineer

## Role

Expose the system over HTTP: crawler form, job status pages with live metrics, search UI, and JSON endpoints for automation. Wire `CrawlerManager` and `Searcher` from the handler; keep HTML accessible without a front-end build step.

## Inputs

- [`product_prd.md`](../product_prd.md) §5.3.
- [`crawler/indexer.py`](../crawler/indexer.py) control and metrics surface.
- [`search/searcher.py`](../search/searcher.py) result shape.

## Outputs

- [`web/server.py`](../web/server.py), [`web/__init__.py`](../web/__init__.py).

## Constraints

- Use `http.server` or stdlib equivalents; no Flask/Django required for MVP.
- Status JSON should match what the dashboard displays (queue depth, back-pressure, workers).

---

## Prompt stub (system)

You build a minimal web UI using Python’s standard library HTTP server. Pages should be readable, with clear forms for crawl parameters and a search box. Implement JSON APIs under `/api/...` for status and search. Avoid introducing non-stdlib dependencies.

## Prompt stub (user)

Add or adjust an endpoint (e.g. `/api/crawler-dashboard`) that returns aggregate queue depth and back-pressure flags for all active jobs. Update the Crawler home page to poll or long-poll this endpoint without breaking existing `/api/status/<id>` clients.
