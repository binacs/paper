"""Know-what-we-already-have: the dedup index used by ``pipeline.hard_filter``.

Before this module, dedup only looked at analysis-file frontmatter and
filenames on ``main``.  Two blind spots made the bot re-propose the same
papers week after week:

1. **Hand-curated README entries** (Borg, MAST, MegaScale, ...) have no
   analysis file, so nothing stopped the bot from analysing them again.
2. **Unmerged paper-bot PRs.**  Every weekly branch starts from ``main``, so
   papers sitting in last week's open PR were "new" again this week.  From
   2026-w37 to 2026-w48 ten open PRs carried the same ~8 papers.

``KnownPapers`` collects identifiers from all three places — analysis
frontmatter, topic READMEs, and the commit trailers of other open paper-bot
PRs — and answers ``seen(entry)``.

Everything here is best-effort and read-only: a missing token or a failed API
call only shrinks the index, it never fails the run.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

_SKIP_PARTS = {".git", ".github", "scripts"}
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", re.I)
_DOI_RE = re.compile(r"(?:doi\.org/|/doi/(?:abs/|pdf/|full/|fullHtml/)?)(10\.\d{4,9}/[^\s)\]#?]+)", re.I)
_SS_URL_RE = re.compile(r"semanticscholar\.org/paper/(?:[^/\s)]+/)?([0-9a-f]{40})", re.I)
_MD_LINK_TEXT_RE = re.compile(r"\[([^\]]{12,})\]\(")
_HEADING_RE = re.compile(r"^#{2,4}\s+\*?\s*(.+?)\s*$", re.M)
_TRAILER_RE = re.compile(r"^(paper-id|arxiv-id):\s*(\S+)\s*$", re.M | re.I)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# Trailing "(Venue Year)" that bot headings carry.
_VENUE_SUFFIX_RE = re.compile(r"\s*\([^()]*\b(19|20)\d{2}\)\s*$")


def norm_title(title: str) -> str:
    """Lower-case alnum words; drops a trailing '(Venue 2024)' suffix."""
    t = _VENUE_SUFFIX_RE.sub("", title or "")
    return " ".join(_NON_ALNUM.sub(" ", t.lower()).split())


def norm_doi(doi: str) -> str:
    return (doi or "").strip().rstrip(".").lower()


@dataclass
class KnownPapers:
    paper_ids: set[str] = field(default_factory=set)
    arxiv_ids: set[str] = field(default_factory=set)
    dois: set[str] = field(default_factory=set)
    titles: set[str] = field(default_factory=set)
    # paper ids that are only "seen" because another open bot PR carries them
    in_open_prs: set[str] = field(default_factory=set)

    def seen(self, entry) -> str | None:
        """Return a short reason string if ``entry`` is already known."""
        if entry.paper_id in self.paper_ids:
            return "paper_id"
        if entry.arxiv_id and entry.arxiv_id in self.arxiv_ids:
            return "arxiv_id"
        if entry.doi and norm_doi(entry.doi) in self.dois:
            return "doi"
        t = norm_title(entry.title)
        # Very short titles ("Orca", "Pond") are too ambiguous to match on.
        if len(t) >= 20 and t in self.titles:
            return "title"
        return None


def _iter_md(repo_root: Path):
    for p in repo_root.rglob("*.md"):
        if any(part in _SKIP_PARTS for part in p.relative_to(repo_root).parts):
            continue
        yield p


def _add_frontmatter(known: KnownPapers, text: str) -> None:
    m = _FM_RE.match(text)
    if not m:
        return
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return
    if not isinstance(meta, dict):
        return
    if meta.get("paper_id"):
        known.paper_ids.add(str(meta["paper_id"]))
    if meta.get("arxiv_id"):
        known.arxiv_ids.add(str(meta["arxiv_id"]))
    if meta.get("doi"):
        known.dois.add(norm_doi(str(meta["doi"])))
    if meta.get("title"):
        known.titles.add(norm_title(str(meta["title"])))


def _add_readme(known: KnownPapers, text: str) -> None:
    known.arxiv_ids.update(_ARXIV_URL_RE.findall(text))
    known.dois.update(norm_doi(d) for d in _DOI_RE.findall(text))
    known.paper_ids.update(s.lower() for s in _SS_URL_RE.findall(text))
    for t in _MD_LINK_TEXT_RE.findall(text):
        known.titles.add(norm_title(t))
    for t in _HEADING_RE.findall(text):
        known.titles.add(norm_title(t))


def scan_worktree(repo_root: Path, known: KnownPapers) -> None:
    for p in _iter_md(repo_root):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if p.name == "README.md":
            _add_readme(known, text)
        else:
            _add_frontmatter(known, text)
            # Hand-written notes may also link related papers; their links
            # are NOT treated as "already covered" — only frontmatter is.


def _github_get(path: str) -> list | dict | None:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    req = urllib.request.Request(
        f"{api}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "paper-bot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.warning("GitHub API %s failed: %s", path, e)
        return None


def open_bot_prs(label: str = "paper-bot") -> list[dict]:
    """Open PRs carrying ``label``: ``[{"number", "head_ref"}]``. Empty on error."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return []
    data = _github_get(f"/repos/{repo}/pulls?state=open&per_page=100")
    if not isinstance(data, list):
        return []
    out = []
    for pr in data:
        labels = {lb.get("name") for lb in pr.get("labels") or []}
        head = (pr.get("head") or {}).get("ref", "")
        if label in labels or head.startswith("paper-bot/"):
            out.append({"number": pr.get("number"), "head_ref": head})
    return out


def scan_open_prs(
    repo_root: Path, known: KnownPapers, prs: list[dict], *, current_branch: str
) -> None:
    """Add trailers of commits on other open paper-bot PR branches.

    Needs the remote branches locally (``actions/checkout`` with
    ``fetch-depth: 0`` already fetches them).  Missing refs are skipped.
    """
    for pr in prs:
        ref = pr["head_ref"]
        if not ref or ref == current_branch:
            continue
        try:
            log_text = subprocess.check_output(
                ["git", "log", f"origin/main..origin/{ref}", "--format=%B%x00"],
                text=True, cwd=repo_root, stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            log.info("could not read branch origin/%s; skipping", ref)
            continue
        for key, value in _TRAILER_RE.findall(log_text):
            if key.lower() == "paper-id":
                known.paper_ids.add(value)
                known.in_open_prs.add(value)
            else:
                known.arxiv_ids.add(value)


def build(repo_root: Path, *, current_branch: str = "", prs: list[dict] | None = None) -> KnownPapers:
    known = KnownPapers()
    scan_worktree(repo_root, known)
    if prs:
        scan_open_prs(repo_root, known, prs, current_branch=current_branch)
    known.titles.discard("")
    log.info(
        "dedup index: %d paper_ids, %d arxiv_ids, %d dois, %d titles (%d ids from other open PRs)",
        len(known.paper_ids), len(known.arxiv_ids), len(known.dois),
        len(known.titles), len(known.in_open_prs),
    )
    return known
