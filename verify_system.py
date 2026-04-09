#!/usr/bin/env python3
"""Integration and smoke checks (loopback only; no public internet)."""

from __future__ import annotations

import json
import os
import queue
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

FAILED = 0


def check(cond: bool, msg: str) -> None:
    global FAILED
    if not cond:
        print(f"FAIL: {msg}")
        FAILED += 1
    else:
        print(f"ok  {msg}")


def _docs_exist() -> None:
    check(os.path.isfile(os.path.join(_ROOT, "product_prd.md")), "product_prd.md exists")
    check(os.path.isfile(os.path.join(_ROOT, "AGENTS.md")), "AGENTS.md exists")
    agents_dir = os.path.join(_ROOT, "agents")
    for name in (
        "architect.md",
        "crawler_agent.md",
        "index_storage_agent.md",
        "search_agent.md",
        "ui_api_agent.md",
        "qa_agent.md",
    ):
        check(os.path.isfile(os.path.join(agents_dir, name)), f"agents/{name} exists")


def _imports() -> None:
    import storage.file_store  # noqa: F401
    import crawler.indexer  # noqa: F401
    import search.searcher  # noqa: F401
    import web.server  # noqa: F401
    import utils  # noqa: F401

    check(True, "core packages import")


def _utils_tokenize() -> None:
    import utils as u

    check(u.tokenize("a hi") == ["hi"], "tokenize drops short terms")
    check(
        u.normalize_url("http://Ex.COM/Path") == u.normalize_url("http://ex.com/Path"),
        "normalize_url stable",
    )


def _dummy_site() -> tuple[ThreadingHTTPServer, str]:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            return

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                body = b"""<!DOCTYPE html><html><head><title>Tiny</title></head>
<body><a href="/page2">p2</a> verifytokenalpha beta</body></html>"""
            elif path == "/page2":
                body = b"""<!DOCTYPE html><html><body>verifytokenalpha gamma deep</body></html>"""
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{srv.server_port}"
    return srv, base


def _integration_crawl_and_search() -> None:
    from crawler.indexer import CrawlerManager
    from search.searcher import Searcher

    srv, base = _dummy_site()
    try:
        with tempfile.TemporaryDirectory() as td:
            mgr = CrawlerManager(td)
            jid = mgr.start_job(
                origin_urls=[base + "/"],
                max_depth=2,
                workers=2,
                queue_size=8,
                page_limit=20,
                timeout_sec=5.0,
                same_host_only=True,
            )
            for _ in range(80):
                st = mgr.status_dict(jid)
                assert st is not None
                if int(st.get("metrics", {}).get("pages_processed", 0)) >= 2:
                    break
                time.sleep(0.05)
            st = mgr.status_dict(jid)
            check(st is not None and st.get("queue_capacity") == 8, "job exposes queue capacity")
            check(
                int(st.get("metrics", {}).get("pages_processed", 0)) >= 1,
                "at least one page indexed",
            )
            hits = Searcher(mgr.words).search("verifytokenalpha", limit=10)
            check(len(hits) >= 1, "search finds token from dummy site")
            if hits:
                check(hits[0].url.startswith(base), "hit URL on dummy origin")
            mgr.stop_job(jid, save_queue_snapshot=False)
    finally:
        srv.shutdown()


def _back_pressure_semantics() -> None:
    q: queue.Queue[int] = queue.Queue(maxsize=1)
    q.put(1)
    seen: list[str] = []

    def blocked_put() -> None:
        try:
            q.put(2, timeout=0.2)
            seen.append("ok")
        except queue.Full:
            seen.append("full")

    t = threading.Thread(target=blocked_put)
    t.start()
    t.join()
    check("full" in seen, "bounded queue blocks when full (back-pressure)")


def _api_smoke() -> None:
    from web.server import AppContext, CrawlHTTPRequestHandler, ThreadingHTTPServer

    srv, base = _dummy_site()
    try:
        with tempfile.TemporaryDirectory() as td:
            app = AppContext(td)
            app.crawler.start_job(
                origin_urls=[base + "/"],
                max_depth=1,
                workers=1,
                queue_size=4,
                page_limit=5,
                timeout_sec=5.0,
            )
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), CrawlHTTPRequestHandler)
            httpd.app = app
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            port = httpd.server_address[1]
            time.sleep(0.15)
            u = f"http://127.0.0.1:{port}/api/crawler-dashboard"
            with urllib.request.urlopen(u, timeout=3) as r:
                data = json.loads(r.read().decode())
            check("active_jobs" in data, "GET /api/crawler-dashboard JSON shape")
            u2 = f"http://127.0.0.1:{port}/api/search?q=verifytokenalpha"
            with urllib.request.urlopen(u2, timeout=3) as r:
                data2 = json.loads(r.read().decode())
            check(
                isinstance(data2.get("results"), list),
                "GET /api/search returns results list",
            )
            u3 = f"http://127.0.0.1:{port}/api/crawler-events?since=0&limit=50"
            with urllib.request.urlopen(u3, timeout=3) as r:
                ev = json.loads(r.read().decode())
            check(
                "events" in ev and "next_since" in ev,
                "GET /api/crawler-events JSON shape",
            )
            u4 = f"http://127.0.0.1:{port}/api/crawler-events?since=0&limit=50&filter=system"
            with urllib.request.urlopen(u4, timeout=3) as r:
                ev2 = json.loads(r.read().decode())
            check(
                isinstance(ev2.get("events"), list),
                "GET /api/crawler-events?filter=system returns events list",
            )
            httpd.shutdown()
    finally:
        srv.shutdown()


def main() -> None:
    _docs_exist()
    try:
        _imports()
    except Exception as e:
        check(False, f"imports: {e}")
        print(f"Aborting after {FAILED} failure(s).")
        sys.exit(1)

    _utils_tokenize()
    _back_pressure_semantics()
    try:
        _integration_crawl_and_search()
    except Exception as e:
        check(False, f"crawl/search integration: {e}")
    try:
        _api_smoke()
    except urllib.error.URLError as e:
        check(False, f"api smoke: {e}")

    if FAILED:
        print(f"\n{FAILED} check(s) failed.")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
