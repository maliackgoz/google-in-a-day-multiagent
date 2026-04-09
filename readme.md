## Google in a Day — Multi-Agent Edition

This repository is set up for a **multi-agent development workflow**: specialized agents implement the crawler, storage, search, and UI **from scratch** against [`product_prd.md`](product_prd.md). The **deliverable docs** ([`multi_agent_workflow.md`](multi_agent_workflow.md), [`agents/`](agents/)) are ready; **runtime behavior** is intentionally incomplete until those agents land code.

### Current scaffold (what works today)

- `python3 run.py` starts a **minimal** HTTP server on port 3600.
- You can submit a crawl form: a **stub** job is created (`status: stub` in logs) — no real fetching or indexing yet.
- **Search** returns empty results until [`search/searcher.py`](search/searcher.py) is implemented.
- [`utils.py`](utils.py) raises `NotImplementedError` until agents implement URL normalization, tokenization, and HTML text extraction.

### Target behavior (per PRD)

When implementation is complete, the site should provide:

- **Crawler** — real jobs (origin URL, depth \(k\), workers, bounded queue / back-pressure, optional rate limit).
- **Crawler Status** — live metrics, logs, pause / resume / stop, **Resume from disk** when a queue snapshot exists.
- **Search** — live queries over the on-disk word index with triples \((url, origin\_url, depth)\) and relevance ordering.

**Search while indexing:** no global “indexing complete” gate; shared `WordStore` with per-letter locks (see [`product_prd.md`](product_prd.md) §4.1).

### Crawler and back-pressure (target)

Worker threads share a **bounded URL queue**; full queues block producers. See [`product_prd.md`](product_prd.md) §FR-4.

### Requirements

- **Python**: 3.10+ (CPython).
- **OS**: macOS or Linux.
- **Dependencies**: Python standard library only for core crawl, parse, storage, and server.

### Quick start

From this directory:

```bash
python3 run.py
```

Open [http://localhost:3600](http://localhost:3600).

### Project layout

| Path | Role |
|------|------|
| `crawler/indexer.py` | **Implement:** `CrawlerJob`, workers, `UrlQueue` (bounded), fetch/parse. **Now:** stub `CrawlerManager` + `CrawlTask`. |
| `storage/file_store.py` | **Implement:** durable visited set, per-letter word index, locks. **Now:** minimal in-memory / no-op stubs. |
| `search/searcher.py` | **Implement:** prefix fallback, relevance, pagination. **Now:** empty `search()` results. |
| `web/server.py` | **Implement:** full dashboard. **Now:** minimal pages + same route names for APIs. |
| `utils.py` | **Implement:** stdlib URL + HTML helpers. **Now:** `NotImplementedError` stubs. |
| `run.py` | Entry point |
| `verify_system.py` | Scaffold checks; extend with crawl/search integration tests as features land |
| `product_prd.md` | PRD for implementers / AI agents |
| `multi_agent_workflow.md` | Agent collaboration narrative |
| `recommendation.md` | Production deployment notes |
| `agents/` | Per-agent role descriptions and prompt stubs |

### Data directory (`data/`)

Created at startup. Gitignored for a fresh clone.

- `visited_urls.data` — normalized visited URLs (one per line).
- `storage/*.data` — inverted lists bucketed by first character of each term.
- `[crawlerId].data` — per-job JSON state and logs.
- `[crawlerId].queue` — NDJSON frontier snapshot written on **stop** for resume.

### Verification

```bash
python3 verify_system.py
```

Validates documentation, `agents/*.md`, module imports, public API symbols, and stub wiring (`create_job`, empty search). **Expand this script** with depth-limited crawl tests, back-pressure, and search-on-index once the implementation exists.

### New GitHub repository

This folder is intended to be self-contained:

```bash
cd google-in-a-day-multiagent
git init
git add .
git commit -m "Initial commit: Multi-Agent edition crawler and search"
```

Then create a remote on GitHub and push.
