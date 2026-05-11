"""Persistent rejected-papers manifest.

Sorted plaintext file at ``.github/paper-bot/rejected.txt`` — one identifier
per line (arXiv id or Semantic Scholar paperId), lexicographically sorted so
diffs are stable and manual edits are easy.

Consulted by :func:`pipeline.hard_filter` so a rejected paper is never
re-scanned, even after the .md is deleted from the worktree.  Manually
editable for pre-rejection of known-noise papers.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

REJECTED_REL_PATH = Path(".github") / "paper-bot" / "rejected.txt"

_HEADER = [
    "# Papers explicitly excluded from paper-bot scanning.",
    "# One identifier per line — arXiv id (NNNN.NNNNN) or Semantic Scholar",
    "# paperId (40-hex). Inline comment after the first whitespace is ignored.",
    "# Lines starting with `#` are comments. Manual edits welcome and survive",
    "# bot-driven updates because the file is re-emitted sorted on every write.",
]


def _parse_entries(text: str) -> dict[str, str]:
    """Parse the file body into ``id -> "  # comment"`` (or empty string).

    Header/blank lines are ignored; the canonical header is re-emitted on write.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        ident = parts[0]
        rest = ("  " + parts[1]) if len(parts) > 1 else ""
        out[ident] = rest
    return out


def load(repo_root: Path) -> set[str]:
    """Return the set of rejected identifiers (paper_id or arxiv_id)."""
    path = repo_root / REJECTED_REL_PATH
    if not path.exists():
        return set()
    return set(_parse_entries(path.read_text(encoding="utf-8")).keys())


def add(repo_root: Path, *, primary_id: str, comment: str = "") -> Path:
    """Add ``primary_id`` to the manifest (idempotent; file kept sorted).

    Returns the path of the file that was written.
    """
    path = repo_root / REJECTED_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        _parse_entries(path.read_text(encoding="utf-8")) if path.exists() else {}
    )
    if primary_id not in existing:
        existing[primary_id] = ("  # " + comment) if comment else ""
    elif comment and not existing[primary_id]:
        # Backfill comment if user added the line manually without one.
        existing[primary_id] = "  # " + comment

    sorted_ids = sorted(existing.keys(), key=str.lower)
    lines = list(_HEADER) + [""] + [f"{i}{existing[i]}" for i in sorted_ids]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
