## Google in a Day — Multi-Agent Edition

This repository holds **documentation and agent orchestration** for a course-style project: a single-node **Python 3.10+** web crawler with live search. **There is no application implementation here yet**—no `run.py`, packages, or tests—only the specs, workflow, and Cursor-oriented rules you use to build the code later.

---

### What is in this repo

| Item | Purpose |
|------|--------|
| [`product_prd.md`](product_prd.md) | Product requirements: behavior, concurrency, persistence, deliverables. |
| [`AGENTS.md`](AGENTS.md) | **Index for AI assistants:** who owns which area, routing to `agents/*.md`, global rules, planned file map. |
| [`agents/`](agents/) | One markdown file per specialist role: role, inputs/outputs, constraints, copy-paste **prompt stubs**. |
| [`multi_agent_workflow.md`](multi_agent_workflow.md) | How those roles collaborate (order, trade-offs, quality gates). |
| [`recommendation.md`](recommendation.md) | Short note on how a production system might evolve (out of MVP scope). |
| [`.cursor/rules/core-architecture.mdc`](.cursor/rules/core-architecture.mdc) | **Cursor rule** (`alwaysApply`): stdlib-only stack, threading, back-pressure, search-while-indexing, pointers to `AGENTS.md`. |

Functional detail (crawler, search UI, APIs, data files) lives in **`product_prd.md`**, not duplicated here.

---

### Multi-agent architecture (development, not runtime)

The **running program** is intended to be an ordinary multi-threaded Python process. **“Multi-agent” means how you develop it**—several narrow **roles** (architect, crawler, storage, search, web/API, QA), each with its own prompt and scope in [`agents/`](agents/), coordinated as described in [`multi_agent_workflow.md`](multi_agent_workflow.md).

- **[`AGENTS.md`](AGENTS.md)** is the single routing table: which role to adopt for which paths, plus setup/verification commands *once you create those scripts*.
- **`agents/*.md`** holds the deep definitions and **system/user prompt stubs** for Cursor (or other) sessions.
- **`multi_agent_workflow.md`** explains typical handoff order and design trade-offs.

---

### Cursor: rules + `AGENTS.md`

In **Cursor**, two layers work together:

1. **[`.cursor/rules/core-architecture.mdc`](.cursor/rules/core-architecture.mdc)** — Always-on project constraints: no Scrapy/BeautifulSoup/Selenium for core crawl/parse; stdlib HTTP server for MVP; explicit locks and bounded queues; search safe while indexing; follow **`AGENTS.md`** for persona routing.
2. **[`AGENTS.md`](AGENTS.md)** — Session-level map: read the matching **`agents/<role>.md`** for the files you are editing so prompts and constraints stay aligned with the multi-agent split.

Open **`AGENTS.md`** first in a new chat; open a specific **`agents/*.md`** when you focus on one subsystem.

---

### After you add code (reference only)

When you implement the project, the PRD and agent files expect a conventional layout (e.g. `crawler/`, `storage/`, `search/`, `web/`, `utils.py`, `run.py`, `verify_system.py`). Names and responsibilities are summarized in [`AGENTS.md`](AGENTS.md) and detailed in [`product_prd.md`](product_prd.md). Until those files exist, treat the layout as a **target**, not something present in the repo today.
