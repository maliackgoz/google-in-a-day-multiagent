"""Web server for Google in a Day (Multi-Agent Edition).

**Scaffold:** Minimal UI and JSON routes so ``run.py`` starts. Agents replace/expand
per [`product_prd.md`](../product_prd.md) §5.3 and [`agents/ui_api_agent.md`](../agents/ui_api_agent.md).

Routes preserved for compatibility with future full implementation:
  ``/``, ``/status/<id>``, ``/search``, ``/api/*``, POST crawl controls.
"""

from __future__ import annotations

import html as html_mod
import http.server
import json
import logging
import os
import sys
import threading
import time
from typing import TYPE_CHECKING, Any
from urllib import parse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if TYPE_CHECKING:
    from crawler.indexer import CrawlerManager
    from search.searcher import Searcher

logger = logging.getLogger(__name__)

_CSS = """\
body{font-family:system-ui,sans-serif;max-width:52rem;margin:0 auto;padding:1.25rem;line-height:1.5;color:#222}
a{color:#1a56db} nav{margin:1rem 0;display:flex;gap:1rem;flex-wrap:wrap}
.scaffold{background:#fff3cd;border:1px solid #ffc107;padding:.75rem 1rem;border-radius:6px;margin-bottom:1.25rem}
form label{display:block;margin-top:.5rem;font-weight:600;font-size:.85rem}
input{width:100%;max-width:28rem;padding:.4rem .5rem;margin-top:.2rem}
button{margin-top:.75rem;padding:.5rem 1rem;cursor:pointer}
table{border-collapse:collapse;width:100%;margin-top:.5rem}
th,td{border:1px solid #ddd;padding:.4rem .5rem;text-align:left;font-size:.9rem}
th{background:#f5f5f5}
.log{font-family:ui-monospace,monospace;font-size:.8rem;background:#1e1e1e;color:#eee;padding:.75rem;border-radius:6px;max-height:16rem;overflow:auto}
"""


def _layout(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>{html_mod.escape(title)}</title><style>{_CSS}</style></head><body>
<nav><a href="/">Crawler</a><a href="/search">Search</a></nav>
{body}</body></html>"""


def _crawler_page(jobs: list[dict], stats: dict) -> str:
    rows = ""
    for j in jobs[:25]:
        cid = html_mod.escape(str(j.get("id", "")))
        st = html_mod.escape(str(j.get("status", "")))
        ou = html_mod.escape(str(j.get("origin_url", "")))
        rows += f"<tr><td><a href='/status/{cid}'>{cid}</a></td><td>{st}</td><td>{ou}</td></tr>"
    if not rows:
        rows = "<tr><td colspan='3'>No jobs yet.</td></tr>"
    body = f"""<h1>Crawler — Google in a Day (Multi-Agent)</h1>
<div class="scaffold"><strong>Scaffold mode.</strong> Crawl jobs are registered but workers are not
implemented yet. See <code>product_prd.md</code> and <code>agents/crawler_agent.md</code>.</div>
<h2>Start a job</h2>
<form method="post" action="/">
<label>Origin URL<input name="origin_url" type="url" placeholder="https://example.com" required></label>
<label>Max depth <input name="max_depth" type="number" value="2" min="0"></label>
<label>Workers <input name="max_workers" type="number" value="4" min="1"></label>
<label>Queue capacity <input name="queue_capacity" type="number" value="1000" min="1"></label>
<label>Max pages <input name="max_pages" type="number" value="500" min="1"></label>
<label>Hit rate (0=unlimited) <input name="hit_rate" type="number" value="0" step="0.1" min="0"></label>
<button type="submit">Crawl</button>
</form>
<h2>Statistics</h2>
<p>Crawlers: {stats.get("total_crawlers", 0)} · Active: {stats.get("active_crawlers", 0)}
· Visited (memory): {stats.get("total_visited_urls", 0)} · Pages processed: {stats.get("total_pages_processed", 0)}
· Words indexed: {stats.get("total_words_indexed", 0)}</p>
<form method="post" action="/clear" style="margin-top:1rem"><button type="submit" class="danger">Clear all data</button></form>
<h2>Recent jobs</h2>
<table><thead><tr><th>ID</th><th>Status</th><th>Origin</th></tr></thead><tbody>{rows}</tbody></table>"""
    return _layout("Crawler", body)


def _status_page(cid: str, data: dict) -> str:
    logs = data.get("logs") or []
    log_html = ""
    for e in logs[-80:]:
        msg = html_mod.escape(str(e.get("message", "")))
        log_html += f"<div class='log-entry'>{msg}</div>"
    if not log_html:
        log_html = "<div class='log-entry'>(no logs)</div>"
    st = html_mod.escape(str(data.get("status", "")))
    body = f"""<h1>Status: {html_mod.escape(cid)}</h1>
<p><a href="/">&larr; Crawler home</a></p>
<p>Status: <strong>{st}</strong></p>
<div class="scaffold">Pause/resume/stop buttons appear once <code>CrawlerJob</code> is implemented.</div>
<h2>Logs</h2>
<div class="log">{log_html}</div>"""
    return _layout(f"Status {cid}", body)


def _search_page(q: str, res: dict) -> str:
    total = int(res.get("total", 0))
    results = res.get("results") or []
    out = ""
    for r in results:
        u = html_mod.escape(str(r.get("url", "")))
        ou = html_mod.escape(str(r.get("origin_url", "")))
        dep = r.get("depth", "")
        out += f"<div><strong>{u}</strong><br><small>{ou} depth {dep}</small></div><hr>"
    if not out and q:
        out = "<p>No results (scaffold search returns empty).</p>"
    elif not q:
        out = "<p>Enter a query.</p>"
    body = f"""<h1>Search</h1>
<div class="scaffold">Scaffold: <code>Searcher.search</code> returns empty results until implemented.</div>
<form method="get" action="/search"><label>Query<input name="q" value="{html_mod.escape(q)}"></label>
<button type="submit">Search</button></form>
<p>{total} total</p>{out}"""
    return _layout("Search", body)


class CrawlerHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple,
        handler: type,
        manager: "CrawlerManager",
        searcher: "Searcher",
    ) -> None:
        super().__init__(address, handler)
        self.manager = manager
        self.searcher = searcher
        self.shutdown_event = threading.Event()


class CrawlerHandler(http.server.BaseHTTPRequestHandler):
    server: CrawlerHTTPServer  # type: ignore[assignment]

    def do_GET(self) -> None:
        parsed = parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse.parse_qs(parsed.query)

        if path == "/":
            self._respond_html(_crawler_page(self.server.manager.list_jobs(), self.server.manager.get_statistics()))
        elif path.startswith("/status/"):
            cid = path[len("/status/") :]
            data = self.server.manager.get_job_status(cid)
            if data is None:
                self.send_error(404, "Crawler not found")
            else:
                self._respond_html(_status_page(cid, data))
        elif path == "/search":
            q = qs.get("q", [""])[0].strip()
            page = int(qs.get("page", ["1"])[0])
            pp = int(qs.get("per_page", ["10"])[0])
            sort = qs.get("sort", ["relevance"])[0]
            if sort not in ("relevance", "frequency", "depth"):
                sort = "relevance"
            res = (
                self.server.searcher.search(q, page=page, per_page=pp, sort_by=sort)
                if q
                else {
                    "results": [],
                    "total": 0,
                    "page": 1,
                    "per_page": pp,
                    "total_pages": 0,
                    "sort_by": sort,
                }
            )
            self._respond_html(_search_page(q, res))
        elif path.startswith("/api/status/"):
            cid = path[len("/api/status/") :]
            self._api_status(cid, qs)
        elif path == "/api/search":
            q = qs.get("q", [""])[0]
            page = int(qs.get("page", ["1"])[0])
            pp = int(qs.get("per_page", ["10"])[0])
            sort = qs.get("sort", ["relevance"])[0]
            if sort not in ("relevance", "frequency", "depth"):
                sort = "relevance"
            self._respond_json(self.server.searcher.search(q, page=page, per_page=pp, sort_by=sort))
        elif path == "/api/stats":
            self._respond_json(self.server.manager.get_statistics())
        elif path == "/api/crawler-dashboard":
            m = self.server.manager
            self._respond_json({"stats": m.get_statistics(), "jobs": m.list_jobs()})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        path = parse.urlparse(self.path).path.rstrip("/") or "/"
        if path == "/":
            self._handle_create_job()
        elif path.startswith("/stop/"):
            cid = path[len("/stop/") :]
            self._respond_json({"ok": self.server.manager.stop_job(cid)})
        elif path.startswith("/pause/"):
            cid = path[len("/pause/") :]
            self._respond_json({"ok": self.server.manager.pause_job(cid)})
        elif path.startswith("/resume/"):
            cid = path[len("/resume/") :]
            self._respond_json({"ok": self.server.manager.resume_job(cid)})
        elif path.startswith("/resume-disk/"):
            cid = parse.unquote(path[len("/resume-disk/") :])
            ok = self.server.manager.resume_job_from_disk(cid)
            if ok:
                self.send_response(303)
                self.send_header("Location", "/status/" + parse.quote(cid, safe=""))
                self.end_headers()
            else:
                self._respond_json({"ok": False}, 400)
        elif path == "/clear":
            self.server.manager.clear_data()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_error(404)

    def _respond_html(self, body: str, code: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond_json(self, obj: Any, code: int = 200) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle_create_job(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        params = parse.parse_qs(body)
        origin = params.get("origin_url", [""])[0].strip()
        if not origin:
            self.send_error(400, "Missing origin_url")
            return
        depth = int(params.get("max_depth", ["2"])[0])
        workers = int(params.get("max_workers", ["4"])[0])
        q_cap = int(params.get("queue_capacity", ["1000"])[0])
        max_pg = int(params.get("max_pages", ["500"])[0])
        hit_rate = float(params.get("hit_rate", ["0"])[0])
        cid = self.server.manager.create_job(
            origin_url=origin,
            max_depth=depth,
            max_workers=workers,
            max_queue_size=q_cap,
            max_pages=max_pg,
            hit_rate=hit_rate,
        )
        self.send_response(303)
        self.send_header("Location", f"/status/{cid}")
        self.end_headers()

    def _api_status(self, crawler_id: str, qs: dict) -> None:
        poll = qs.get("poll", [None])[0]
        last_count = int(qs.get("last_log_count", ["0"])[0])
        shutdown_ev = self.server.shutdown_event
        if poll:
            deadline = time.time() + 10
            while time.time() < deadline and not shutdown_ev.is_set():
                data = self.server.manager.get_job_status(crawler_id)
                if data is None:
                    break
                if len(data.get("logs", [])) > last_count:
                    break
                if data.get("status") not in ("running", "pending", "paused"):
                    break
                shutdown_ev.wait(0.5)
        data = self.server.manager.get_job_status(crawler_id)
        if data is None:
            self._respond_json({"error": "not found"}, 404)
        else:
            self._respond_json(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug(fmt, *args)


def start_server(
    manager: "CrawlerManager",
    searcher: "Searcher",
    host: str = "0.0.0.0",
    port: int = 3600,
) -> None:
    import signal

    server = CrawlerHTTPServer((host, port), CrawlerHandler, manager, searcher)
    logger.info("Server running on http://%s:%d", host, port)
    print(f"  Server running on http://localhost:{port}")
    print("  Press Ctrl+C to stop.\n")

    def _request_shutdown(signum: int, frame: object) -> None:
        signal.signal(signal.SIGINT, _force_exit)
        server.shutdown_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    def _force_exit(signum: int, frame: object) -> None:
        print("\nForce quit.")
        os._exit(1)

    signal.signal(signal.SIGINT, _request_shutdown)
    try:
        server.serve_forever()
    finally:
        server.shutdown_event.set()
        server.shutdown()
