# AGENTS — Google in a Day (multi-agent)

This file orients Cursor Agent and other AI assistants on **who does what** in this repo. Full role definitions, inputs/outputs, constraints, and copy-paste **prompt stubs** live under [`agents/`](agents/).

## Project overview

Single-node **Python 3.10+** web **crawler** plus **live search** over a file-backed inverted index. Core stack: **stdlib only** for HTTP (`urllib` / `http.client`), HTML (`html.parser`), and the web server (`http.server`). No Scrapy, BeautifulSoup, Selenium, Flask, or Django for MVP crawl/parse/server.

**Implementation is built from scratch** in this repository; paths below are **planned** module boundaries unless files already exist.

Authoritative product detail: [`product_prd.md`](product_prd.md). Collaboration narrative: [`multi_agent_workflow.md`](multi_agent_workflow.md).

## Setup and verification (conventional targets)

| Action | Command (once you add these entry points) |
|--------|-------------------------------------------|
| Run app | `python3 run.py` — use the port you define (e.g. **3600**). |
| Verify | `python3 verify_system.py` (from repo root) |

The app creates a **`data/`** directory at runtime for the index and crawl state. In **this** repository, **`data/` may be committed** so evaluators can inspect crawler output; see [`readme.md`](readme.md). Fresh worktrees still get an empty or populated `data/` as shipped.

## Global rules for any agent

- Prefer **correctness and clear concurrency** over premature scaling.
- **Shared mutable state** (visited set, index, job files): document and enforce **lock or queue discipline**; avoid inconsistent lock ordering across stores.
- **Search while indexing** is required: no global “indexing complete” gate; readers/writers coordinate via storage-layer locking (per PRD §4.1).
- **Tests**: default to **loopback / in-process** HTTP; no external internet dependency unless explicitly agreed.

## Specialist agents (routing)

When work touches the paths in the third column, read the linked **`agents/*.md`** file and adopt that role’s **Role**, **Constraints**, and **prompt stubs** (system + user) in your reasoning and edits.

| Agent | Doc | Primary code / artifacts (create or own) |
|-------|-----|------------------------------------------|
| **Architect** | [`agents/architect.md`](agents/architect.md) | System design, PRD updates, module boundaries, concurrency story — not a single file |
| **Crawler engineer** | [`agents/crawler_agent.md`](agents/crawler_agent.md) | `crawler/indexer.py`, crawler package; uses `storage/file_store.py`, `utils.py` |
| **Index & storage engineer** | [`agents/index_storage_agent.md`](agents/index_storage_agent.md) | `storage/file_store.py`, `data/` layout, [`readme.md`](readme.md) storage description |
| **Search engineer** | [`agents/search_agent.md`](agents/search_agent.md) | `search/searcher.py`; search checks in `verify_system.py` when present |
| **UI / API engineer** | [`agents/ui_api_agent.md`](agents/ui_api_agent.md) | `web/server.py`, `web/__init__.py` |
| **QA / integration engineer** | [`agents/qa_agent.md`](agents/qa_agent.md) | `verify_system.py`, cross-module correctness |

### Shared utilities

URL normalization, tokenization, and HTML text extraction: **`utils.py`** — align with both indexer and searcher (same tokenization rules).

## Delegation hints

- **Design or trade-off questions** (e.g. search during indexing, resume semantics): **Architect** doc first, then implement in the owning module.
- **Crawl frontier, workers, queues, fetch/parse**: **Crawler engineer**; persistence contracts live in **Index & storage** doc.
- **On-disk JSON, locks, visited/word/job stores**: **Index & storage engineer**; do not change `WordStore` public API without updating crawler/search call sites.
- **Query matching, ranking, pagination**: **Search engineer**; keep ranking **deterministic** for a fixed index snapshot.
- **Forms, dashboards, `/api/*` JSON**: **UI / API engineer**; status JSON should match what the UI shows.
- **End-to-end checks, regressions, homework acceptance themes**: **QA / integration engineer**; use a consistent `check(condition, message)` (or equivalent) style in `verify_system.py`.

## File map (quick reference)

| Path | Owner persona (typical) |
|------|-------------------------|
| `crawler/indexer.py` | Crawler engineer |
| `storage/file_store.py` | Index & storage engineer |
| `search/searcher.py` | Search engineer |
| `web/server.py` | UI / API engineer |
| `utils.py` | Crawler + Search (coordinate) |
| `verify_system.py` | QA / integration |
| `product_prd.md` | Architect (updates when requirements change) |

For **system** and **user** prompt text to paste into agent sessions, use the **Prompt stub** sections in each file under [`agents/`](agents/).
