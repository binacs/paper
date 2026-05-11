"""End-to-end paper-bot pipeline: venue scan -> filter -> classify -> analyze -> emit.

Source of truth is Semantic Scholar's venue API (peer-reviewed top venues),
ranked locally by citation count so the highest-impact unanalyzed paper
bubbles up first — matching the owner's "classics over firehose" preference.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from . import deepseek, git_ops, rejected, render
from .semscholar import PaperEntry, fetch_venues
from .slugs import kebab, paper_slug

log = logging.getLogger(__name__)

# Filesystem locations to skip when checking for prior analyses.
_DEDUP_SKIP_PARTS = {".git", ".github", "scripts"}
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Sources:
    venues: list[dict] = field(default_factory=list)
    since_year: int = 2018
    keyword_blocklist: list[str] = field(default_factory=list)
    max_candidates_per_run: int = 8
    topics: list[str] = field(default_factory=list)


def load_sources(path: Path) -> Sources:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Sources(
        venues=data.get("venues", []),
        since_year=int(data.get("since_year", 2018)),
        keyword_blocklist=[w.lower() for w in data.get("keyword_blocklist", [])],
        max_candidates_per_run=int(data.get("max_candidates_per_run", 8)),
        topics=list(data.get("topics", [])),
    )


def _matches_any(text: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    haystack = text.lower()
    return any(p in haystack for p in patterns)


def _short_id(entry: PaperEntry) -> str:
    """Identifier used as the filename prefix and for dedup glob."""
    return entry.arxiv_id or entry.paper_id[:7]


def _already_present(repo_root: Path, entry: PaperEntry) -> bool:
    short = _short_id(entry)
    for p in repo_root.rglob(f"{short}-*.md"):
        if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
            continue
        return True
    return False


def _gather_existing_ids(repo_root: Path) -> tuple[set[str], set[str]]:
    """Walk every analysis .md frontmatter, return (paper_ids, arxiv_ids).

    Used to cross-source-dedup: a paper that exists as both an arXiv preprint
    and a peer-reviewed venue copy must not be analyzed twice just because
    its filename prefix differs (preprint uses arxiv id, venue copy uses
    SS paperId when arxiv id is absent).
    """
    paper_ids: set[str] = set()
    arxiv_ids: set[str] = set()
    for p in repo_root.rglob("*.md"):
        if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
            continue
        if p.name == "README.md":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _FM_RE.match(text)
        if not m:
            continue
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if isinstance(meta, dict):
            if meta.get("paper_id"):
                paper_ids.add(str(meta["paper_id"]))
            if meta.get("arxiv_id"):
                arxiv_ids.add(str(meta["arxiv_id"]))
    return paper_ids, arxiv_ids


def hard_filter(
    repo_root: Path,
    entries: Iterable[PaperEntry],
    sources: Sources,
    rejected_ids: set[str],
    existing_paper_ids: set[str],
    existing_arxiv_ids: set[str],
) -> list[PaperEntry]:
    """Pre-LLM filter. A candidate is dropped if ANY of:

    1. Matches the blocklist (title/abstract substring).
    2. Listed in the persistent reject manifest (paper_id OR arxiv_id).
    3. Cross-source dedup — its paper_id or arxiv_id already appears in
       another analysis file's frontmatter (catches preprint vs venue
       double-coverage even when filename prefixes differ).
    4. Filename-prefix dedup — fast fallback for files lacking frontmatter.
    """
    out: list[PaperEntry] = []
    for e in entries:
        text = f"{e.title}\n{e.abstract}"
        if _matches_any(text, sources.keyword_blocklist):
            continue
        if e.paper_id in rejected_ids or (e.arxiv_id and e.arxiv_id in rejected_ids):
            continue
        if e.paper_id in existing_paper_ids:
            continue
        if e.arxiv_id and e.arxiv_id in existing_arxiv_ids:
            continue
        if _already_present(repo_root, e):
            continue
        out.append(e)
    return out


def classify(entry: PaperEntry, topics: list[str], prompt_template: str) -> str | None:
    prompt = prompt_template.format(
        title=entry.title,
        abstract=entry.abstract,
        venue=entry.venue,
        year=entry.year,
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
    log.warning("classifier returned off-list value %r for %s", raw, entry.paper_id)
    return None


def analyze(entry: PaperEntry, prompt_template: str) -> dict | None:
    prompt = prompt_template.format(
        title=entry.title,
        abstract=entry.abstract,
        authors=", ".join(entry.authors[:8]),
        venue=entry.venue,
        year=entry.year,
        citation_count=entry.citation_count,
    )
    try:
        return deepseek.chat_json(
            [{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
    except Exception:
        log.exception("analyzer failed for %s", entry.paper_id)
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
    """Run venue scan -> filter -> classify -> analyze, committing one
    per paper.  Returns the number added this run.  PR body assembly is
    handled separately by :func:`render.write_pr_body`.
    """
    sources = load_sources(sources_path)
    if max_override is not None:
        sources.max_candidates_per_run = max_override

    classify_prompt = classify_prompt_path.read_text(encoding="utf-8")
    analyze_prompt = analyze_prompt_path.read_text(encoding="utf-8")

    venues = [v["name"] for v in sources.venues]
    log.info("fetching %d venues since %d: %s", len(venues), sources.since_year, venues)
    all_papers = fetch_venues(venues, sources.since_year)
    log.info("fetched %d unique papers across venues", len(all_papers))

    rejected_ids = rejected.load(repo_root)
    if rejected_ids:
        log.info("rejected manifest contains %d ids", len(rejected_ids))
    existing_paper_ids, existing_arxiv_ids = _gather_existing_ids(repo_root)
    log.info(
        "existing analyses: %d paper_ids, %d arxiv_ids",
        len(existing_paper_ids), len(existing_arxiv_ids),
    )
    candidates = hard_filter(
        repo_root, all_papers, sources, rejected_ids,
        existing_paper_ids, existing_arxiv_ids,
    )
    # Classics-first: rank by citation count, then by year (recent breaks ties).
    candidates.sort(key=lambda p: (-p.citation_count, -p.year))
    candidates = candidates[: sources.max_candidates_per_run]
    log.info("after filter+cap: %d candidates (top cites: %s)",
             len(candidates),
             [c.citation_count for c in candidates[:5]])

    if dry_run:
        for c in candidates:
            print(f"DRY  {_short_id(c):>16}  cites={c.citation_count:>4}  "
                  f"{(c.venue[:30] or '?'):<30}  {c.title}")
        return 0

    added = 0
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    for c in candidates:
        topic = classify(c, sources.topics, classify_prompt)
        if not topic:
            log.info("classifier skipped %s (%s)", c.paper_id, c.title)
            continue
        analysis = analyze(c, analyze_prompt)
        if not analysis:
            continue
        system_slug = kebab(str(analysis.get("system_slug") or "misc"))
        file_slug = paper_slug(_short_id(c), c.title)
        path = render.write_analysis(
            repo_root, topic, system_slug, file_slug, c, analysis, model
        )
        render.patch_topic_readme(repo_root, topic, system_slug, file_slug, c)
        rel = path.relative_to(repo_root)
        readme_rel = (repo_root / topic / "README.md").relative_to(repo_root)
        # `paper-id:` is the canonical trailer.  `arxiv-id:` is included when
        # available so existing review-handler grep paths keep working.
        trailer_lines = [f"paper-id: {c.paper_id}"]
        if c.arxiv_id:
            trailer_lines.append(f"arxiv-id: {c.arxiv_id}")
        trailer_lines.append(f"venue: {c.venue}")
        trailer_lines.append(f"year: {c.year}")
        trailer_lines.append(f"citations: {c.citation_count}")
        commit_msg = f"paper-bot: {c.title}\n\n" + "\n".join(trailer_lines)
        git_ops.commit_files([rel, readme_rel], commit_msg)
        added += 1
    return added
