"""Shared URL normalization, HTML text/link extraction, and tokenization."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(url: str, base: str | None = None) -> str:
    """Return a canonical form for deduplication and storage keys."""
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"unsupported scheme: {parsed.scheme!r}")
    netloc = parsed.netloc.lower()
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    # Drop fragment; keep query (distinct resources).
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            path,
            parsed.params,
            parsed.query,
            "",
        )
    )
    return normalized


_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase tokens; drop terms shorter than two characters (PRD)."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text) if len(m.group(0)) >= 2]


def word_frequencies(tokens: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return counts


class _HTMLTextAndLinksParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base = base_url
        self.title: str = ""
        self._in_title = False
        self._skip_depth = 0
        self._chunks: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): v for k, v in attrs if v is not None}
        if t == "a" and "href" in ad:
            href = ad["href"].strip()
            if href and not href.lower().startswith(
                ("javascript:", "mailto:", "#")
            ):
                try:
                    self.links.append(normalize_url(href, self._base))
                except ValueError:
                    pass
        if t == "title":
            self._in_title = True
        if t in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "title":
            self._in_title = False
        if t in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title += data
        else:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(self._chunks)


def extract_title_content_and_links(html: str, page_url: str) -> tuple[str, str, list[str]]:
    """Parse HTML with html.parser; return title, body text, absolute normalized links."""
    parser = _HTMLTextAndLinksParser(page_url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    title = " ".join(parser.title.split())
    body = " ".join(parser.text().split())
    seen: set[str] = set()
    unique_links: list[str] = []
    for u in parser.links:
        if u not in seen:
            seen.add(u)
            unique_links.append(u)
    return title, body, unique_links
