"""End-to-end paper-bot pipeline: venue scan -> filter -> classify -> analyze -> emit.

Source of truth is Semantic Scholar's venue API (peer-reviewed top venues),
ranked locally by citation count so the highest-impact unanalyzed paper
bubbles up first — matching the owner's "classics over firehose" preference.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from . import dedup, deepseek, git_ops, rejected, render
from .semscholar import PaperEntry, fetch_venues
from .slugs import kebab, paper_slug

log = logging.getLogger(__name__)

# Filesystem locations to skip when checking for prior analyses.
_DEDUP_SKIP_PARTS = {".git", ".github", "scripts"}


@dataclass
class Sources:
    venues: list[dict] = field(default_factory=list)
    since_year: int = 2018
    keyword_blocklist: list[str] = field(default_factory=list)
    max_candidates_per_run: int = 8
    topics: list[str] = field(default_factory=list)
    # Backlog guard: skip the whole run while this many *other* paper-bot PRs
    # are still open.  0 disables the guard.
    max_open_bot_prs: int = 0
    # Analyses are written from the abstract alone; below this length the LLM
    # tends to fill sections with generic text.  0 disables the check.
    min_abstract_chars: int = 0
    # Case-insensitive substrings; papers matching any are ranked ahead of
    # non-matching ones (citations still order within each group).
    focus_keywords: list[str] = field(default_factory=list)


def load_sources(path: Path) -> Sources:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Sources(
        venues=data.get("venues", []),
        since_year=int(data.get("since_year", 2018)),
        keyword_blocklist=[w.lower() for w in data.get("keyword_blocklist", [])],
        max_candidates_per_run=int(data.get("max_candidates_per_run", 8)),
        topics=list(data.get("topics", [])),
        max_open_bot_prs=int(data.get("max_open_bot_prs", 0) or 0),
        min_abstract_chars=int(data.get("min_abstract_chars", 0) or 0),
        focus_keywords=[w.lower() for w in data.get("focus_keywords", []) or []],
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


def hard_filter(
    repo_root: Path,
    entries: Iterable[PaperEntry],
    sources: Sources,
    rejected_ids: set[str],
    known: "dedup.KnownPapers",
    skipped: dict[str, list[PaperEntry]] | None = None,
) -> list[PaperEntry]:
    """Pre-LLM filter. A candidate is dropped if ANY of:

    1. Matches the blocklist (title/abstract substring).
    2. Listed in the persistent reject manifest (paper_id OR arxiv_id).
    3. Already known (``dedup.KnownPapers``): its paper_id / arxiv_id / DOI /
       normalised title appears in an analysis file's frontmatter, in any
       topic README (hand-curated entries included), or in another open
       paper-bot PR.
    4. Filename-prefix dedup — fast fallback for files lacking frontmatter.
    5. Abstract shorter than ``min_abstract_chars`` (analysis would be
       mostly guesswork).

    ``skipped`` (optional) collects dropped entries by reason, for logging
    and the PR body.
    """
    def _skip(reason: str, e: PaperEntry) -> None:
        if skipped is not None:
            skipped.setdefault(reason, []).append(e)

    out: list[PaperEntry] = []
    for e in entries:
        text = f"{e.title}\n{e.abstract}"
        if _matches_any(text, sources.keyword_blocklist):
            _skip("blocklist", e)
            continue
        if e.paper_id in rejected_ids or (e.arxiv_id and e.arxiv_id in rejected_ids):
            _skip("rejected", e)
            continue
        if e.paper_id in known.in_open_prs:
            _skip("in-open-pr", e)
            continue
        why = known.seen(e)
        if why:
            _skip(f"known-{why}", e)
            continue
        if _already_present(repo_root, e):
            _skip("known-filename", e)
            continue
        if sources.min_abstract_chars and len(e.abstract) < sources.min_abstract_chars:
            _skip("short-abstract", e)
            continue
        out.append(e)
    return out


def rank(candidates: list[PaperEntry], sources: Sources) -> list[PaperEntry]:
    """Focus-keyword matches first, then citation count, then recency."""
    def key(p: PaperEntry):
        focus = _matches_any(f"{p.title}\n{p.abstract}", sources.focus_keywords)
        return (0 if focus else 1, -p.citation_count, -p.year)
    return sorted(candidates, key=key)


def _current_branch(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, cwd=repo_root, stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


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

    branch = _current_branch(repo_root)
    prs = dedup.open_bot_prs()
    other_open = [p for p in prs if p["head_ref"] != branch]
    if sources.max_open_bot_prs and len(other_open) >= sources.max_open_bot_prs:
        log.warning(
            "backlog guard: %d other paper-bot PR(s) still open (%s) >= max_open_bot_prs=%d; "
            "skipping this run so the queue does not grow. Merge or close them to resume.",
            len(other_open), ", ".join(f"#{p['number']}" for p in other_open),
            sources.max_open_bot_prs,
        )
        return 0

    known = dedup.build(repo_root, current_branch=branch, prs=prs)
    skipped: dict[str, list[PaperEntry]] = {}
    candidates = hard_filter(
        repo_root, all_papers, sources, rejected_ids, known, skipped,
    )
    for reason, items in sorted(skipped.items()):
        log.info("filtered %-16s %d", reason, len(items))
    candidates = rank(candidates, sources)
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
