"""End-to-end paper-bot pipeline: fetch -> filter -> classify -> analyze -> emit."""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from . import deepseek, git_ops, render
from .arxiv import ArxivEntry, fetch_categories
from .slugs import kebab, paper_slug

log = logging.getLogger(__name__)

# Filesystem locations to skip when checking for prior analyses.
_DEDUP_SKIP_PARTS = {".git", ".github", "scripts"}


@dataclass
class Sources:
    arxiv_categories: list[dict] = field(default_factory=list)
    keyword_allowlist: list[str] = field(default_factory=list)
    keyword_blocklist: list[str] = field(default_factory=list)
    max_candidates_per_run: int = 8
    topics: list[str] = field(default_factory=list)


def load_sources(path: Path) -> Sources:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Sources(
        arxiv_categories=data.get("arxiv_categories", []),
        keyword_allowlist=[w.lower() for w in data.get("keyword_allowlist", [])],
        keyword_blocklist=[w.lower() for w in data.get("keyword_blocklist", [])],
        max_candidates_per_run=int(data.get("max_candidates_per_run", 8)),
        topics=list(data.get("topics", [])),
    )


def _matches_any(text: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    haystack = text.lower()
    return any(p in haystack for p in patterns)


def _slug_already_present(repo_root: Path, arxiv_id: str) -> bool:
    for p in repo_root.rglob(f"{arxiv_id}-*.md"):
        if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
            continue
        return True
    return False


def hard_filter(
    repo_root: Path, entries: Iterable[ArxivEntry], sources: Sources
) -> list[ArxivEntry]:
    out: list[ArxivEntry] = []
    for e in entries:
        text = f"{e.title}\n{e.abstract}"
        if sources.keyword_allowlist and not _matches_any(text, sources.keyword_allowlist):
            continue
        if _matches_any(text, sources.keyword_blocklist):
            continue
        if _slug_already_present(repo_root, e.arxiv_id):
            continue
        out.append(e)
    return out


def classify(entry: ArxivEntry, topics: list[str], prompt_template: str) -> str | None:
    prompt = prompt_template.format(
        title=entry.title,
        abstract=entry.abstract,
        topics=", ".join(topics),
    )
    raw = deepseek.chat(
        [{"role": "user", "content": prompt}],
        max_tokens=20,
    ).strip().lower()
    first = re.split(r"\s+", raw, maxsplit=1)[0] if raw else ""
    first = first.strip(".,'\"`:")
    if first in topics:
        return first
    if first == "skip":
        return None
    log.warning("classifier returned off-list value %r for %s", raw, entry.arxiv_id)
    return None


def analyze(entry: ArxivEntry, prompt_template: str) -> dict | None:
    prompt = prompt_template.format(
        title=entry.title,
        abstract=entry.abstract,
        authors=", ".join(entry.authors[:8]),
        categories=", ".join(entry.categories),
    )
    try:
        return deepseek.chat_json(
            [{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
    except Exception:
        log.exception("analyzer failed for %s", entry.arxiv_id)
        return None


def run(
    repo_root: Path,
    sources_path: Path,
    classify_prompt_path: Path,
    analyze_prompt_path: Path,
    *,
    dry_run: bool,
    max_override: int | None = None,
) -> int:
    """Run the scan + analyze pipeline. Returns the number of papers added in
    this run. PR body assembly is handled separately by ``render.write_pr_body``
    so that re-runs which add 0 papers still emit a body covering pre-existing
    commits on the branch.
    """
    sources = load_sources(sources_path)
    if max_override is not None:
        sources.max_candidates_per_run = max_override

    classify_prompt = classify_prompt_path.read_text(encoding="utf-8")
    analyze_prompt = analyze_prompt_path.read_text(encoding="utf-8")

    cats = [c["cat"] for c in sources.arxiv_categories]
    log.info("fetching arXiv categories: %s", cats)
    entries = fetch_categories(cats, n=50)
    log.info("fetched %d unique entries", len(entries))

    candidates = hard_filter(repo_root, entries, sources)
    candidates = candidates[: sources.max_candidates_per_run]
    log.info("after filter+cap: %d candidates", len(candidates))

    if dry_run:
        for c in candidates:
            print(f"DRY  {c.arxiv_id}\t{c.title}")
        return 0

    added = 0
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    for c in candidates:
        topic = classify(c, sources.topics, classify_prompt)
        if not topic:
            log.info("classifier skipped %s (%s)", c.arxiv_id, c.title)
            continue
        analysis = analyze(c, analyze_prompt)
        if not analysis:
            continue
        system_slug = kebab(str(analysis.get("system_slug") or "misc"))
        file_slug = paper_slug(c.arxiv_id, c.title)
        path = render.write_analysis(
            repo_root, topic, system_slug, file_slug, c, analysis, model
        )
        render.patch_topic_readme(repo_root, topic, system_slug, file_slug, c)
        rel = path.relative_to(repo_root)
        readme_rel = (repo_root / topic / "README.md").relative_to(repo_root)
        # One commit per paper.  The `arxiv-id:` trailer is what review.py
        # greps for when handling /refine, /regenerate, /reject.
        commit_msg = f"paper-bot: {c.title}\n\narxiv-id: {c.arxiv_id}"
        git_ops.commit_files([rel, readme_rel], commit_msg)
        added += 1
    return added
