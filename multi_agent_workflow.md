## Multi-Agent Workflow — Google in a Day (Multi-Agent Edition)

### 1. Scope

This document describes how **multiple AI agents** (each with a narrow mandate) collaborate to produce the codebase in this repository. The **running application** is not a multi-agent system: it is a normal multi-threaded Python server. The **multi-agent aspect is the development process**: division of responsibility, prompts, handoffs, and review.

**Initial codebase state**: The repo is a **scaffold**—routes and types line up with the PRD, but crawl, persistence, and search logic are stubs or `NotImplementedError` until agents implement them. Use this document plus [`agents/`](agents/) prompts to drive that work; extend [`verify_system.py`](verify_system.py) as features become real.

### 2. Agent roster and responsibilities

| Agent | Responsibility | Primary artifacts |
|-------|----------------|-------------------|
| **Architect** | End-to-end design, module boundaries, concurrency and back-pressure strategy, alignment with course constraints (stdlib-only core). | [`product_prd.md`](product_prd.md) updates, high-level file map, answers to “search while indexing” design questions. |
| **Crawler engineer** | Frontier, visited set, depth \(k\), fetch/parse, worker pool, bounded queue, rate limiting, job lifecycle (pause/resume/stop, optional queue snapshot). | [`crawler/indexer.py`](crawler/indexer.py) |
| **Index & storage engineer** | Durable visited set, per-letter word index, per-job JSON state, locking for concurrent crawl + search. | [`storage/file_store.py`](storage/file_store.py) |
| **Search engineer** | Tokenization, query resolution (exact + prefix), relevance scoring, pagination, sort modes, triple \((url, origin, depth)\). | [`search/searcher.py`](search/searcher.py) |
| **UI / API engineer** | HTTP server, HTML pages, JSON endpoints, dashboard metrics, long-polling or refresh patterns for status. | [`web/server.py`](web/server.py) |
| **QA / integration engineer** | End-to-end checks, edge cases, verification script maintenance, regression after cross-cutting changes. | [`verify_system.py`](verify_system.py) |

Detailed prompts and I/O contracts for each role live under [`agents/`](agents/).

### 3. Interaction order (typical pass)

```mermaid
flowchart TD
  A[Architect] --> B[Crawler_engineer]
  A --> C[Index_storage_engineer]
  B --> C
  C --> D[Search_engineer]
  B --> E[UI_API_engineer]
  D --> E
  E --> F[QA_engineer]
  F -->|issues| B
  F -->|issues| C
  F -->|issues| D
  F -->|issues| E
```

1. **Architect** locks the PRD-level decisions: stdlib-only HTTP/HTML, bounded queue back-pressure, shared `WordStore` with per-letter locks for live search.
2. **Crawler** and **Index/storage** can proceed in parallel early; crawler depends on storage APIs (`VisitedUrlsStore`, `WordStore`, `CrawlerDataStore`).
3. **Search** consumes `WordStore` read API only (no crawler internals).
4. **UI/API** wires `CrawlerManager` + `Searcher` into the HTTP layer.
5. **QA** runs `verify_system.py` and manual crawl/search scenarios; files bugs back to the owning agent.

### 4. Prompt patterns (summary)

Each agent session used a **system** preamble (role, non-negotiables: no Scrapy/BeautifulSoup/Selenium for core work, thread-safe shared state, explicit back-pressure) and a **user** task (specific file, acceptance criteria, link to PRD section). Agents were instructed to **read existing modules first** and match style, and to **avoid drive-by refactors** outside their slice.

### 5. Decisions and trade-offs

- **Per-letter file locks** instead of a single global index lock: reduces contention versus one big JSON file while keeping a simple on-disk model.
- **Blocking producers on full queue** rather than dropping URLs: preserves crawl completeness at the cost of slower producers when the frontier explodes—acceptable for the MVP scale assumption.
- **Resume via NDJSON queue snapshot on stop** rather than continuous WAL: simpler implementation; hard crash loses pending queue (documented limitation).
- **Search during crawl** accepted **near-real-time** consistency (see PRD §4.1); no snapshot isolation for readers.

### 6. Evaluation and quality gates

- **Automated (scaffold phase)**: `python3 verify_system.py` confirms docs, imports, and stub wiring only.
- **Automated (mature phase)**: extend `verify_system.py` with crawl, storage, search, and API checks; all must pass before a milestone is “done.”
- **Manual**: short crawl against a small site; run search mid-crawl; confirm metrics on the status page once implemented.
- **Cross-agent review**: when one agent changes a shared contract (e.g., `WordStore.add_words` signature), the Architect (or human) confirms crawler and search callers are updated in the same change set.

### 7. Files per agent (descriptions)

See:

- [`agents/architect.md`](agents/architect.md)
- [`agents/crawler_agent.md`](agents/crawler_agent.md)
- [`agents/index_storage_agent.md`](agents/index_storage_agent.md)
- [`agents/search_agent.md`](agents/search_agent.md)
- [`agents/ui_api_agent.md`](agents/ui_api_agent.md)
- [`agents/qa_agent.md`](agents/qa_agent.md)
