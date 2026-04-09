#!/usr/bin/env python3
"""Lightweight verification for the **scaffold** repository.

Full end-to-end checks (crawl dummy site, back-pressure, search index) belong here once
agents implement the system. For now this script only validates:

  1. Required documentation and agent description files exist.
  2. Core modules import and expected symbols are defined.
  3. ``CrawlerManager`` / ``Searcher`` / HTTP stack can be wired as in ``run.py``.

Usage (from the project root):

    python3 verify_system.py
"""

from __future__ import annotations

import importlib
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

_passed = 0
_failed = 0
_failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {label}")
    else:
        _failed += 1
        line = f"  [FAIL] {label}"
        if detail:
            line += f" -- {detail}"
        print(line)
        _failures.append(label)


def section_deliverables() -> None:
    print("\n--- Section 1: Deliverables ---")
    for name in (
        "readme.md",
        "product_prd.md",
        "recommendation.md",
        "multi_agent_workflow.md",
    ):
        check(os.path.isfile(os.path.join(PROJECT_ROOT, name)), f"{name} exists")
    agents_dir = os.path.join(PROJECT_ROOT, "agents")
    check(os.path.isdir(agents_dir), "agents/ directory exists")
    for agent_file in (
        "architect.md",
        "crawler_agent.md",
        "index_storage_agent.md",
        "search_agent.md",
        "ui_api_agent.md",
        "qa_agent.md",
    ):
        p = os.path.join(agents_dir, agent_file)
        check(os.path.isfile(p), f"agents/{agent_file} exists")


def section_imports() -> None:
    print("\n--- Section 2: Module imports & API surface ---")
    utils = importlib.import_module("utils")
    check(callable(getattr(utils, "normalize_url", None)), "utils.normalize_url")
    check(callable(getattr(utils, "tokenize", None)), "utils.tokenize")
    check(callable(getattr(utils, "extract_title_and_content", None)), "utils.extract_title_and_content")

    storage = importlib.import_module("storage.file_store")
    check(hasattr(storage, "VisitedUrlsStore"), "VisitedUrlsStore")
    check(hasattr(storage, "WordStore"), "WordStore")
    check(hasattr(storage, "CrawlerDataStore"), "CrawlerDataStore")

    crawler = importlib.import_module("crawler.indexer")
    check(hasattr(crawler, "CrawlerManager"), "CrawlerManager")
    check(hasattr(crawler, "CrawlTask"), "CrawlTask")
    check(hasattr(crawler, "UrlQueue"), "UrlQueue")

    search = importlib.import_module("search.searcher")
    check(hasattr(search, "Searcher"), "Searcher")

    web = importlib.import_module("web.server")
    check(hasattr(web, "CrawlerHTTPServer"), "CrawlerHTTPServer")
    check(hasattr(web, "CrawlerHandler"), "CrawlerHandler")
    check(callable(getattr(web, "start_server", None)), "start_server")


def section_stub_wiring() -> None:
    print("\n--- Section 3: Stub wiring (no network crawl) ---")
    import tempfile

    from crawler.indexer import CrawlerManager
    from search.searcher import Searcher

    data_dir = tempfile.mkdtemp(prefix="giad_scaffold_")
    try:
        m = CrawlerManager(data_dir)
        s = Searcher(m.word_store)
        cid = m.create_job("https://example.com", max_depth=1, max_pages=10)
        check(bool(cid), "create_job returns id")
        st = m.get_job_status(cid)
        check(st is not None and st.get("id") == cid, "get_job_status round-trip")
        check(st is not None and st.get("status") == "stub", "job status is scaffold stub")
        r = s.search("test")
        check(r.get("total") == 0, "searcher returns empty total")
        stats = m.get_statistics()
        check("total_crawlers" in stats, "get_statistics has total_crawlers")
        m.shutdown()
    finally:
        import shutil

        shutil.rmtree(data_dir, ignore_errors=True)


def main() -> int:
    print("=" * 60)
    print("  Google-in-a-Day (Multi-Agent)  —  Scaffold verification")
    print("=" * 60)
    section_deliverables()
    section_imports()
    section_stub_wiring()
    print()
    print("=" * 60)
    print(f"  Results:  {_passed}/{_passed + _failed} passed,  {_failed} failed")
    if _failed:
        print("  Failures:", "; ".join(_failures))
        print("=" * 60)
        return 1
    print("  All scaffold checks passed.")
    print("  Implement features per product_prd.md, then extend this script.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
