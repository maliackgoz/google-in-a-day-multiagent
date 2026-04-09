from __future__ import annotations

import glob
import json
import logging
import os
import queue
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from storage.file_store import CrawlerDataStore, VisitedUrlsStore, WordStore
from utils import (
    extract_title_content_and_links,
    normalize_url,
    tokenize,
    word_frequencies,
)

logger = logging.getLogger(__name__)


def _short_url(url: str, max_len: int = 96) -> str:
    u = url.replace("\n", " ").strip()
    if len(u) <= max_len:
        return u
    return u[: max_len - 1] + "…"


class CrawlEventLog:
    """
    Thread-safe ring buffer of crawl events for live UI (bounded; oldest dropped).
    fetch_since(0) returns the newest tail so the panel opens on recent activity.
    """

    def __init__(self, max_entries: int = 800) -> None:
        self._max = max_entries
        self._lock = threading.Lock()
        self._seq = 0
        self._entries: deque[dict[str, Any]] = deque(maxlen=max_entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._seq = 0

    def emit(
        self,
        *,
        job_id: str,
        level: str,
        event: str,
        message: str,
        url: str | None = None,
    ) -> None:
        with self._lock:
            self._seq += 1
            row: dict[str, Any] = {
                "seq": self._seq,
                "ts": time.time(),
                "job_id": job_id,
                "level": level,
                "event": event,
                "message": message,
            }
            if url is not None:
                row["url"] = url
            self._entries.append(row)

    def fetch_since(
        self,
        since: int,
        limit: int = 200,
        job_id: str | None = None,
        *,
        system_only: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            chronological = list(self._entries)
            newest_seq = self._seq
            if not chronological:
                return {
                    "next_since": 0,
                    "events": [],
                    "dropped": False,
                    "newest_seq": newest_seq,
                }

            def _match(e: dict[str, Any]) -> bool:
                if system_only:
                    return (e.get("event") or "").lower() == "system"
                return not job_id or e["job_id"] == job_id

            if since == 0:
                filtered = [dict(e) for e in chronological if _match(e)]
                chunk = filtered[-limit:] if filtered else []
                dropped = len(filtered) > limit
                # Avoid re-delivering the same tail when the buffer is empty on repeat poll.
                next_s = chunk[-1]["seq"] if chunk else newest_seq
                return {
                    "next_since": next_s,
                    "events": chunk,
                    "dropped": dropped,
                    "newest_seq": newest_seq,
                }

            oldest_seq = chronological[0]["seq"]
            dropped = since > 0 and since < oldest_seq - 1
            out: list[dict[str, Any]] = []
            for e in chronological:
                if e["seq"] <= since:
                    continue
                if not _match(e):
                    continue
                out.append(dict(e))
                if len(out) >= limit:
                    break
            next_s = out[-1]["seq"] if out else since
            return {
                "next_since": next_s,
                "events": out,
                "dropped": dropped,
                "newest_seq": newest_seq,
            }


@dataclass(frozen=True)
class CrawlTask:
    url: str
    origin_url: str
    depth: int


@dataclass
class JobMetrics:
    pages_processed: int = 0
    urls_discovered: int = 0
    fetch_errors: int = 0
    skipped_duplicate: int = 0
    skipped_host: int = 0
    skipped_non_html: int = 0
    skipped_empty_body: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def bump_pages(self) -> None:
        with self.lock:
            self.pages_processed += 1

    def bump_discovered(self, n: int = 1) -> None:
        with self.lock:
            self.urls_discovered += n

    def bump_errors(self) -> None:
        with self.lock:
            self.fetch_errors += 1

    def bump_skipped_duplicate(self) -> None:
        with self.lock:
            self.skipped_duplicate += 1

    def bump_skipped_host(self) -> None:
        with self.lock:
            self.skipped_host += 1

    def bump_skipped_non_html(self) -> None:
        with self.lock:
            self.skipped_non_html += 1

    def bump_skipped_empty_body(self) -> None:
        with self.lock:
            self.skipped_empty_body += 1

    def snapshot(self) -> dict[str, int]:
        with self.lock:
            return {
                "pages_processed": self.pages_processed,
                "urls_discovered": self.urls_discovered,
                "fetch_errors": self.fetch_errors,
                "skipped_duplicate": self.skipped_duplicate,
                "skipped_host": self.skipped_host,
                "skipped_non_html": self.skipped_non_html,
                "skipped_empty_body": self.skipped_empty_body,
            }


class _JobRuntime:
    def __init__(
        self,
        job_id: str,
        task_queue: queue.Queue[CrawlTask | None],
        workers: int,
        max_depth: int,
        page_limit: int,
        timeout_sec: float,
        same_host_only: bool,
        seed_hosts: set[str],
        visited: VisitedUrlsStore,
        words: WordStore,
        job_store: CrawlerDataStore,
        metrics: JobMetrics,
        pause_event: threading.Event,
        stop_event: threading.Event,
        threads: list[threading.Thread],
    ) -> None:
        self.job_id = job_id
        self.task_queue = task_queue
        self.workers = workers
        self.max_depth = max_depth
        self.page_limit = page_limit
        self.timeout_sec = timeout_sec
        self.same_host_only = same_host_only
        self.seed_hosts = seed_hosts
        self.visited = visited
        self.words = words
        self.job_store = job_store
        self.metrics = metrics
        self.pause_event = pause_event
        self.stop_event = stop_event
        self.threads = threads


class CrawlerManager:
    """
    Bounded frontier queue (blocking back-pressure), worker pool, pause/resume/stop,
    optional NDJSON queue snapshot on stop for resume.
    """

    # Large pages (e.g. Wikipedia) expose huge link lists; cap keeps the frontier bounded.
    MAX_LINKS_ENQUEUED_PER_PAGE = 300

    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self.visited = VisitedUrlsStore(data_dir)
        self.words = WordStore(data_dir)
        self.job_store = CrawlerDataStore(data_dir)
        self._jobs: dict[str, _JobRuntime] = {}
        self._jobs_lock = threading.Lock()
        self._event_log = CrawlEventLog(max_entries=800)

    def fetch_crawl_events(
        self,
        since: int,
        limit: int = 200,
        job_id: str | None = None,
        *,
        system_only: bool = False,
    ) -> dict[str, Any]:
        cap = max(1, min(int(limit), 500))
        return self._event_log.fetch_since(
            int(since), limit=cap, job_id=job_id, system_only=system_only
        )

    def _emit_crawl(
        self,
        job_id: str,
        level: str,
        event: str,
        message: str,
        url: str | None = None,
    ) -> None:
        su = _short_url(url) if url else None
        self._event_log.emit(
            job_id=job_id, level=level, event=event, message=message, url=su
        )

    def _snapshot_path(self, job_id: str) -> str:
        return os.path.join(self.data_dir, "jobs", f"{job_id}_queue.ndjson")

    def _enqueue_task(self, rt: _JobRuntime, child: CrawlTask) -> bool:
        """
        Try to put a child URL on the frontier without deadlocking workers.

        If all workers are busy producing links and the queue is full, waiting forever
        (or for very long) on put() can deadlock because no worker is free to call get().
        We use short bounded retries; on sustained pressure the caller can skip the rest
        of this page's links and continue processing.
        """
        if rt.stop_event.is_set():
            return False
        for _ in range(3):
            try:
                rt.task_queue.put(child, timeout=0.05)
                return True
            except queue.Full:
                if rt.stop_event.is_set():
                    return False
        return False

    def start_job(
        self,
        *,
        origin_urls: list[str],
        max_depth: int,
        workers: int = 4,
        queue_size: int = 256,
        page_limit: int = 500,
        timeout_sec: float = 15.0,
        same_host_only: bool = True,
        job_id: str | None = None,
        resume: bool = False,
    ) -> str:
        jid = job_id or str(uuid.uuid4())
        task_queue: queue.Queue[CrawlTask | None] = queue.Queue(maxsize=queue_size)
        metrics = JobMetrics()
        pause_event = threading.Event()
        stop_event = threading.Event()
        threads: list[threading.Thread] = []

        normalized_origins: list[str] = []
        seed_hosts: set[str] = set()
        for o in origin_urls:
            try:
                nu = normalize_url(o)
                normalized_origins.append(nu)
                seed_hosts.add(urlparse(nu).netloc.lower())
            except ValueError:
                logger.warning("skip bad origin %r", o)

        if not normalized_origins:
            raise ValueError("no valid origin URLs")

        # page_limit <= 0 means no cap (otherwise 0 would make "0 >= 0" and skip all work).
        effective_page_limit = page_limit if page_limit > 0 else 0

        rt = _JobRuntime(
            job_id=jid,
            task_queue=task_queue,
            workers=workers,
            max_depth=max_depth,
            page_limit=effective_page_limit,
            timeout_sec=timeout_sec,
            same_host_only=same_host_only,
            seed_hosts=seed_hosts,
            visited=self.visited,
            words=self.words,
            job_store=self.job_store,
            metrics=metrics,
            pause_event=pause_event,
            stop_event=stop_event,
            threads=threads,
        )

        with self._jobs_lock:
            self._jobs[jid] = rt

        n_snap = 0
        if resume:
            snap = self._snapshot_path(jid)
            if os.path.isfile(snap):
                with open(snap, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                            task_queue.put(
                                CrawlTask(
                                    d["url"],
                                    d["origin_url"],
                                    int(d["depth"]),
                                ),
                                block=True,
                            )
                            n_snap += 1
                        except (json.JSONDecodeError, KeyError, TypeError):
                            continue

        for u in normalized_origins:
            task_queue.put(CrawlTask(u, u, 0), block=True)
            metrics.bump_discovered(1)

        self.job_store.write(
            jid,
            {
                "job_id": jid,
                "status": "running",
                "config": {
                    "origin_urls": normalized_origins,
                    "max_depth": max_depth,
                    "workers": workers,
                    "queue_size": queue_size,
                    "page_limit": page_limit,
                    "timeout_sec": timeout_sec,
                    "same_host_only": same_host_only,
                },
                "metrics": metrics.snapshot(),
            },
        )

        def worker() -> None:
            self._worker_loop(rt)

        for _ in range(workers):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
        threading.Thread(
            target=lambda: self._monitor_job_completion(rt),
            daemon=True,
        ).start()

        parts = [
            f"{workers} workers",
            f"max_depth={max_depth}",
            f"queue_size={queue_size}",
            f"same_host_only={same_host_only}",
        ]
        if resume and n_snap:
            parts.append(f"restored_queue={n_snap}")
        self._emit_crawl(
            jid,
            "info",
            "job_start",
            "Crawl started (" + ", ".join(parts) + ")",
        )

        return jid

    def _worker_loop(self, rt: _JobRuntime) -> None:
        while True:
            if rt.stop_event.is_set():
                break
            while rt.pause_event.is_set() and not rt.stop_event.is_set():
                threading.Event().wait(0.05)
            if rt.stop_event.is_set():
                break
            try:
                task = rt.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if task is None:
                rt.task_queue.task_done()
                break
            try:
                try:
                    self._process_task(rt, task)
                except Exception:
                    logger.exception("worker failed for task %s", task.url)
                    rt.metrics.bump_errors()
                    self._emit_crawl(
                        rt.job_id,
                        "error",
                        "worker_error",
                        "worker exception (see server stderr)",
                        task.url,
                    )
            finally:
                rt.task_queue.task_done()

    def _unfinished_tasks(self, rt: _JobRuntime) -> int:
        # queue.unfinished_tasks is guarded by queue.mutex.
        with rt.task_queue.mutex:
            return int(rt.task_queue.unfinished_tasks)

    def _monitor_job_completion(self, rt: _JobRuntime) -> None:
        """
        Auto-finish a crawl when no queued work remains.

        Workers can run indefinitely in idle polling mode after all tasks are done.
        This monitor transitions the job to a terminal "finished" state.
        """
        while not rt.stop_event.is_set():
            if self._unfinished_tasks(rt) == 0:
                self.stop_job(
                    rt.job_id,
                    save_queue_snapshot=False,
                    final_status="finished",
                )
                return
            time.sleep(0.2)

    def _allowed_host(self, rt: _JobRuntime, url: str) -> bool:
        if not rt.same_host_only:
            return True
        host = urlparse(url).netloc.lower()
        return host in rt.seed_hosts

    def _flush_job_metrics(self, rt: _JobRuntime) -> None:
        """Persist metrics + queue snapshot for UI/API (safe to call often)."""
        merged = rt.metrics.snapshot()
        merged.update(
            {
                "queue_depth": rt.task_queue.qsize(),
                "queue_capacity": rt.task_queue.maxsize,
                "back_pressure": rt.task_queue.full(),
            }
        )
        status = (
            "paused"
            if rt.pause_event.is_set() and not rt.stop_event.is_set()
            else ("stopped" if rt.stop_event.is_set() else "running")
        )
        try:
            self.job_store.merge_patch(
                rt.job_id,
                {"metrics": merged, "status": status},
            )
        except OSError:
            logger.warning("could not persist job metrics for %s", rt.job_id)

    def _over_page_limit(self, rt: _JobRuntime) -> bool:
        if rt.page_limit <= 0:
            return False
        with rt.metrics.lock:
            return rt.metrics.pages_processed >= rt.page_limit

    def _process_task(self, rt: _JobRuntime, task: CrawlTask) -> None:
        try:
            if rt.stop_event.is_set():
                return
            if self._over_page_limit(rt):
                return

            if not self._allowed_host(rt, task.url):
                rt.metrics.bump_skipped_host()
                self._emit_crawl(
                    rt.job_id,
                    "skip",
                    "skip_host",
                    "URL not on allowed seed host(s)",
                    task.url,
                )
                return

            if not rt.visited.try_add(task.url):
                rt.metrics.bump_skipped_duplicate()
                self._emit_crawl(
                    rt.job_id,
                    "skip",
                    "skip_dup",
                    "Already visited (dedupe)",
                    task.url,
                )
                return

            self._emit_crawl(rt.job_id, "info", "fetch", "GET", task.url)

            html: str | None = None
            try:
                req = Request(
                    task.url,
                    headers={"User-Agent": "GoogleInADayCrawler/1.0 (+edu)"},
                )
                with urlopen(req, timeout=rt.timeout_sec) as resp:
                    ctype = (resp.headers.get_content_type() or "").lower()
                    if ctype and "html" not in ctype and not ctype.startswith(
                        "text/"
                    ):
                        rt.metrics.bump_skipped_non_html()
                        self._emit_crawl(
                            rt.job_id,
                            "skip",
                            "skip_type",
                            f"Not HTML (content-type: {ctype or 'unknown'})",
                            task.url,
                        )
                        return
                    raw = resp.read(2_000_000)
                html = raw.decode("utf-8", errors="replace")
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as e:
                logger.debug("fetch fail %s: %s", task.url, e)
                rt.metrics.bump_errors()
                self._emit_crawl(
                    rt.job_id,
                    "warn",
                    "fetch_error",
                    str(e)[:160],
                    task.url,
                )
                return

            if not html:
                rt.metrics.bump_skipped_empty_body()
                self._emit_crawl(
                    rt.job_id,
                    "skip",
                    "skip_empty",
                    "Empty response body",
                    task.url,
                )
                return

            title, body, links = extract_title_content_and_links(html, task.url)
            text = f"{title}\n{body}"
            counts = word_frequencies(tokenize(text))
            if counts:
                rt.words.add_document(
                    task.url,
                    task.origin_url,
                    task.depth,
                    counts,
                )
            rt.metrics.bump_pages()

            n_enqueued = 0
            if task.depth >= rt.max_depth or rt.stop_event.is_set():
                self._emit_crawl(
                    rt.job_id,
                    "info",
                    "indexed",
                    f"depth={task.depth} terms={len(counts)} links_found={len(links)} enqueued=0 (depth cap or stopping)",
                    task.url,
                )
                return
            if self._over_page_limit(rt):
                self._emit_crawl(
                    rt.job_id,
                    "info",
                    "indexed",
                    f"depth={task.depth} terms={len(counts)} links_found={len(links)} enqueued=0 (page limit)",
                    task.url,
                )
                return

            budget = self.MAX_LINKS_ENQUEUED_PER_PAGE
            for link in links:
                if rt.stop_event.is_set():
                    break
                if budget <= 0:
                    self._emit_crawl(
                        rt.job_id,
                        "info",
                        "link_cap",
                        f"Per-page link cap reached ({self.MAX_LINKS_ENQUEUED_PER_PAGE}); rest skipped",
                        task.url,
                    )
                    break
                if not self._allowed_host(rt, link):
                    continue
                try:
                    nu = normalize_url(link)
                except ValueError:
                    continue
                child = CrawlTask(nu, task.origin_url, task.depth + 1)
                if self._enqueue_task(rt, child):
                    rt.metrics.bump_discovered(1)
                    n_enqueued += 1
                    budget -= 1
                else:
                    if not rt.stop_event.is_set():
                        self._emit_crawl(
                            rt.job_id,
                            "info",
                            "queue_full",
                            "Frontier full; remaining links from this page were deferred",
                            task.url,
                        )
                    break

            self._emit_crawl(
                rt.job_id,
                "info",
                "indexed",
                f"depth={task.depth} terms={len(counts)} links_found={len(links)} enqueued={n_enqueued}",
                task.url,
            )
        finally:
            self._flush_job_metrics(rt)

    def get_job(self, job_id: str) -> _JobRuntime | None:
        with self._jobs_lock:
            return self._jobs.get(job_id)

    def status_dict(self, job_id: str) -> dict[str, Any] | None:
        rt = self.get_job(job_id)
        disk = self.job_store.read(job_id)
        if not rt and not disk:
            return None
        base = dict(disk) if disk else {}
        if rt:
            m = rt.metrics.snapshot()
            base.update(
                {
                    "job_id": job_id,
                    "status": "paused"
                    if rt.pause_event.is_set() and not rt.stop_event.is_set()
                    else ("stopped" if rt.stop_event.is_set() else "running"),
                    "metrics": m,
                    "queue_depth": rt.task_queue.qsize(),
                    "queue_capacity": rt.task_queue.maxsize,
                    "back_pressure": rt.task_queue.full(),
                    "workers": rt.workers,
                }
            )
        return base

    def pause_job(self, job_id: str) -> bool:
        rt = self.get_job(job_id)
        if not rt or rt.stop_event.is_set():
            return False
        rt.pause_event.set()
        self.job_store.merge_patch(job_id, {"status": "paused"})
        self._emit_crawl(job_id, "info", "pause", "Paused (workers will idle until resume)")
        return True

    def resume_job(self, job_id: str) -> bool:
        rt = self.get_job(job_id)
        if not rt or rt.stop_event.is_set():
            return False
        rt.pause_event.clear()
        self.job_store.merge_patch(job_id, {"status": "running"})
        self._emit_crawl(job_id, "info", "resume", "Resumed")
        return True

    def stop_job(
        self,
        job_id: str,
        save_queue_snapshot: bool = True,
        final_status: str = "stopped",
    ) -> bool:
        rt = self.get_job(job_id)
        if not rt:
            return False
        if final_status not in ("stopped", "finished"):
            final_status = "stopped"
        rt.stop_event.set()
        rt.pause_event.clear()

        pending: list[CrawlTask] = []
        while True:
            try:
                item = rt.task_queue.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                pending.append(item)

        if save_queue_snapshot and pending:
            os.makedirs(os.path.dirname(self._snapshot_path(job_id)), exist_ok=True)
            with open(self._snapshot_path(job_id), "w", encoding="utf-8") as f:
                for t in pending:
                    f.write(
                        json.dumps(
                            {
                                "url": t.url,
                                "origin_url": t.origin_url,
                                "depth": t.depth,
                            }
                        )
                        + "\n"
                    )

        for _ in range(rt.workers):
            try:
                rt.task_queue.put_nowait(None)
            except queue.Full:
                pass

        for th in rt.threads:
            th.join(timeout=30.0)

        final_metrics = rt.metrics.snapshot()
        snap_saved = bool(save_queue_snapshot and pending)
        event = "job_finish" if final_status == "finished" else "job_stop"
        msg = (
            f"Finished; drained {len(pending)} queued URL(s)"
            if final_status == "finished"
            else f"Stopped; drained {len(pending)} queued URL(s); snapshot_saved={snap_saved}"
        )
        self._emit_crawl(
            job_id,
            "info",
            event,
            msg,
        )
        self.job_store.merge_patch(
            job_id,
            {
                "status": final_status,
                "metrics": final_metrics,
                "queue_snapshot": self._snapshot_path(job_id)
                if save_queue_snapshot
                else None,
            },
        )

        with self._jobs_lock:
            self._jobs.pop(job_id, None)
        return True

    def dashboard_aggregate(self) -> dict[str, Any]:
        with self._jobs_lock:
            ids = list(self._jobs.keys())
        total_depth = 0
        total_cap = 0
        any_bp = False
        for jid in ids:
            st = self.status_dict(jid)
            if st:
                total_depth += int(st.get("queue_depth", 0))
                total_cap += int(st.get("queue_capacity", 0))
                any_bp = any_bp or bool(st.get("back_pressure"))
        return {
            "active_jobs": len(ids),
            "aggregate_queue_depth": total_depth,
            "aggregate_queue_capacity": total_cap,
            "any_back_pressure": any_bp,
            "job_ids": ids,
        }

    def list_saved_job_summaries(self) -> list[dict[str, Any]]:
        """Jobs persisted under data/jobs/*.json (newest first)."""
        jobs_dir = os.path.join(self.data_dir, "jobs")
        if not os.path.isdir(jobs_dir):
            return []
        records: list[dict[str, Any]] = []
        with self._jobs_lock:
            active_ids = set(self._jobs.keys())
        for fn in os.listdir(jobs_dir):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(jobs_dir, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            jid = str(data.get("job_id") or fn[:-5])
            st = str(data.get("status") or "unknown")
            if jid in active_ids:
                st = "running"
            snap_path = self._snapshot_path(jid)
            has_snap = os.path.isfile(snap_path) and os.path.getsize(snap_path) > 0
            cfg = data.get("config") or {}
            origins = cfg.get("origin_urls") or []
            preview = str(origins[0]) if origins else ""
            if len(preview) > 72:
                preview = preview[:72] + "…"
            m = data.get("metrics") or {}
            records.append(
                {
                    "job_id": jid,
                    "status": st,
                    "active": jid in active_ids,
                    "has_resume_snapshot": has_snap,
                    "seed_preview": preview or "—",
                    "pages_processed": int(m.get("pages_processed", 0)),
                    "mtime": os.path.getmtime(path),
                }
            )
        records.sort(key=lambda r: float(r["mtime"]), reverse=True)
        return records

    def resume_from_saved(self, job_id: str | None = None) -> str:
        """
        Start a job using config from disk and optional queue snapshot.
        If job_id is None, picks the newest stopped job (prefers one with a non-empty snapshot).
        """
        summaries = self.list_saved_job_summaries()
        with self._jobs_lock:
            if job_id and job_id in self._jobs:
                raise ValueError("job is already running")

        chosen: str | None = job_id
        if not chosen:
            inactive = [s for s in summaries if not s["active"]]
            stopped = [s for s in inactive if s["status"] == "stopped"]
            with_snap = [s for s in stopped if s["has_resume_snapshot"]]
            pool = with_snap or stopped
            if not pool:
                raise ValueError("no stopped crawl on disk to resume")
            pool = sorted(pool, key=lambda s: float(s["mtime"]), reverse=True)
            chosen = str(pool[0]["job_id"])

        raw = self.job_store.read(chosen)
        if not raw:
            raise ValueError("saved job not found")
        cfg = raw.get("config") or {}
        origins = cfg.get("origin_urls") or []
        if not origins:
            raise ValueError("saved job has no seed URLs")

        return self.start_job(
            origin_urls=list(origins),
            max_depth=int(cfg.get("max_depth", 2)),
            workers=int(cfg.get("workers", 2)),
            queue_size=int(cfg.get("queue_size", 64)),
            page_limit=int(cfg.get("page_limit", 100)),
            timeout_sec=float(cfg.get("timeout_sec", 15.0)),
            same_host_only=bool(cfg.get("same_host_only", True)),
            job_id=chosen,
            resume=True,
        )

    def clear_persistent_data(self) -> None:
        """
        Stop all active crawls (no queue snapshot), delete index buckets, job files,
        and reset the visited URL set.
        """
        with self._jobs_lock:
            ids = list(self._jobs.keys())
        for jid in ids:
            self.stop_job(jid, save_queue_snapshot=False)

        index_dir = os.path.join(self.data_dir, "index")
        jobs_dir = os.path.join(self.data_dir, "jobs")
        for pattern in (
            os.path.join(index_dir, "*.json"),
            os.path.join(jobs_dir, "*.json"),
            os.path.join(jobs_dir, "*.ndjson"),
        ):
            for path in glob.glob(pattern):
                try:
                    os.remove(path)
                except OSError:
                    logger.warning("could not remove %s", path)

        self.visited.reset_empty()
        self._event_log.clear()
        self._emit_crawl(
            "",
            "info",
            "system",
            "All persistent crawl data was cleared (index, job files, visited URLs).",
        )
