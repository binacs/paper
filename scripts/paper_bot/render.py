"""Render analysis dicts to markdown and patch topic READMEs."""
from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .arxiv import ArxivEntry

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
    entry: ArxivEntry,
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

    meta = {
        "arxiv_id": entry.arxiv_id,
        "title": entry.title,
        "authors": entry.authors,
        "categories": entry.categories,
        "published": entry.published,
        "abs_url": entry.abs_url,
        "pdf_url": entry.pdf_url,
        "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
    }
    body = "\n\n".join(body_sections) + ("\n" if body_sections else "")
    target.write_text(_yaml_frontmatter(meta) + "\n# " + entry.title + "\n\n" + body, encoding="utf-8")
    return target


def patch_topic_readme(
    repo_root: Path,
    topic: str,
    system_slug: str,
    file_slug: str,
    entry: ArxivEntry,
) -> None:
    """Insert a section above the paper-bot end marker in <topic>/README.md.

    If the marker is missing, append it at end-of-file with a heading so the
    bot-managed region is visually distinct from hand-curated entries.
    """
    readme = repo_root / topic / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else f"# {topic}\n"
    rel_link = f"{system_slug}/{file_slug}.md"
    new_block = (
        f"\n## {entry.title}\n\n"
        f"Paper link: [{entry.title}]({entry.abs_url})\n\n"
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
    text = text.replace(PAPER_BOT_END_MARKER, new_block + "\n" + PAPER_BOT_END_MARKER, 1)
    readme.write_text(text, encoding="utf-8")


def _branch_paper_lines(repo_root: Path, base: str = "origin/main") -> list[str]:
    """Walk every paper-bot commit between `base` and HEAD, collect a checklist
    line per analysis file still present in the worktree.

    Building from branch state (rather than from this run's outputs) means a
    re-run that finds 0 new candidates still re-derives the full PR body, and
    a `/reject` of one paper produces a body that simply omits the rejected
    one (revert commits delete the .md, so they're skipped here).
    """
    try:
        out = subprocess.check_output(
            ["git", "log", f"{base}..HEAD", "--grep=arxiv-id:", "--format=%H"],
            text=True, cwd=repo_root,
        ).strip().splitlines()
    except subprocess.CalledProcessError:
        return []

    seen_paths: set[str] = set()
    lines: list[str] = []
    # Oldest first so the checklist reads chronologically.
    for sha in reversed(out):
        try:
            diff = subprocess.check_output(
                ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", sha],
                text=True, cwd=repo_root,
            ).splitlines()
        except subprocess.CalledProcessError:
            continue
        for entry in diff:
            status, _, path = entry.partition("\t")
            # Only "A"dded files; skip "M"odified READMEs and "D"eleted reverts.
            if status != "A" or not path.endswith(".md"):
                continue
            if path.endswith("README.md") or path in seen_paths:
                continue
            seen_paths.add(path)
            full = repo_root / path
            if not full.exists():
                continue  # was reverted or otherwise removed
            text = full.read_text(encoding="utf-8")
            m = _FM_RE.match(text)
            if not m:
                continue
            meta = yaml.safe_load(m.group(1)) or {}
            title = meta.get("title", "?")
            abs_url = meta.get("abs_url", "")
            arxiv_id = meta.get("arxiv_id", "")
            body_text = text[m.end():]
            tldr_match = re.search(r"##\s*TL;DR\s*\n+([^\n]+)", body_text)
            tldr = tldr_match.group(1).strip() if tldr_match else ""
            lines.append(
                f"`{path}` (`{sha[:7]}`, arxiv-id `{arxiv_id}`) — [{title}]({abs_url}) — {tldr}"
            )
    return lines


def write_pr_body(repo_root: Path) -> Path | None:
    """Generate the PR body from the branch's full paper-bot commit history.

    Returns the path of the written file, or None if there are no paper-bot
    commits on the branch (in which case no PR body is needed).
    """
    lines = _branch_paper_lines(repo_root)
    if not lines:
        return None
    target = repo_root / ".paper-bot-pr-body.md"
    body = (
        "## paper-bot batch\n\n"
        f"{len(lines)} papers auto-analyzed from arXiv. Each paper is its own "
        "commit so reviews are surgical.\n\n"
        + "\n".join(f"- [ ] {line}" for line in lines)
        + "\n\n"
        "### How to review\n\n"
        "Comment on this PR with one of:\n\n"
        "- `/refine <arxiv-id> <free-form instructions>` — re-write the analysis with your feedback. Folds into the original commit.\n"
        "- `/regenerate <arxiv-id>` — re-fetch the abstract and run the full analyzer again.\n"
        "- `/reject <arxiv-id>` — revert the paper's commit.\n\n"
        "Examples:\n\n"
        "```\n"
        "/refine 2402.15627 缩短 TL;DR 到一句话；扩充 evaluation 段\n"
        "/regenerate 2403.07648\n"
        "/reject 2402.99999\n"
        "```\n\n"
        "When done, merge with **Squash & merge** to keep `main` history clean.\n"
    )
    target.write_text(body, encoding="utf-8")
    return target
