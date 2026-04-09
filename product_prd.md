## Google in a Day — Multi-Agent Edition — Product Requirements Document (PRD)

### 0. Audience and build process

**Primary readers**: Specialized AI agents (and human reviewers) collaborating to implement and evolve this codebase.

**Important distinction**: The **runtime system** is a conventional single-process Python application with threads. **Multi-agent** refers to the **development workflow** (separate agent roles, prompts, and handoffs documented in [`multi_agent_workflow.md`](multi_agent_workflow.md) and [`agents/`](agents/)). Agents MUST still produce code that satisfies the functional and non-functional requirements below.

**Repository state**: The codebase may start as a **scaffold** (importable modules, stub `CrawlerManager` / `Searcher`, minimal UI). Agents implement real crawl, storage, and search until `verify_system.py` and manual tests match the PRD.

**Product Name**: Google in a Day (Multi-Agent Edition)  
**Version**: 1.0 (MVP)  
**Document Owner**: System Architecture Team  
**Primary Stakeholders**: Engineering, Product Management, DevOps, QA  

### 1. Overview

**Goal**:  
Build a functional, small-scale web crawler and real-time search engine that can:

- Crawl the web starting from one or more origin URLs.
- Maintain a live index of discovered pages (persisted incrementally to disk under appropriate locking, so search reflects new pages as they are written).
- Allow users to query the index in real time while crawling is ongoing.
- Provide operational visibility via a simple UI or CLI dashboard.

The initial implementation is a single-node Python application focused on correctness, clarity, and extensibility rather than internet-scale performance.

### 2. Objectives & Non-Goals

- **Objectives**
  - **Functional Web Crawler**: Recursive crawler from configured origin URL up to maximum depth \(k\).
  - **Real-Time Search Engine**: Query interface usable while the crawler is running.
  - **Operational Visibility**: Dashboard showing real-time system state and metrics.
  - **Resumable Crawling**: Persistence to support resuming a crawl after interruption without full restart.
  - **Python & Standard Library Focus**: HTTP fetching, HTML parsing, concurrency using stdlib (`urllib`, `http.client`, `html.parser`, `threading`, `queue`, `logging`, etc.).

- **Non-Goals (for this MVP)**
  - Internet-wide crawling; advanced ranking (PageRank, ML); heavy NLP; distributed multi-node design; headless browser rendering.

### 3. Users & Use Cases

- **UC-1**: Configure and start a crawl (origin, depth \(k\), workers, queue capacity, limits).
- **UC-2**: Monitor progress (queue depth, back-pressure, workers).
- **UC-3**: Search while crawling; results update as the index grows.
- **UC-4**: Pause / resume / stop; optional resume from disk after stop.
- **UC-5**: Results expose \((relevant\_url, origin\_url, depth)\).

### 4. High-Level Architecture

Three subsystems:

- **Indexer (Crawler)** — frontier, visited set, bounded queue, back-pressure, fetch/parse, feed index.
- **Searcher** — thread-safe reads from on-disk inverted lists (per-letter files + locks); relevance heuristic; triples + optional metadata.
- **Dashboard / API** — web UI and JSON endpoints for control and metrics.

Cross-cutting: threading primitives for all shared state; file-based persistence for visited set, index, and crawler job state.

### 4.1 Search while the indexer is active (design)

**MVP (implemented)**:

- Crawler workers and HTTP search handlers share a `WordStore` backed by per-letter JSON files.
- Each letter bucket is protected by a lock so concurrent **writes** (from multiple workers) and **reads** (search) do not corrupt files.
- After each document update, committed data is visible to the next search once the store completes its write for that letter. There is no global “indexing complete” barrier.

**Future evolution** (if search and ingest must scale further or reduce lock contention):

- **Segmented index**: Append-only segment files per time window; background compaction merges segments; search merges top results across segments (log-structured merge tree pattern).
- **Snapshot / replica**: Periodic consistent snapshot for read-only query nodes; ingest continues on primary (trade-off: slightly stale reads vs higher query throughput).
- **Pipeline decouple**: Fetch → parse → index enqueue over a durable queue so search serving can restart independently of crawl workers (still single-machine friendly with SQLite or embedded queue).

### 5. Functional Requirements

#### 5.1 Indexer (Crawler)

- **FR-1**: Accept origin URL(s) and maximum depth \(k\) (hops from origin; depth 0 = origin).
- **FR-2**: Recursively discover links via HTML parsing until depth \(k\), no more URLs, or global page limit.
- **FR-3**: Thread-safe visited set of normalized URLs; no duplicate fetches.
- **FR-4**: Back-pressure — bounded URL queue; producers block (or defined policy) at capacity; expose queue depth and back-pressure status.
- **FR-5**: HTTP via `urllib` / `http.client`; parse via `html.parser`. **No** Scrapy, BeautifulSoup, or Selenium for core crawl/parse.
- **FR-6**: Robust to HTTP errors, timeouts, bad HTML, non-HTML (log and skip).
- **FR-7**: Extract URL, origin, depth, title, body text; pass to index store under correct locking.

#### 5.2 Searcher

- **FR-8**: CLI and/or HTTP search usable during active crawl.
- **FR-9**: Results as triples \((relevant\_url, origin\_url, depth)\) ordered by relevance (default).
- **FR-10**: Shared thread-safe index; near-real-time visibility of committed writes.
- **FR-11**: Deterministic relevance: tokenize (ignore terms shorter than two characters); exact key then longest prefix (minimum length three); per-URL aggregation with frequency and depth-aware scoring; optional sort by relevance, frequency, or depth.

#### 5.3 Dashboard

- **FR-12**: Web or CLI dashboard for live metrics.
- **FR-13**: At minimum: pages processed, URLs discovered, queue depth vs max, back-pressure / worker activity.
- **FR-14**: JSON status API per job where web UI is used.

#### 5.4 Persistence & resumability (bonus)

- **FR-15**: Persist visited set, index, per-job state; optional NDJSON queue snapshot on stop.
- **FR-16**: Resume from disk when queue snapshot exists; hard crash may lose frontier but retains visited + index.

### 6. Non-Functional Requirements

- **NFR-1**: Configurable concurrency; reasonable performance at hundreds–thousands of pages.
- **NFR-2**: Long runs survive typical web failures; structured logging.
- **NFR-3**: All shared structures accessed in a thread-safe way.
- **NFR-4**: Modular layout: crawler, storage, search, web, utils.
- **NFR-5**: Observable lifecycle events.
- **NFR-6**: Python 3.10+ on macOS/Linux; no non-stdlib dependencies required for core behavior.

### 7. Data Model

(URL records, document records, inverted index sketch, metrics state — same semantics as the reference implementation: normalized URL, `origin_url`, `depth`, word postings with frequencies.)

### 8. Concurrency Model

- Worker threads consume a bounded `queue.Queue`.
- Visited set and metrics updated under locks.
- Index: per-bucket locks; search reads and crawler writes coordinate on those locks (MVP correctness over maximal read throughput).

### 9. Configuration

Origin URLs, \(k\), workers, queue size, page limits, timeouts, optional rate limit, data directory, dashboard port.

### 10. Security & Compliance (MVP)

Optional robots.txt; configurable host scope; no secret headers by default.

### 11. Testing & Validation

Unit tests for normalization, parsing, index operations where applicable; integration against a local dummy site; `verify_system.py` for automated checks.

### 12. Deliverables

- **D-1**: Working Python codebase (`crawler/`, `storage/`, `search/`, `web/`, `run.py`, etc.).
- **D-2**: [`readme.md`](readme.md) — setup, run, layout.
- **D-3**: This [`product_prd.md`](product_prd.md).
- **D-4**: [`recommendation.md`](recommendation.md) — production evolution (short).
- **D-5**: [`multi_agent_workflow.md`](multi_agent_workflow.md) — agents, prompts, interactions, evaluation.
- **D-6**: [`agents/`](agents/) — one description file per agent role used in the workflow.

### 13. Future Enhancements (Out of Scope for MVP)

Distributed crawl, advanced ranking, rich NLP, JS rendering, multi-tenant auth, full cloud runbooks (beyond `recommendation.md`).
