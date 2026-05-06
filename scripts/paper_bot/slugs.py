"""Slug helpers for arXiv papers."""
from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_VERSION_SUFFIX = re.compile(r"v\d+$")


def normalize_arxiv_id(raw_id: str) -> str:
    """Strip URL prefix and version suffix from an arXiv entry id.

    >>> normalize_arxiv_id("http://arxiv.org/abs/2402.15627v2")
    '2402.15627'
    """
    bare = raw_id.rstrip("/").split("/")[-1]
    return _VERSION_SUFFIX.sub("", bare)


def title_slug(title: str, max_words: int = 8) -> str:
    words = _NON_ALNUM.sub(" ", title.lower()).split()
    return "-".join(words[:max_words]) or "untitled"


def paper_slug(arxiv_id: str, title: str) -> str:
    return f"{arxiv_id}-{title_slug(title)}"


def kebab(value: str) -> str:
    """Lower-case kebab. Used for system_slug sanitization."""
    cleaned = _NON_ALNUM.sub("-", value.lower()).strip("-")
    return cleaned or "misc"
