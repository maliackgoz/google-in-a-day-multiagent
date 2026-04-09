## Google in a Day — Multi-Agent Edition

Single-process **Python 3.10+** web crawler with a **live file-backed inverted index** and a small **HTTP dashboard**. Core stack uses only the **standard library** (HTTP client/server, `html.parser`, threading, `queue`).

Multi-agent **development** roles and prompts live under [`AGENTS.md`](AGENTS.md) and [`agents/`](agents/).

---

### Quick start

```bash
python3 run.py
```

Defaults: listen on **http://127.0.0.1:3600**, store data under `./data`. Override with environment variables:

- `PORT` — HTTP port (default `3600`)
- `DATA_DIR` — persistence root (default `data`)

Verification (loopback tests, no public internet):

```bash
python3 verify_system.py
```

---

### Layout

| Path | Role |
|------|------|
| `utils.py` | URL normalization, HTML text/links, shared `tokenize` |
| `storage/file_store.py` | `VisitedUrlsStore`, `WordStore` (per-letter JSON + locks), `CrawlerDataStore` |
| `crawler/indexer.py` | Bounded frontier queue, workers, pause/resume/stop, optional NDJSON queue snapshot |
| `search/searcher.py` | Query resolution and deterministic ranking over `WordStore` |
| `web/server.py` | `http.server` UI + `/api/*` JSON |
| `run.py` | App entrypoint |
| `verify_system.py` | QA checks and local integration scenarios |
| `data/` | Created at runtime (gitignored): `visited_urls.json`, `index/*.json`, `jobs/*.json`, optional `*_queue.ndjson` |

---

### HTTP routes (stable)

| Route | Purpose |
|--------|---------|
| `GET /` | HTML dashboard and forms |
| `POST /crawl` | Form POST to start a crawl |
| `GET /api/crawler-dashboard` | Aggregate queue depth, capacity, back-pressure, active job IDs |
| `GET /api/status/<job_id>` | Per-job metrics and queue snapshot path |
| `GET /api/search?q=...&limit=&offset=&sort=` | JSON search (`sort`: `relevance`, `frequency`, `depth`) |
| `POST /api/crawl` | JSON body: `origin_urls`, `max_depth`, `workers`, `queue_size`, `page_limit`, `same_host_only`, `resume`, optional `job_id` |
| `POST /api/pause/<job_id>` | Pause workers |
| `POST /api/resume/<job_id>` | Resume |
| `POST /api/stop/<job_id>` | Stop; writes NDJSON queue snapshot when pending work remains |

Requirements and concurrency rules are defined in [`product_prd.md`](product_prd.md). Workflow between roles is in [`multi_agent_workflow.md`](multi_agent_workflow.md).
