from __future__ import annotations

import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from crawler.indexer import CrawlerManager
from search.searcher import Searcher


DEFAULT_PORT = 3600

# Google-inspired accent palette (logo + UI)
_C_BLUE = "#4285F4"
_C_RED = "#EA4335"
_C_YELLOW = "#FBBC04"
_C_GREEN = "#34A853"


class AppContext:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.crawler = CrawlerManager(data_dir)
        self.searcher = Searcher(self.crawler.words)


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class CrawlHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "GoogleInADay/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    @property
    def app(self) -> AppContext:
        return self.server.app  # type: ignore[attr-defined]

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: Any) -> None:
        data = json.dumps(obj, indent=2).encode("utf-8")
        self._send(code, data, "application/json; charset=utf-8")

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n <= 0:
            return b""
        return self.rfile.read(n)

    def _layout(
        self,
        *,
        title: str,
        active: str,
        body_main: str,
        extra_head: str = "",
    ) -> str:
        nav_items = [
            ("home", "/", "Home"),
            ("crawl", "/crawl", "Crawler"),
            ("search", "/search", "Search"),
        ]
        nav_html = []
        for key, href, label in nav_items:
            cls = "nav__link"
            if key == active:
                cls += " nav__link--active"
            nav_html.append(f'<a class="{cls}" href="{href}">{label}</a>')
        nav_joined = "\n".join(nav_html)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html_escape(title)}</title>
  <style>
    :root {{
      --g-blue: {_C_BLUE};
      --g-red: {_C_RED};
      --g-yellow: {_C_YELLOW};
      --g-green: {_C_GREEN};
      --text: #202124;
      --text-secondary: #5f6368;
      --border: #dadce0;
      --surface: #fff;
      --bg: #f8f9fa;
      --shadow: 0 1px 6px rgba(32,33,36,.08);
      --shadow-hover: 0 2px 12px rgba(32,33,36,.15);
      --radius: 24px;
      --radius-sm: 8px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "Google Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      color: var(--text);
      background: var(--bg);
      line-height: 1.5;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 24px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 10;
      box-shadow: var(--shadow);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--text);
      font-size: 1.15rem;
      font-weight: 500;
      letter-spacing: -0.02em;
    }}
    .brand__dots {{
      display: flex;
      gap: 4px;
      align-items: center;
    }}
    .brand__dots span {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }}
    .brand__dots span:nth-child(1) {{ background: var(--g-blue); }}
    .brand__dots span:nth-child(2) {{ background: var(--g-red); }}
    .brand__dots span:nth-child(3) {{ background: var(--g-yellow); }}
    .brand__dots span:nth-child(4) {{ background: var(--g-green); }}
    .nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .nav__link {{
      color: var(--text-secondary);
      text-decoration: none;
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 0.875rem;
      transition: background .15s, color .15s;
    }}
    .nav__link:hover {{ background: #f1f3f4; color: var(--text); }}
    .nav__link--active {{
      background: #e8f0fe;
      color: var(--g-blue);
      font-weight: 500;
    }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }}
    .card {{
      background: var(--surface);
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      padding: 24px;
      margin-bottom: 20px;
    }}
    .card h2 {{
      margin: 0 0 16px;
      font-size: 1.125rem;
      font-weight: 500;
      color: var(--text);
    }}
    label.field {{
      display: block;
      margin-bottom: 14px;
      font-size: 0.8125rem;
      color: var(--text-secondary);
    }}
    label.field span.label-text {{ display: block; margin-bottom: 6px; font-weight: 500; color: var(--text); }}
    input[type="text"], input[type="number"], textarea, select {{
      width: 100%;
      max-width: 100%;
      padding: 10px 14px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: 0.9375rem;
      font-family: inherit;
      transition: border-color .15s, box-shadow .15s;
    }}
    input:focus, textarea:focus, select:focus {{
      outline: none;
      border-color: var(--g-blue);
      box-shadow: 0 0 0 2px rgba(66,133,244,.2);
    }}
    textarea {{ min-height: 72px; resize: vertical; }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 10px 20px;
      border: none;
      border-radius: var(--radius-sm);
      font-size: 0.875rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      transition: box-shadow .15s, background .15s;
    }}
    .btn--primary {{
      background: var(--g-blue);
      color: #fff;
      box-shadow: 0 1px 2px rgba(60,64,67,.3);
    }}
    .btn--primary:hover {{ background: #1967d2; box-shadow: var(--shadow-hover); }}
    .btn--secondary {{ background: #f1f3f4; color: #3c4043; }}
    .btn--secondary:hover {{ background: #e8eaed; }}
    .btn--danger {{ background: #fce8e6; color: #c5221f; }}
    .btn--danger:hover {{ background: #fad2cf; }}
    .btn--small {{ padding: 6px 12px; font-size: 0.8125rem; }}
    .btn-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .muted {{ color: var(--text-secondary); font-size: 0.8125rem; }}
    .hero {{
      text-align: center;
      padding: 48px 16px 32px;
    }}
    .hero h1 {{
      font-size: clamp(1.75rem, 4vw, 2.5rem);
      font-weight: 400;
      margin: 0 0 12px;
      letter-spacing: -0.03em;
    }}
    .hero p {{ color: var(--text-secondary); margin: 0 0 28px; max-width: 28rem; margin-left: auto; margin-right: auto; }}
    .hero-actions {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
    .hero-actions a {{
      text-decoration: none;
      padding: 12px 24px;
      border-radius: var(--radius-sm);
      font-weight: 500;
      font-size: 0.9375rem;
    }}
    .hero-actions .primary {{ background: var(--g-blue); color: #fff; box-shadow: var(--shadow); }}
    .hero-actions .primary:hover {{ box-shadow: var(--shadow-hover); }}
    .hero-actions .ghost {{ background: var(--surface); color: var(--g-blue); border: 1px solid var(--border); }}
    .split {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      align-items: start;
    }}
    @media (max-width: 880px) {{ .split {{ grid-template-columns: 1fr; }} }}
    .job-card {{
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 16px;
      margin-bottom: 12px;
      background: #fafbfc;
    }}
    .job-card:last-child {{ margin-bottom: 0; }}
    .job-card__head {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .job-id {{ font-family: ui-monospace, monospace; font-size: 0.75rem; word-break: break-all; color: var(--text-secondary); }}
    .pill {{
      display: inline-block;
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 500;
      text-transform: capitalize;
    }}
    .pill--running {{ background: #e6f4ea; color: #137333; }}
    .pill--paused {{ background: #fef7e0; color: #b06000; }}
    .pill--stopped {{ background: #f1f3f4; color: #5f6368; }}
    .pill--finished {{ background: #e6f4ea; color: #137333; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 10px;
      font-size: 0.8125rem;
    }}
    .metric strong {{ display: block; font-size: 1.125rem; color: var(--text); font-weight: 500; }}
    .queue-bar {{
      height: 8px;
      background: #e8eaed;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 8px;
    }}
    .queue-bar__fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--g-blue), var(--g-green));
      border-radius: 4px;
      transition: width .35s ease;
    }}
    .queue-bar--hot .queue-bar__fill {{ background: linear-gradient(90deg, var(--g-yellow), var(--g-red)); }}
    #jobs-live .empty {{
      text-align: center;
      padding: 28px 16px;
      color: var(--text-secondary);
    }}
    .search-hero {{ text-align: center; padding: 40px 16px 24px; }}
    .search-box-wrap {{
      max-width: 584px;
      margin: 0 auto 28px;
      position: relative;
    }}
    .search-box {{
      display: flex;
      align-items: center;
      width: 100%;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 4px 8px 4px 16px;
      background: var(--surface);
      box-shadow: var(--shadow);
      transition: box-shadow .2s;
    }}
    .search-box:focus-within {{
      box-shadow: var(--shadow-hover);
      border-color: transparent;
    }}
    .search-box input {{
      flex: 1;
      border: none;
      padding: 12px 8px;
      font-size: 1rem;
      outline: none;
      background: transparent;
    }}
    .search-box button {{
      border: none;
      background: var(--g-blue);
      color: #fff;
      padding: 10px 20px;
      border-radius: calc(var(--radius) - 6px);
      font-weight: 500;
      cursor: pointer;
      font-family: inherit;
    }}
    .search-box button:hover {{ background: #1967d2; }}
    .serp {{ max-width: 640px; margin: 0 auto; }}
    .result {{
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid #ebebeb;
    }}
    .result:last-child {{ border-bottom: none; }}
    .result__title {{
      font-size: 1.125rem;
      color: #1a0dab;
      text-decoration: none;
      font-weight: 400;
    }}
    .result__title:hover {{ text-decoration: underline; }}
    .result__url {{ font-size: 0.875rem; color: #006621; margin: 4px 0; word-break: break-all; }}
    .result__meta {{ font-size: 0.8125rem; color: var(--text-secondary); }}
    .loading {{ text-align: center; padding: 24px; color: var(--text-secondary); }}
    .err {{ background: #fce8e6; color: #c5221f; padding: 12px 16px; border-radius: var(--radius-sm); margin: 12px 0; font-size: 0.875rem; }}
    {extra_head}
  </style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/">
      <span class="brand__dots" aria-hidden="true"><span></span><span></span><span></span><span></span></span>
      <span>Google in a Day</span>
    </a>
    <nav class="nav" aria-label="Main">
      {nav_joined}
    </nav>
  </header>
  <main>
    {body_main}
  </main>
</body>
</html>"""

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path)
        route = path.path or "/"
        q = urllib.parse.parse_qs(path.query)

        if route == "/":
            self._page_home()
            return
        if route == "/crawl":
            self._page_crawl(q)
            return
        if route == "/search":
            self._page_search(q)
            return
        if route == "/api/crawler-dashboard":
            self._json(200, self.app.crawler.dashboard_aggregate())
            return
        if route == "/api/saved-jobs":
            self._json(200, {"jobs": self.app.crawler.list_saved_job_summaries()})
            return
        if route == "/api/crawler-events":
            since = int((q.get("since") or ["0"])[0])
            limit = int((q.get("limit") or ["250"])[0])
            filter_raw = (q.get("filter") or [""])[0].strip().lower()
            system_only = filter_raw == "system"
            job_f = (q.get("job") or [""])[0].strip() or None
            if system_only:
                job_f = None
            self._json(
                200,
                self.app.crawler.fetch_crawl_events(
                    since, limit, job_f, system_only=system_only
                ),
            )
            return
        if route.startswith("/api/status/"):
            jid = route[len("/api/status/") :].strip("/")
            st = self.app.crawler.status_dict(jid)
            if not st:
                self._json(404, {"error": "unknown job"})
                return
            self._json(200, st)
            return
        if route == "/api/search":
            query = (q.get("q") or [""])[0]
            limit = int((q.get("limit") or ["20"])[0])
            offset = int((q.get("offset") or ["0"])[0])
            sort_by = (q.get("sort") or ["relevance"])[0]
            if sort_by not in ("relevance", "frequency", "depth"):
                sort_by = "relevance"
            hits = self.app.searcher.search(
                query, limit=limit, offset=offset, sort_by=sort_by  # type: ignore[arg-type]
            )
            self._json(
                200,
                {
                    "query": query,
                    "results": [
                        {
                            "url": h.url,
                            "origin_url": h.origin_url,
                            "depth": h.depth,
                            "relevance_score": h.relevance_score,
                            "total_frequency": h.total_frequency,
                        }
                        for h in hits
                    ],
                },
            )
            return

        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path or "/"
        if path == "/crawl":
            self._handle_form_crawl()
            return
        if path == "/api/crawl":
            self._handle_api_crawl()
            return
        if path.startswith("/api/pause/"):
            jid = path[len("/api/pause/") :].strip("/")
            ok = self.app.crawler.pause_job(jid)
            self._json(200, {"ok": ok})
            return
        if path.startswith("/api/resume/"):
            jid = path[len("/api/resume/") :].strip("/")
            ok = self.app.crawler.resume_job(jid)
            self._json(200, {"ok": ok})
            return
        if path.startswith("/api/stop/"):
            jid = path[len("/api/stop/") :].strip("/")
            ok = self.app.crawler.stop_job(jid, save_queue_snapshot=True)
            self._json(200, {"ok": ok})
            return
        if path == "/api/resume-saved":
            self._handle_resume_saved()
            return
        if path == "/api/clear-data":
            self._handle_clear_data()
            return

        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def _handle_form_crawl(self) -> None:
        raw = self._read_body()
        fields = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))
        origins = (fields.get("origins") or [""])[0].split()
        try:
            jid = self.app.crawler.start_job(
                origin_urls=origins or ["http://127.0.0.1/"],
                max_depth=int((fields.get("max_depth") or ["2"])[0]),
                workers=int((fields.get("workers") or ["2"])[0]),
                queue_size=int((fields.get("queue_size") or ["64"])[0]),
                page_limit=int((fields.get("page_limit") or ["100"])[0]),
                same_host_only=(fields.get("same_host_only") or ["0"])[0]
                in ("1", "on", "true"),
            )
        except Exception as e:
            self._send(400, str(e).encode("utf-8"), "text/plain; charset=utf-8")
            return
        loc = f"/crawl?job={urllib.parse.quote(jid)}"
        self.send_response(302)
        self.send_header("Location", loc)
        self.end_headers()

    def _handle_api_crawl(self) -> None:
        try:
            body = json.loads(self._read_body().decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})
            return
        origins = body.get("origin_urls") or []
        if isinstance(origins, str):
            origins = [origins]
        try:
            jid = self.app.crawler.start_job(
                origin_urls=list(origins),
                max_depth=int(body.get("max_depth", 2)),
                workers=int(body.get("workers", 4)),
                queue_size=int(body.get("queue_size", 256)),
                page_limit=int(body.get("page_limit", 500)),
                timeout_sec=float(body.get("timeout_sec", 15.0)),
                same_host_only=bool(body.get("same_host_only", True)),
                resume=bool(body.get("resume", False)),
            )
        except Exception as e:
            self._json(400, {"error": str(e)})
            return
        self._json(200, {"job_id": jid})

    def _handle_resume_saved(self) -> None:
        try:
            body = json.loads(self._read_body().decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})
            return
        jid = body.get("job_id")
        if jid is not None and not isinstance(jid, str):
            self._json(400, {"error": "job_id must be a string"})
            return
        if isinstance(jid, str):
            jid = jid.strip() or None
        else:
            jid = None
        try:
            new_id = self.app.crawler.resume_from_saved(job_id=jid)
        except ValueError as e:
            self._json(400, {"error": str(e)})
            return
        self._json(200, {"job_id": new_id})

    def _handle_clear_data(self) -> None:
        try:
            self.app.crawler.clear_persistent_data()
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})
            return
        self._json(200, {"ok": True})

    def _page_home(self) -> None:
        body = f"""
<div class="hero">
  <h1>Search the web you crawl</h1>
  <p>Index pages in real time, query while workers run, and watch queue depth and back-pressure on a live dashboard.</p>
  <div class="hero-actions">
    <a class="primary" href="/crawl">Open Crawler</a>
    <a class="ghost" href="/search">Search index</a>
  </div>
</div>
<div class="card" style="max-width:640px;margin:0 auto;text-align:center">
  <p class="muted" style="margin:0">API: <code>/api/crawler-dashboard</code> · <code>/api/crawler-events</code> · <code>/api/saved-jobs</code> · <code>/api/search</code> · <code>POST /api/resume-saved</code> · <code>POST /api/clear-data</code></p>
</div>"""
        html = self._layout(title="Google in a Day", active="home", body_main=body)
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _page_crawl(self, q: dict[str, list[str]]) -> None:
        focus_job = (q.get("job") or [""])[0].strip()
        focus_js = json.dumps(focus_job)
        crawl_log_css = """
    .crawl-log-card h2 { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
    .crawl-log-card .crawl-log-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-left: auto; }
    .crawl-log-card .crawl-log-toolbar select {
      min-width: 12rem;
      max-width: min(22rem, 100%);
      padding: 6px 10px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
      font-size: 0.8125rem;
      font-family: inherit;
      background: var(--surface);
      color: var(--text);
    }
    .crawl-log-view {
      margin: 0;
      max-height: min(420px, 50vh);
      overflow: auto;
      background: #1e1e1e;
      color: #d4d4d4;
      font-size: 11px;
      line-height: 1.5;
      padding: 12px 14px;
      border-radius: var(--radius-sm);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .crawl-log__line { margin: 0 0 4px; padding: 2px 0; border-bottom: 1px solid #2d2d2d; }
    .crawl-log__line:last-child { border-bottom: none; }
    .crawl-log__line--info .crawl-log__evt { color: #9cdcfe; }
    .crawl-log__line--skip .crawl-log__evt { color: #ce9178; }
    .crawl-log__line--warn .crawl-log__evt { color: #ffb74d; }
    .crawl-log__line--error .crawl-log__evt { color: #f48771; }
    .crawl-log__line--system .crawl-log__evt { color: #c586c0; }
    .crawl-log__line--gap { color: #858585; font-style: italic; border-bottom: none; }
    .crawl-log__ts { color: #6a9955; margin-right: 6px; }
    .crawl-log__job { color: #569cd6; margin-right: 6px; }
"""
        body = f"""
<div class="split">
  <div>
    <div class="card">
      <h2>Start a crawl</h2>
      <form method="post" action="/crawl" id="crawl-form">
        <label class="field">
          <span class="label-text">Seed URLs</span>
          <textarea name="origins" rows="2" placeholder="https://example.com https://example.org/page" required></textarea>
        </label>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <label class="field"><span class="label-text">Max depth</span>
            <input type="number" name="max_depth" value="2" min="0"></label>
          <label class="field"><span class="label-text">Workers</span>
            <input type="number" name="workers" value="2" min="1"></label>
          <label class="field"><span class="label-text">Queue size</span>
            <input type="number" name="queue_size" value="64" min="1"></label>
          <label class="field"><span class="label-text">Page limit</span>
            <input type="number" name="page_limit" value="100" min="1"></label>
        </div>
        <label class="field muted">
          <input type="checkbox" name="same_host_only" value="1" checked> Stay on seed host only (uncheck to follow external links)
        </label>
        <button type="submit" class="btn btn--primary">Start crawl</button>
      </form>
    </div>
    <div class="card">
      <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;margin-bottom:4px">
        <h2 style="margin:0">Saved crawls <span class="muted" style="font-weight:400;font-size:0.875rem">· same refresh as dashboard</span></h2>
        <button type="button" class="btn btn--danger btn--small" id="btn-clear-disk">Clear disk…</button>
      </div>
      <p class="muted" style="margin:0 0 12px;font-size:0.8125rem">Stopped jobs stay on disk until cleared. Use <strong>Resume this crawl</strong> to continue with saved seeds and queue snapshot.</p>
      <div id="saved-jobs"><div class="loading">Loading…</div></div>
    </div>
  </div>
  <div>
    <div class="card">
      <h2>Active jobs <span class="muted" style="font-weight:400;font-size:0.875rem">· updates every 1.5s</span></h2>
      <p class="muted" style="margin-top:-8px;margin-bottom:16px">Aggregate: <span id="dash-summary">…</span></p>
      <div id="jobs-live"><div class="loading">Loading status…</div></div>
      <p class="muted" style="margin-top:16px;margin-bottom:0">Stopped jobs disappear here but remain listed under Saved crawls until you clear disk.</p>
    </div>
  </div>
</div>
<div class="card crawl-log-card" style="margin-top:4px">
  <h2 style="margin:0 0 12px">
    Live crawl log
    <span class="crawl-log-toolbar">
      <label class="muted" style="display:flex;align-items:center;gap:8px;font-size:0.8125rem;flex-wrap:wrap;margin:0">
        <span>Show</span>
        <select id="log-job-filter" aria-label="Filter crawl log">
          <option value="">All logs</option>
          <option value="__system__">System only</option>
        </select>
      </label>
      <button type="button" class="btn btn--secondary btn--small" id="btn-log-clear-view">Clear view</button>
    </span>
  </h2>
  <p class="muted" style="margin:-4px 0 12px;font-size:0.8125rem">Use <strong>All logs</strong> for everything, <strong>System only</strong> for global events (e.g. disk cleared), or pick one crawl. Buffer holds the last ~800 lines; new lines stay out of the way until you scroll near the bottom.</p>
  <div id="crawl-log" class="crawl-log-view" aria-live="polite" aria-relevant="additions"></div>
</div>
<script>
(function() {{
  let focusJob = {focus_js};
  const jobsEl = document.getElementById('jobs-live');
  const savedEl = document.getElementById('saved-jobs');
  const summaryEl = document.getElementById('dash-summary');
  const logEl = document.getElementById('crawl-log');
  const logJobFilter = document.getElementById('log-job-filter');
  let logSince = 0;
  let newestSeq = 0;
  let logGapShown = false;
  let logBusy = false;
  let urlLogFilterApplied = false;

  function esc(s) {{
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }}

  function logIsNearBottom() {{
    const sh = logEl.scrollHeight, ch = logEl.clientHeight, st = logEl.scrollTop;
    if (sh <= ch + 2) return true;
    return (sh - st - ch) <= 100;
  }}

  function syncLogJobFilterOptions(activeIds, savedJobs) {{
    const prev = logJobFilter.value;
    const idSet = new Set();
    (activeIds || []).forEach(function(id) {{ if (id) idSet.add(id); }});
    (savedJobs || []).forEach(function(j) {{ if (j && j.job_id) idSet.add(j.job_id); }});
    if (focusJob) idSet.add(focusJob);
    const sorted = Array.from(idSet).sort();
    const parts = [
      '<option value="">All logs</option>',
      '<option value="__system__">System only</option>',
    ];
    for (let i = 0; i < sorted.length; i++) {{
      const id = sorted[i];
      const short = id.length > 13 ? id.slice(0, 8) + '…' : id;
      const isAct = activeIds.indexOf(id) >= 0;
      let sj = null;
      for (let k = 0; k < (savedJobs || []).length; k++) {{
        if ((savedJobs[k] || {{}}).job_id === id) {{ sj = savedJobs[k]; break; }}
      }}
      let tag = 'Job';
      if (isAct) tag = 'Running';
      else if (sj) {{
        const st = (sj.status || '').toLowerCase();
        if (sj.active || st === 'running') tag = 'Running';
        else if (st === 'stopped') tag = 'Saved';
        else if (st === 'finished') tag = 'Finished';
        else if (st === 'paused') tag = 'Paused';
        else tag = st || 'Saved';
      }}
      const titleAttr = esc(id).replace(/"/g, '&quot;');
      parts.push(
        '<option value="' + id.replace(/&/g, '&amp;').replace(/"/g, '&quot;') + '" title="' + titleAttr + '">' +
        esc(short) + ' · ' + esc(tag) + '</option>'
      );
    }}
    logJobFilter.innerHTML = parts.join('');
    if (!urlLogFilterApplied && focusJob && idSet.has(focusJob) && prev === '') {{
      logJobFilter.value = focusJob;
      urlLogFilterApplied = true;
      logEl.innerHTML = '';
      logSince = 0;
      logGapShown = false;
      pollLog();
      return;
    }}
    if (prev === '__system__') logJobFilter.value = '__system__';
    else if (prev && idSet.has(prev)) logJobFilter.value = prev;
    else if (prev && prev !== '__system__' && !idSet.has(prev)) logJobFilter.value = '';
  }}

  function formatLogLine(e) {{
    const t = new Date((e.ts || 0) * 1000);
    const ts = t.toISOString().slice(11, 19);
    const jid = (e.job_id || '—').slice(0, 8);
    const ev = (e.event || '').toLowerCase();
    const lvl = (ev === 'system') ? 'system' : (e.level || 'info').toLowerCase();
    const url = e.url ? (' · ' + esc(e.url)) : '';
    return (
      '<div class="crawl-log__line crawl-log__line--' + esc(lvl) + '">' +
        '<span class="crawl-log__ts">' + esc(ts) + '</span>' +
        '<span class="crawl-log__job">' + esc(jid) + '</span>' +
        '<span class="crawl-log__evt">' + esc(e.event || '') + '</span> ' +
        esc(e.message || '') + url +
      '</div>'
    );
  }}

  async function pollLog() {{
    if (logBusy) return;
    logBusy = true;
    try {{
      let q = 'since=' + logSince + '&limit=250';
      const jobPick = logJobFilter.value;
      if (jobPick === '__system__') q += '&filter=system';
      else if (jobPick) q += '&job=' + encodeURIComponent(jobPick);
      const r = await fetch('/api/crawler-events?' + q);
      const d = await r.json();
      newestSeq = d.newest_seq || newestSeq;
      if (d.dropped && !logGapShown) {{
        logGapShown = true;
        const gap = document.createElement('div');
        gap.className = 'crawl-log__line crawl-log__gap';
        gap.textContent = '… older log lines were rotated out of the buffer …';
        logEl.insertBefore(gap, logEl.firstChild);
      }}
      const evs = d.events || [];
      const isInitialTail = logSince === 0 && evs.length > 0;
      const nearBottom = logIsNearBottom();
      if (isInitialTail) logEl.innerHTML = '';
      for (let i = 0; i < evs.length; i++) {{
        logEl.insertAdjacentHTML('beforeend', formatLogLine(evs[i]));
      }}
      if (typeof d.next_since === 'number') logSince = d.next_since;
      if (nearBottom && !isInitialTail) {{
        logEl.scrollTop = logEl.scrollHeight;
      }}
    }} catch (e) {{}}
    finally {{ logBusy = false; }}
  }}

  logJobFilter.addEventListener('change', function() {{
    logEl.innerHTML = '';
    logSince = 0;
    logGapShown = false;
    pollLog();
  }});

  document.getElementById('btn-log-clear-view').addEventListener('click', function() {{
    logEl.innerHTML = '';
    logSince = newestSeq;
    logGapShown = false;
  }});

  function pillClass(st) {{
    const s = (st.status || '').toLowerCase();
    if (s === 'paused') return 'pill pill--paused';
    if (s === 'stopped') return 'pill pill--stopped';
    if (s === 'finished') return 'pill pill--finished';
    return 'pill pill--running';
  }}

  function renderJob(st) {{
    const id = st.job_id || '';
    const m = st.metrics || {{}};
    const depth = st.queue_depth ?? 0;
    const cap = st.queue_capacity ?? 1;
    const pct = Math.min(100, Math.round((depth / cap) * 100));
    const hot = st.back_pressure ? ' queue-bar--hot' : '';
    const isFocus = focusJob && id === focusJob;
    const stLower = (st.status || '').toLowerCase();
    const pauseToggleAct = stLower === 'paused' ? 'resume' : 'pause';
    const pauseToggleLabel = stLower === 'paused' ? 'Resume' : 'Pause';
    return (
      '<div class="job-card"' + (isFocus ? ' style="box-shadow:0 0 0 2px var(--g-blue)"' : '') + '>' +
        '<div class="job-card__head">' +
          '<span class="' + pillClass(st) + '">' + (st.status || 'unknown') + '</span>' +
          '<span class="job-id">' + id + '</span>' +
        '</div>' +
        '<div class="metrics">' +
          '<div class="metric"><strong>' + (m.pages_processed ?? 0) + '</strong>pages</div>' +
          '<div class="metric"><strong>' + (m.urls_discovered ?? 0) + '</strong>URLs queued</div>' +
          '<div class="metric"><strong>' + (m.fetch_errors ?? 0) + '</strong>fetch errors</div>' +
          '<div class="metric"><strong>' + (st.workers ?? '—') + '</strong>workers</div>' +
          '<div class="metric"><strong>' + (m.skipped_duplicate ?? 0) + '</strong>skip dup</div>' +
          '<div class="metric"><strong>' + (m.skipped_host ?? 0) + '</strong>skip host</div>' +
          '<div class="metric"><strong>' + (m.skipped_non_html ?? 0) + '</strong>skip !html</div>' +
          '<div class="metric"><strong>' + (m.skipped_empty_body ?? 0) + '</strong>skip empty</div>' +
        '</div>' +
        '<div class="muted" style="margin-top:12px">Queue depth / capacity</div>' +
        '<div class="queue-bar' + hot + '"><div class="queue-bar__fill" style="width:' + pct + '%"></div></div>' +
        '<div class="btn-row">' +
          '<button type="button" class="btn btn--secondary btn--small" data-act="' + pauseToggleAct + '" data-id="' + encodeURIComponent(id) + '">' + pauseToggleLabel + '</button>' +
          '<button type="button" class="btn btn--danger btn--small" data-act="stop" data-id="' + encodeURIComponent(id) + '">Stop</button>' +
        '</div>' +
      '</div>'
    );
  }}

  function renderSavedRow(j) {{
    const id = j.job_id || '';
    const shortId = id.length > 10 ? id.slice(0, 8) + '…' : id;
    const canResume = !j.active && j.status === 'stopped';
    const snapHint = j.has_resume_snapshot ? 'snapshot' : 'seeds only';
    return (
      '<div class="job-card">' +
        '<div class="job-card__head">' +
          '<span class="' + pillClass(j) + '">' + (j.status || 'unknown') + '</span>' +
          '<span class="job-id" title="' + id.replace(/"/g, '&quot;') + '">' + shortId + '</span>' +
        '</div>' +
        '<div class="muted" style="font-size:0.8125rem;margin-bottom:10px;word-break:break-all">' +
          (j.seed_preview || '—').replace(/</g, '&lt;') +
        '</div>' +
        '<div class="muted" style="font-size:0.75rem;margin-bottom:10px">' +
          (j.pages_processed || 0) + ' pages · ' + snapHint +
        '</div>' +
        (canResume
          ? '<button type="button" class="btn btn--secondary btn--small" data-resume-job="' + encodeURIComponent(id) + '">Resume this crawl</button>'
          : '<span class="muted" style="font-size:0.8125rem">' + (j.active ? 'Already running' : '—') + '</span>') +
      '</div>'
    );
  }}

  async function postResume(jobId) {{
    const body = JSON.stringify({{ job_id: jobId }});
    try {{
      const r = await fetch('/api/resume-saved', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: body,
      }});
      const data = await r.json().catch(function() {{ return {{}}; }});
      if (!r.ok) {{
        alert(data.error || 'Could not resume');
        return;
      }}
      focusJob = data.job_id || focusJob;
      const u = new URL(window.location.href);
      u.searchParams.set('job', focusJob);
      history.replaceState(null, '', u);
      await poll();
      if (focusJob) logJobFilter.value = focusJob;
      logEl.innerHTML = '';
      logSince = 0;
      logGapShown = false;
      pollLog();
    }} catch (e) {{
      alert('Resume request failed');
    }}
  }}

  async function poll() {{
    try {{
      const dash = await (await fetch('/api/crawler-dashboard')).json();
      const ids = dash.job_ids || [];
      summaryEl.textContent =
        (dash.active_jobs || 0) + ' active · queue ' + (dash.aggregate_queue_depth || 0) +
        '/' + (dash.aggregate_queue_capacity || 0) +
        (dash.any_back_pressure ? ' · back-pressure' : '');

      if (!ids.length) {{
        jobsEl.innerHTML = '<div class="empty">No active jobs. Start a crawl on the left or resume a stopped job from Saved crawls.</div>';
      }} else {{
        const parts = [];
        for (const id of ids) {{
          const r = await fetch('/api/status/' + encodeURIComponent(id));
          if (!r.ok) continue;
          const st = await r.json();
          st.job_id = id;
          parts.push(renderJob(st));
        }}
        jobsEl.innerHTML = parts.join('') || '<div class="empty">No status available.</div>';
      }}

      const sj = await (await fetch('/api/saved-jobs')).json();
      const list = sj.jobs || [];
      syncLogJobFilterOptions(ids, list);
      if (!list.length) {{
        savedEl.innerHTML = '<div class="empty">No job files yet. Stop a crawl to keep it on disk.</div>';
      }} else {{
        savedEl.innerHTML = list.map(renderSavedRow).join('');
      }}
    }} catch (e) {{
      jobsEl.innerHTML = '<div class="err">Could not refresh status. Is the server running?</div>';
      savedEl.innerHTML = '<div class="err">Could not load saved jobs.</div>';
    }}
  }}

  jobsEl.addEventListener('click', async function(ev) {{
    const btn = ev.target.closest('button[data-act]');
    if (!btn) return;
    const act = btn.getAttribute('data-act');
    const id = btn.getAttribute('data-id');
    if (!id) return;
    try {{
      await fetch('/api/' + act + '/' + id, {{ method: 'POST' }});
      poll();
    }} catch (e) {{}}
  }});

  savedEl.addEventListener('click', function(ev) {{
    const btn = ev.target.closest('button[data-resume-job]');
    if (!btn) return;
    const enc = btn.getAttribute('data-resume-job');
    if (!enc) return;
    postResume(decodeURIComponent(enc));
  }});

  document.getElementById('btn-clear-disk').addEventListener('click', async function() {{
    if (!confirm('This stops any running crawls and deletes the index, job files, queue snapshots, and visited URL set. Continue?')) return;
    try {{
      const r = await fetch('/api/clear-data', {{ method: 'POST' }});
      const data = await r.json().catch(function() {{ return {{}}; }});
      if (!r.ok) {{
        alert(data.error || 'Clear failed');
        return;
      }}
      focusJob = '';
      urlLogFilterApplied = false;
      logJobFilter.value = '';
      const u = new URL(window.location.href);
      u.searchParams.delete('job');
      history.replaceState(null, '', u);
      logEl.innerHTML = '';
      logSince = 0;
      logGapShown = false;
      poll();
      pollLog();
    }} catch (e) {{
      alert('Clear request failed');
    }}
  }});

  poll();
  setInterval(poll, 1500);
  pollLog();
  setInterval(pollLog, 450);
}})();
</script>"""
        html = self._layout(
            title="Crawler — Google in a Day",
            active="crawl",
            body_main=body,
            extra_head=crawl_log_css,
        )
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _page_search(self, q: dict[str, list[str]]) -> None:
        initial_q = (q.get("q") or [""])[0]
        initial_q_js = json.dumps(initial_q)
        body = f"""
<div class="search-hero">
  <h1 style="font-weight:400;font-size:1.75rem;margin:0 0 8px;letter-spacing:-0.02em">Search your index</h1>
  <p class="muted" style="margin:0 0 20px">Same tokenization as the crawler · results update as pages are indexed</p>
  <div class="search-box-wrap">
    <div class="search-box">
      <input type="search" id="q" name="q" placeholder="Search…" value="{_html_escape(initial_q)}" autocomplete="off" aria-label="Search query">
      <button type="button" id="go">Search</button>
    </div>
    <div style="display:flex;gap:12px;justify-content:center;align-items:center;flex-wrap:wrap;margin-top:12px">
      <label class="muted" style="display:flex;align-items:center;gap:6px">
        Sort
        <select id="sort" style="width:auto;padding:6px 10px">
          <option value="relevance">Relevance</option>
          <option value="frequency">Frequency</option>
          <option value="depth">Depth</option>
        </select>
      </label>
    </div>
  </div>
</div>
<div id="serp" class="serp" aria-live="polite"></div>
<script>
(function() {{
  const input = document.getElementById('q');
  const sort = document.getElementById('sort');
  const go = document.getElementById('go');
  const serp = document.getElementById('serp');
  let debounce = null;

  function render(data) {{
    const q = data.query || '';
    const results = data.results || [];
    if (!q.trim()) {{
      serp.innerHTML = '';
      return;
    }}
    if (!results.length) {{
      serp.innerHTML = '<p class="muted" style="text-align:center;padding:24px">No results for <strong>' +
        q.replace(/</g,'&lt;') + '</strong></p>';
      return;
    }}
    serp.innerHTML = results.map(function(r) {{
      const title = (r.url || '').replace(/</g,'&lt;');
      const ou = (r.origin_url || '').replace(/</g,'&lt;');
      return '<article class="result">' +
        '<a class="result__title" href="' + title.replace(/"/g,'&quot;') + '" target="_blank" rel="noopener">' + title + '</a>' +
        '<div class="result__url">' + ou + '</div>' +
        '<div class="result__meta">depth ' + r.depth + ' · score ' + (Math.round(r.relevance_score * 1000) / 1000) +
        ' · freq ' + r.total_frequency + '</div></article>';
    }}).join('');
  }}

  async function run() {{
    const q = input.value.trim();
    const params = new URLSearchParams({{ q: q, sort: sort.value, limit: '20' }});
    if (!q) {{ serp.innerHTML = ''; return; }}
    serp.innerHTML = '<div class="loading">Searching…</div>';
    try {{
      const r = await fetch('/api/search?' + params.toString());
      const data = await r.json();
      render(data);
      const u = new URL(window.location.href);
      u.searchParams.set('q', q);
      u.searchParams.set('sort', sort.value);
      history.replaceState(null, '', u);
    }} catch (e) {{
      serp.innerHTML = '<div class="err">Search failed.</div>';
    }}
  }}

  go.addEventListener('click', run);
  input.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') {{ e.preventDefault(); run(); }}
  }});
  input.addEventListener('input', function() {{
    clearTimeout(debounce);
    debounce = setTimeout(run, 380);
  }});
  sort.addEventListener('change', run);

  if ({initial_q_js}) {{
    input.value = {initial_q_js};
    run();
  }}
}})();
</script>"""
        html = self._layout(title="Search — Google in a Day", active="search", body_main=body)
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")


def main() -> None:
    data_dir = os.environ.get("DATA_DIR", "data")
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    app = AppContext(data_dir)
    server = ThreadingHTTPServer(("", port), CrawlHTTPRequestHandler)
    server.app = app
    print(f"Serving on http://127.0.0.1:{port}  (DATA_DIR={data_dir})")
    server.serve_forever()


if __name__ == "__main__":
    main()
