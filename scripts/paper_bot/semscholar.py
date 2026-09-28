"""Semantic Scholar Graph API client for venue-based paper discovery.

The API is free and key-less for low-volume use (~1 req/s).  We use the bulk
search endpoint with a ``venue=<name>`` filter, paginate via the returned
``token``, and sort the result locally by citation count so the highest-impact
unanalyzed paper bubbles up first — matching the owner's "classics over
firehose" preference.
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List
from urllib.parse import urlencode

log = logging.getLogger(__name__)

_API_BASE = "https://api.semanticscholar.org/graph/v1"
_BULK_FIELDS = ",".join([
    "title", "abstract", "authors.name", "venue", "year",
    "publicationDate", "citationCount", "externalIds",
    "openAccessPdf",
])
_REQUEST_DELAY_S = 2.5  # politeness: SS unauthenticated quota is shared and tight
_BACKOFF_BASE_S = 10
_BACKOFF_CAP_S = 60
_RETRYABLE_HTTP = {429, 500, 502, 503, 504}
# Optional: a Semantic Scholar API key raises the quota. Unset = anonymous.
_API_KEY_ENV = "SEMANTIC_SCHOLAR_API_KEY"


@dataclass(frozen=True)
class PaperEntry:
    """A paper, regardless of where it was discovered.

    ``paper_id`` is always the Semantic Scholar paperId (40-hex), which is the
    canonical key used in commit trailers and filesystem dedup. ``arxiv_id``
    is set whenever SS knows the arXiv preprint id, and is preferred for
    human-facing references (PR body, slash commands) since it is short and
    memorable.
    """
    paper_id: str
    title: str
    abstract: str
    authors: list[str]
    venue: str
    year: int
    citation_count: int
    arxiv_id: str | None
    doi: str | None
    abs_url: str
    pdf_url: str

    @property
    def display_id(self) -> str:
        return self.arxiv_id or self.paper_id


def _to_entry(p: dict, venue_hint: str = "") -> PaperEntry | None:
    if not p.get("paperId") or not p.get("title"):
        return None
    external = p.get("externalIds") or {}
    arxiv_id = external.get("ArXiv")
    doi = external.get("DOI")
    venue_name = (p.get("venue") or "").strip() or venue_hint
    abs_url = (
        f"https://arxiv.org/abs/{arxiv_id}"
        if arxiv_id
        else f"https://www.semanticscholar.org/paper/{p['paperId']}"
    )
    pdf_url = (
        f"https://arxiv.org/pdf/{arxiv_id}"
        if arxiv_id
        else (p.get("openAccessPdf") or {}).get("url") or ""
    )
    return PaperEntry(
        paper_id=p["paperId"],
        title=" ".join((p.get("title") or "").split()),
        abstract=(p.get("abstract") or "").strip(),
        authors=[a.get("name", "") for a in (p.get("authors") or []) if a.get("name")],
        venue=venue_name,
        year=int(p.get("year") or 0),
        citation_count=int(p.get("citationCount") or 0),
        arxiv_id=arxiv_id,
        doi=doi,
        abs_url=abs_url,
        pdf_url=pdf_url,
    )


def _backoff(attempt: int) -> float:
    """Exponential back-off (10, 20, 40, 60, 60, ...s) plus a little jitter."""
    return min(_BACKOFF_BASE_S * (2 ** attempt), _BACKOFF_CAP_S) + random.uniform(0, 2)


def _retry_after(exc: urllib.error.HTTPError) -> float | None:
    """Parse a numeric ``Retry-After`` header, if the server sent one."""
    value = exc.headers.get("Retry-After") if exc.headers else None
    try:
        return min(max(float(value), 0.0), _BACKOFF_CAP_S * 5) if value else None
    except ValueError:
        return None


def _get(url: str, max_retries: int = 6) -> dict:
    """GET a JSON endpoint with polite back-off on 429 / 5xx / network errors.

    Honors ``Retry-After`` when present; otherwise backs off exponentially.
    The final failed attempt raises immediately instead of sleeping first.
    """
    headers = {"User-Agent": "paper-bot/1.0"}
    api_key = os.environ.get(_API_KEY_ENV)
    if api_key:
        headers["x-api-key"] = api_key
    req = urllib.request.Request(url, headers=headers)
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRYABLE_HTTP:
                raise
            last_exc = exc
            wait = (_retry_after(exc) if exc.code == 429 else None) or _backoff(attempt)
            reason = "rate-limited" if exc.code == 429 else f"HTTP {exc.code}"
        except urllib.error.URLError as exc:
            last_exc = exc
            wait = _backoff(attempt)
            reason = f"request error ({exc.reason})"
        if attempt == max_retries - 1:
            break
        log.warning(
            "semscholar %s; sleeping %.0fs (attempt %d/%d)",
            reason, wait, attempt + 1, max_retries,
        )
        time.sleep(wait)
    raise RuntimeError(
        f"semscholar GET failed after {max_retries} attempts ({last_exc}): {url}"
    )


def fetch_venue(venue: str, since_year: int, hard_limit: int = 500) -> List[PaperEntry]:
    """Fetch papers from a venue published in ``since_year`` or later.

    Uses ``/paper/search/bulk`` (sorted by paperId, paginated via token).
    Returns at most ``hard_limit`` entries to bound a runaway venue. If a
    later page fails after some papers were already fetched, the partial
    result is returned with a warning; if nothing was fetched, it raises.
    """
    out: List[PaperEntry] = []
    token: str | None = None
    while True:
        params: dict = {
            "query": "*",
            "venue": venue,
            "year": f"{since_year}-",
            "fields": _BULK_FIELDS,
        }
        if token:
            params["token"] = token
        url = f"{_API_BASE}/paper/search/bulk?{urlencode(params)}"
        try:
            data = _get(url)
        except (RuntimeError, urllib.error.HTTPError) as exc:
            if not out:
                raise
            log.warning(
                "venue %s: pagination failed after %d papers (%s); "
                "keeping partial result", venue, len(out), exc,
            )
            break
        for p in data.get("data") or []:
            entry = _to_entry(p, venue_hint=venue)
            if entry:
                out.append(entry)
        token = data.get("token")
        if not token or len(out) >= hard_limit:
            break
        time.sleep(_REQUEST_DELAY_S)
    return out


def fetch_venues(venues: Iterable[str], since_year: int) -> List[PaperEntry]:
    """Fetch papers from multiple venues, deduping by paperId.

    A venue that fails (after retries) is logged and skipped so one flaky
    venue doesn't sink the whole run. Raises only if *every* venue failed.
    """
    seen: set[str] = set()
    merged: List[PaperEntry] = []
    venues = list(venues)
    failed: List[str] = []
    for i, v in enumerate(venues):
        if i > 0:
            time.sleep(_REQUEST_DELAY_S)
        log.info("fetching venue %s (since %d)", v, since_year)
        try:
            venue_papers = fetch_venue(v, since_year)
        except (RuntimeError, urllib.error.HTTPError) as exc:
            log.warning("venue %s: fetch failed, skipping (%s)", v, exc)
            failed.append(v)
            continue
        log.info("  -> %d papers", len(venue_papers))
        for p in venue_papers:
            if p.paper_id in seen:
                continue
            seen.add(p.paper_id)
            merged.append(p)
    if venues and len(failed) == len(venues):
        raise RuntimeError(f"semscholar: all {len(venues)} venues failed: {failed}")
    if failed:
        log.warning("skipped %d/%d venues: %s", len(failed), len(venues), failed)
    return merged


def fetch_by_paper_id(paper_id: str) -> PaperEntry | None:
    """Fetch a single paper by Semantic Scholar paperId OR external id.

    SS accepts forms like ``arXiv:2402.15627``, ``DOI:10.1145/...``, plain
    paperId hash, etc.
    """
    url = f"{_API_BASE}/paper/{paper_id}?fields={_BULK_FIELDS}"
    try:
        data = _get(url)
    except (RuntimeError, urllib.error.HTTPError):
        return None
    return _to_entry(data)


def fetch_by_arxiv_id(arxiv_id: str) -> PaperEntry | None:
    return fetch_by_paper_id(f"arXiv:{arxiv_id}")
