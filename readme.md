# Google in a Day — Multi-Agent Edition

## What this is

This repository is a small **web crawler** plus **live search** over a file-backed inverted index, implemented as a single **Python 3.10+** process with threads. The HTTP UI and JSON API let you start crawls, watch queue depth and back-pressure, and **search while indexing**—new pages show up in search as they are written.

The **runtime** is a normal application (not “multiple AI agents” talking to each other at run time). **Multi-agent** here means **how the project was built**: separate developer roles, prompts, and handoffs documented in [`AGENTS.md`](AGENTS.md) and [`agents/`](agents/), plus [`multi_agent_workflow.md`](multi_agent_workflow.md).

### How this repo relates to “Google in a Day”

An earlier **“google-in-a-day”** version was implemented in **another repository**, largely through **vibe coding** (iterative, conversational development). **This repository is different:** it targets the same kind of product, but the work is organized around **multi-agent development**—clear ownership per area (crawler, storage, search, web, QA), shared constraints in the PRD, and prompts that keep implementations aligned.

### Data on disk (`data/`)

Crawl state and index files live under **`data/`** (visited URLs, per-letter index JSON, job metadata, optional queue snapshots). **`data/` is kept in version control on purpose** so evaluators can inspect **real crawler results** without having to run long crawls themselves. In a typical production setup you would gitignore this folder and generate data only on the machine that runs the crawler.

---

## Quick start

```bash
python3 run.py
```

By default the server listens at **http://127.0.0.1:3600** and uses **`./data`** for persistence. You can override:

| Variable   | Meaning        | Default   |
|-----------|----------------|-----------|
| `PORT`    | HTTP port      | `3600`    |
| `DATA_DIR`| Data directory | `data`    |

Run the automated checks (loopback / in-process; **no dependency on the public internet**):

```bash
python3 verify_system.py
```

---

## Project layout

| Path | Role |
|------|------|
| `utils.py` | URL normalization, HTML text and links, shared `tokenize` |
| `storage/file_store.py` | `VisitedUrlsStore`, `WordStore` (per-letter JSON + locks), `CrawlerDataStore` |
| `crawler/indexer.py` | Bounded frontier queue, worker pool, pause / resume / stop, optional NDJSON queue snapshot |
| `search/searcher.py` | Query handling and deterministic ranking over `WordStore` |
| `web/server.py` | `http.server` UI and `/api/*` JSON |
| `run.py` | Application entrypoint |
| `verify_system.py` | Integration and regression checks |
| `data/` | Runtime crawl and index data (tracked here for evaluation) |

---

## HTTP API and pages (overview)

| Route | Purpose |
|--------|---------|
| `GET /` | Home |
| `GET /crawl` | Crawler UI (start jobs, dashboard, saved crawls, live log) |
| `POST /crawl` | Form POST to start a crawl |
| `GET /search` | Search UI |
| `GET /api/crawler-dashboard` | Aggregate queue depth, capacity, back-pressure, active job IDs |
| `GET /api/status/<job_id>` | Per-job status, metrics, queue info |
| `GET /api/saved-jobs` | List saved job summaries on disk |
| `GET /api/crawler-events?since=&limit=&job=&filter=` | Crawl event log for the live panel |
| `GET /api/search?q=...&limit=&offset=&sort=` | JSON search (`sort`: `relevance`, `frequency`, `depth`) |
| `POST /api/crawl` | JSON: `origin_urls`, `max_depth`, `workers`, `queue_size`, `page_limit`, `same_host_only`, `resume`, optional `job_id` |
| `POST /api/pause/<job_id>` | Pause workers |
| `POST /api/resume/<job_id>` | Resume |
| `POST /api/stop/<job_id>` | Stop; may write NDJSON queue snapshot for resume |
| `POST /api/resume-saved` | Resume a stopped job from disk (`job_id` in JSON body) |
| `POST /api/clear-data` | Clear index, jobs, visited set (destructive) |

**Requirements and concurrency** are specified in [`product_prd.md`](product_prd.md). **Multi-agent workflow and design decisions** are in [`multi_agent_workflow.md`](multi_agent_workflow.md). **Production-style next steps** are sketched in [`recommendation.md`](recommendation.md).
