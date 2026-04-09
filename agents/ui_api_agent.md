# Agent: UI / API engineer

## Role

Expose the system over HTTP: crawler form, job status pages with live metrics, search UI, and JSON endpoints for automation. Wire the crawler control surface and `Searcher` from handlers; keep HTML accessible without a front-end build step.

## Inputs

- [`product_prd.md`](../product_prd.md) §5.3.
- [`crawler/indexer.py`](../crawler/indexer.py) control and metrics surface (as implemented).
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

Implement [`web/server.py`](../web/server.py) per [`product_prd.md`](../product_prd.md) §5.3: HTML pages and `/api/...` routes wired to the crawler manager and `Searcher`. Add `/api/crawler-dashboard` (or equivalent) returning aggregate queue depth and back-pressure flags for active jobs; keep per-job routes such as `/api/status/<id>` consistent with the UI. Document route names in code or readme so clients stay stable.
