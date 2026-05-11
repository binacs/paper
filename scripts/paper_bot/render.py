"""Render analysis dicts to markdown and patch topic READMEs."""
from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .semscholar import PaperEntry

log = logging.getLogger(__name__)
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

PAPER_BOT_END_MARKER = "<!-- paper-bot:end -->"

_SECTIONS: list[tuple[str, str]] = [
    ("tldr", "TL;DR"),
    ("problem", "Problem & Motivation"),
    ("key_ideas", "Key Ideas"),
    ("system_design", "System Design"),
    ("evaluation", "Evaluation"),
    ("takeaways", "Takeaways"),
    ("related_work", "Related Work"),
    ("open_questions", "Open Questions"),
]


def _yaml_frontmatter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n"


def _existing_system_dir(topic_dir: Path, system_slug: str) -> Path:
    """Reuse a system directory regardless of case/hyphenation drift."""
    target = system_slug.lower()
    if topic_dir.is_dir():
        for child in topic_dir.iterdir():
            if child.is_dir() and child.name.lower() == target:
                return child
    return topic_dir / system_slug


def write_analysis(
    repo_root: Path,
    topic: str,
    system_slug: str,
    file_slug: str,
    entry: PaperEntry,
    analysis: dict,
    model: str,
) -> Path:
    topic_dir = repo_root / topic
    system_dir = _existing_system_dir(topic_dir, system_slug)
    system_dir.mkdir(parents=True, exist_ok=True)
    target = system_dir / f"{file_slug}.md"

    body_sections: list[str] = []
    for key, heading in _SECTIONS:
        v = analysis.get(key)
        if not v:
            continue
        body_sections.append(f"## {heading}\n\n{str(v).strip()}")

    meta: dict = {
        "paper_id": entry.paper_id,
        "title": entry.title,
        "authors": entry.authors,
        "venue": entry.venue,
        "year": entry.year,
        "citations": entry.citation_count,
        "abs_url": entry.abs_url,
        "pdf_url": entry.pdf_url,
        "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
    }
    if entry.arxiv_id:
        meta["arxiv_id"] = entry.arxiv_id
    if entry.doi:
        meta["doi"] = entry.doi

    body = "\n\n".join(body_sections) + ("\n" if body_sections else "")
    target.write_text(
        _yaml_frontmatter(meta) + "\n# " + entry.title + "\n\n" + body,
        encoding="utf-8",
    )
    return target


def append_readme_entry(
    repo_root: Path,
    topic: str,
    system_slug: str,
    file_slug: str,
    *,
    title: str,
    abs_url: str,
    venue: str = "",
    year: int | str = "",
) -> None:
    """Insert a paper section above ``<!-- paper-bot:end -->`` in <topic>/README.md.

    Idempotent: if the same `abs_url` already appears in the bot-managed
    region, the file is left unchanged.  Bot region is created lazily on
    first write.
    """
    readme = repo_root / topic / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else f"# {topic}\n"
    rel_link = f"{system_slug}/{file_slug}.md"
    venue_year_str = (
        f" ({venue} {year})" if venue
        else (f" ({year})" if year else "")
    )
    new_block = (
        f"\n## {title}{venue_year_str}\n\n"
        f"Paper link: [{title}]({abs_url})\n\n"
        f"Analysis: [{rel_link}]({rel_link})\n"
    )

    if PAPER_BOT_END_MARKER not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += (
            "\n---\n\n"
            "## Auto-analyzed papers\n\n"
            "_Entries below this line are managed by `paper-bot`. "
            "Manual edits are fine; just keep them above the marker._\n\n"
            f"{PAPER_BOT_END_MARKER}\n"
        )
    # Idempotency: skip if abs_url already in the bot region.
    head, _, _ = text.partition(PAPER_BOT_END_MARKER)
    bot_start = head.rfind("## Auto-analyzed papers")
    if bot_start != -1 and abs_url and abs_url in head[bot_start:]:
        readme.write_text(text, encoding="utf-8")
        return
    text = text.replace(PAPER_BOT_END_MARKER, new_block + "\n" + PAPER_BOT_END_MARKER, 1)
    readme.write_text(text, encoding="utf-8")


def patch_topic_readme(
    repo_root: Path,
    topic: str,
    system_slug: str,
    file_slug: str,
    entry: PaperEntry,
) -> None:
    """Back-compat wrapper used by the scan pipeline."""
    append_readme_entry(
        repo_root, topic, system_slug, file_slug,
        title=entry.title, abs_url=entry.abs_url,
        venue=entry.venue, year=entry.year,
    )


def remove_paper_from_readme(repo_root: Path, topic: str, meta: dict) -> None:
    """Strip the bot section for one paper from <topic>/README.md, identified
    by abs_url / arxiv_id / paper_id.  No-op if the file or section is absent.
    """
    readme = repo_root / topic / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    if PAPER_BOT_END_MARKER not in text:
        return

    abs_url = str(meta.get("abs_url") or "").strip()
    paper_id = str(meta.get("paper_id") or "").strip()
    arxiv_id = str(meta.get("arxiv_id") or "").strip()
    if not (abs_url or paper_id or arxiv_id):
        return

    head, sep, tail = text.partition(PAPER_BOT_END_MARKER)
    bot_start = head.rfind("## Auto-analyzed papers")
    if bot_start == -1:
        return
    pre = head[:bot_start]
    bot_region = head[bot_start:]

    parts = re.split(r"(\n## )", bot_region)
    kept = [parts[0]]
    i = 1
    while i < len(parts):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        matched = (
            (abs_url and abs_url in body)
            or (arxiv_id and f"{arxiv_id}-" in body)
            or (paper_id and paper_id[:7] in body)
        )
        if not matched:
            kept.extend([parts[i], body])
        i += 2

    new_text = pre + "".join(kept) + sep + tail
    if new_text != text:
        readme.write_text(new_text, encoding="utf-8")


def _branch_paper_lines(repo_root: Path, base: str = "origin/main") -> list[str]:
    """Walk every paper-bot commit between `base` and HEAD, collect a checklist
    line per analysis file still present in the worktree.

    Built from branch state (rather than from the current run's outputs) so
    re-runs after partial failures still produce a complete checklist, and
    a `/reject` of one paper produces a body that simply omits that paper
    (revert commits delete the .md, so it falls out here).
    """
    try:
        # Multiple --grep is OR by default.  Recognize either the canonical
        # `paper-id:` trailer or the legacy `arxiv-id:` trailer so an old PR
        # produced by the arXiv-firehose pipeline still renders correctly.
        out = subprocess.check_output(
            ["git", "log", f"{base}..HEAD",
             "--grep=paper-id:", "--grep=arxiv-id:",
             "--format=%H"],
            text=True, cwd=repo_root,
        ).strip().splitlines()
    except subprocess.CalledProcessError:
        return []

    seen_paths: set[str] = set()
    lines: list[str] = []
    for sha in reversed(out):  # oldest first; chronological reading order
        try:
            diff = subprocess.check_output(
                ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", sha],
                text=True, cwd=repo_root,
            ).splitlines()
        except subprocess.CalledProcessError:
            continue
        for entry in diff:
            status, _, path = entry.partition("\t")
            if status != "A" or not path.endswith(".md"):
                continue
            if path.endswith("README.md") or path in seen_paths:
                continue
            seen_paths.add(path)
            full = repo_root / path
            if not full.exists():
                continue
            text = full.read_text(encoding="utf-8")
            m = _FM_RE.match(text)
            if not m:
                continue
            meta = yaml.safe_load(m.group(1)) or {}
            title = meta.get("title", "?")
            abs_url = meta.get("abs_url", "")
            display_id = meta.get("arxiv_id") or (meta.get("paper_id") or "")[:7]
            venue = meta.get("venue", "")
            year = meta.get("year", "")
            cites = meta.get("citations", "")
            venue_meta = f"{venue} {year}" if venue else str(year)
            body_text = text[m.end():]
            tldr_match = re.search(r"##\s*TL;DR\s*\n+([^\n]+)", body_text)
            tldr = tldr_match.group(1).strip() if tldr_match else ""
            lines.append(
                f"`{display_id}` ({cites} cites, {venue_meta}) — "
                f"[{title}]({abs_url})\n"
                f"  - file: `{path}` (`{sha[:7]}`)\n"
                f"  - tl;dr: {tldr}"
            )
    return lines


def write_pr_body(repo_root: Path) -> Path | None:
    """Generate the PR body from the branch's full paper-bot commit history."""
    lines = _branch_paper_lines(repo_root)
    if not lines:
        return None
    target = repo_root / ".paper-bot-pr-body.md"
    body = (
        "## paper-bot batch\n\n"
        f"{len(lines)} papers from top systems venues, ranked by citation "
        "count. Each paper is its own commit so reviews are surgical.\n\n"
        + "\n".join(f"- [ ] {line}" for line in lines)
        + "\n\n"
        "### How to review\n\n"
        "Comment on this PR with one of:\n\n"
        "- `/refine <id> <free-form instructions>` — re-write the analysis with your feedback. Folds into the original commit.\n"
        "- `/regenerate <id>` — re-fetch the paper and run the full analyzer again.\n"
        "- `/reject <id>` — revert the paper's commit.\n\n"
        "`<id>` can be an arXiv id (when shown), the 7-char paper-id, "
        "or the file path. Examples:\n\n"
        "```\n"
        "/refine 2401.09670 把 evaluation 段补充和 vLLM 的对比数字\n"
        "/regenerate 72f77a3\n"
        "/reject gpu-training/misc/2024-some-paper.md\n"
        "```\n\n"
        "When done, merge with **Squash & merge** to keep `main` history clean.\n"
    )
    target.write_text(body, encoding="utf-8")
    return target
