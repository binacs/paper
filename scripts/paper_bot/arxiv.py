"""Fetch arXiv entries by category via the public Atom API."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, List

import feedparser

from .slugs import normalize_arxiv_id

ARXIV_QUERY = (
    "https://export.arxiv.org/api/query"
    "?search_query=cat:{cat}"
    "&sortBy=submittedDate&sortOrder=descending"
    "&max_results={n}"
)

# arXiv ToS asks clients to pause ≥3s between requests.
_REQUEST_DELAY_S = 3.0


@dataclass(frozen=True)
class ArxivEntry:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published: str
    pdf_url: str
    abs_url: str


def _pdf_link(entry) -> str:
    for link in getattr(entry, "links", []):
        if getattr(link, "type", "") == "application/pdf":
            return link.href
    return ""


def fetch_category(cat: str, n: int = 50) -> List[ArxivEntry]:
    feed = feedparser.parse(ARXIV_QUERY.format(cat=cat, n=n))
    out: List[ArxivEntry] = []
    for e in feed.entries:
        bare = normalize_arxiv_id(e.id)
        out.append(
            ArxivEntry(
                arxiv_id=bare,
                title=" ".join(e.title.split()),
                abstract=e.summary.strip(),
                authors=[a.name for a in getattr(e, "authors", [])],
                categories=[t.term for t in getattr(e, "tags", [])],
                published=getattr(e, "published", ""),
                pdf_url=_pdf_link(e) or f"https://arxiv.org/pdf/{bare}",
                abs_url=f"https://arxiv.org/abs/{bare}",
            )
        )
    return out


def fetch_categories(cats: Iterable[str], n: int = 50) -> List[ArxivEntry]:
    """Fetch each category, dedup by arxiv_id, preserve insertion order."""
    seen: set[str] = set()
    merged: List[ArxivEntry] = []
    for i, c in enumerate(cats):
        if i > 0:
            time.sleep(_REQUEST_DELAY_S)
        for entry in fetch_category(c, n):
            if entry.arxiv_id in seen:
                continue
            seen.add(entry.arxiv_id)
            merged.append(entry)
    return merged


def fetch_one(arxiv_id: str) -> ArxivEntry | None:
    """Fetch a single arXiv entry by id (e.g. ``2402.15627``).

    Used by ``/regenerate`` to refresh an analysis from the original abstract.
    """
    feed = feedparser.parse(
        f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    )
    for e in feed.entries:
        bare = normalize_arxiv_id(e.id)
        if bare != arxiv_id:
            continue
        return ArxivEntry(
            arxiv_id=bare,
            title=" ".join(e.title.split()),
            abstract=e.summary.strip(),
            authors=[a.name for a in getattr(e, "authors", [])],
            categories=[t.term for t in getattr(e, "tags", [])],
            published=getattr(e, "published", ""),
            pdf_url=_pdf_link(e) or f"https://arxiv.org/pdf/{bare}",
            abs_url=f"https://arxiv.org/abs/{bare}",
        )
    return None
