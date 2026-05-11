"""Apply slash commands posted as PR comments.

Triggered by .github/workflows/paper-bot-review.yml when a comment on a PR
labeled ``paper-bot`` starts with one of:

- ``/refine <id|path> <free-form instructions>``  — DeepSeek revises the analysis,
                                                    folded into the original commit
- ``/regenerate <id|path>``                       — full re-analyze, same overwrite
- ``/reject <id|path>``                           — delete the file, sweep READMEs,
                                                    append to rejected manifest
- ``/move <id|path> <new-topic>``                 — relocate to a different topic dir

``<id>`` can be an arXiv id (``2401.09670``), a Semantic Scholar paperId
(40-char hex or its 7-char prefix), or a repo-relative file path.

Environment:
- ``COMMENT_BODY`` — the raw comment text
- ``PR_NUMBER``   — the PR number (used to post status replies via ``gh``)
- ``DEEPSEEK_API_KEY``, ``DEEPSEEK_MODEL`` — same as the scan pipeline
- ``GH_TOKEN``    — read by ``gh`` for posting reply comments
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import deepseek, git_ops, rejected, render, slugs
from .pipeline import analyze
from .semscholar import fetch_by_arxiv_id, fetch_by_paper_id

log = logging.getLogger(__name__)

ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
HEX_ID_RE = re.compile(r"^[0-9a-f]{7,40}$")
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_DEDUP_SKIP_PARTS = {".git", ".github", "scripts"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _post_comment(body: str) -> None:
    pr = os.environ.get("PR_NUMBER")
    if not pr:
        log.warning("no PR_NUMBER set; printing instead:\n%s", body)
        return
    try:
        subprocess.run(
            ["gh", "pr", "comment", pr, "--body", body],
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        log.warning("failed to post PR comment: %s", e)


def _file_for_arxiv_id(arxiv_id: str, repo_root: Path) -> Path | None:
    for p in repo_root.rglob(f"{arxiv_id}-*.md"):
        if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
            continue
        return p
    return None


def _file_for_paper_id(paper_id: str, repo_root: Path) -> Path | None:
    """Match by exact `paper_id` (40-hex) OR its 7-char prefix.

    Falls back to scanning every .md frontmatter when the prefix alone isn't
    enough to disambiguate (rare; <50 papers per PR).
    """
    if len(paper_id) >= 7:
        # First try the filename prefix shortcut for non-arxiv papers.
        for p in repo_root.rglob(f"{paper_id[:7]}-*.md"):
            if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
                continue
            meta, _ = _split_frontmatter(p.read_text(encoding="utf-8"))
            stored = (meta.get("paper_id") or "").lower()
            if stored.startswith(paper_id.lower()):
                return p
    # Slow path: scan every .md frontmatter.
    for p in repo_root.rglob("*.md"):
        if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
            continue
        if p.name == "README.md":
            continue
        meta, _ = _split_frontmatter(p.read_text(encoding="utf-8"))
        stored = (meta.get("paper_id") or "").lower()
        if stored.startswith(paper_id.lower()):
            return p
    return None


def _resolve_target(token: str, repo_root: Path) -> Path | None:
    if ARXIV_ID_RE.match(token):
        return _file_for_arxiv_id(token, repo_root)
    if HEX_ID_RE.match(token):
        return _file_for_paper_id(token, repo_root)
    p = (repo_root / token).resolve()
    try:
        p.relative_to(repo_root)
    except ValueError:
        return None
    return p if p.is_file() else None


def _split_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, text[m.end():]


def _emit_frontmatter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n"


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text, count=1)
        text = re.sub(r"\n```\s*$", "", text, count=1)
    return text


def _resolve_paper(token: str, repo_root: Path) -> tuple[Path, dict, str] | None:
    """Resolve a user-supplied token to (file_path, frontmatter, commit_sha).

    Posts a comment + returns None on failure.
    """
    target = _resolve_target(token, repo_root)
    if not target:
        _post_comment(f"⚠️ Couldn't resolve `{token}` to a file in this PR.")
        return None
    meta, _ = _split_frontmatter(target.read_text(encoding="utf-8"))
    paper_id = meta.get("paper_id")
    arxiv_id = meta.get("arxiv_id")
    commit = None
    if paper_id:
        commit = git_ops.find_by_trailer("paper-id", str(paper_id))
    if not commit and arxiv_id:
        commit = git_ops.find_by_trailer("arxiv-id", str(arxiv_id))
    if not commit:
        _post_comment(
            f"⚠️ Couldn't find a commit on this branch matching "
            f"`paper-id: {paper_id}` (file: `{target.relative_to(repo_root)}`)."
        )
        return None
    return target, meta, commit


def do_refine(args: str, repo_root: Path) -> int:
    parts = args.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        _post_comment("⚠️ Usage: `/refine <id|path> <instructions...>`")
        return 1
    target_token, instruction = parts[0], parts[1].strip()

    resolved = _resolve_paper(target_token, repo_root)
    if not resolved:
        return 1
    target, meta, commit = resolved

    _, body = _split_frontmatter(target.read_text(encoding="utf-8"))
    prompt = (
        repo_root / ".github" / "paper-bot" / "prompts" / "refine.md"
    ).read_text(encoding="utf-8").format(instruction=instruction, body=body)

    revised = deepseek.chat(
        [{"role": "user", "content": prompt}],
        max_tokens=3000,
    )
    revised = _strip_code_fence(revised)
    if not revised:
        _post_comment("⚠️ DeepSeek returned an empty body; aborting.")
        return 1
    if not revised.endswith("\n"):
        revised += "\n"

    meta["revised_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    target.write_text(_emit_frontmatter(meta) + "\n" + revised, encoding="utf-8")

    git_ops.autosquash_into(commit, [target.relative_to(repo_root)])
    _post_comment(
        f"✅ Refined `{target.relative_to(repo_root)}`. "
        f"Folded into commit `{commit[:7]}`."
    )
    return 0


def do_regenerate(args: str, repo_root: Path) -> int:
    token = args.strip().split(None, 1)[0] if args.strip() else ""
    if not token:
        _post_comment("⚠️ Usage: `/regenerate <id|path>`")
        return 1
    resolved = _resolve_paper(token, repo_root)
    if not resolved:
        return 1
    target, meta, commit = resolved
    paper_id = meta.get("paper_id")
    arxiv_id = meta.get("arxiv_id")

    entry = None
    if paper_id:
        entry = fetch_by_paper_id(str(paper_id))
    if not entry and arxiv_id:
        entry = fetch_by_arxiv_id(str(arxiv_id))
    if not entry:
        _post_comment(f"⚠️ Couldn't fetch paper `{paper_id or arxiv_id}` from Semantic Scholar.")
        return 1

    analyze_prompt = (
        repo_root / ".github" / "paper-bot" / "prompts" / "analyze.md"
    ).read_text(encoding="utf-8")
    analysis = analyze(entry, analyze_prompt)
    if not analysis:
        _post_comment("⚠️ DeepSeek analyzer call failed; aborting.")
        return 1

    rel = target.relative_to(repo_root)
    topic = rel.parts[0]
    system_slug = (
        rel.parts[1]
        if len(rel.parts) >= 3
        else slugs.kebab(str(analysis.get("system_slug") or "misc"))
    )
    file_slug = rel.stem
    new_path = render.write_analysis(
        repo_root, topic, system_slug, file_slug, entry, analysis,
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    )
    git_ops.autosquash_into(commit, [new_path.relative_to(repo_root)])
    _post_comment(
        f"♻️ Regenerated `{rel}` from a fresh Semantic Scholar fetch. "
        f"Folded into commit `{commit[:7]}`."
    )
    return 0


def _all_topic_dirs(repo_root: Path) -> list[Path]:
    """Repo-relative paths to top-level directories that look like topics
    (i.e. have a README.md).  Used to sweep all topics when /reject'ing a
    paper that may have been /move'd between topics.
    """
    out: list[Path] = []
    for child in sorted(repo_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in {"scripts"}:
            continue
        if (child / "README.md").exists():
            out.append(child)
    return out


def do_reject(args: str, repo_root: Path) -> int:
    token = args.strip().split(None, 1)[0] if args.strip() else ""
    if not token:
        _post_comment("⚠️ Usage: `/reject <id|path>`")
        return 1
    resolved = _resolve_paper(token, repo_root)
    if not resolved:
        return 1
    target, meta, _ = resolved  # original commit isn't needed for delete-style reject

    primary_id = str(meta.get("arxiv_id") or meta.get("paper_id") or "").strip()
    if not primary_id:
        _post_comment(
            f"⚠️ `{target.relative_to(repo_root)}` has no paper_id/arxiv_id "
            "in frontmatter; aborting reject."
        )
        return 1
    title = str(meta.get("title") or "").strip()

    # Delete file; sweep every topic README (paper may have been /move'd);
    # add to manifest; bundle everything into one commit.  Compared to
    # git-revert, this is robust to prior /move and avoids patch conflicts.
    target.unlink(missing_ok=True)
    for topic_dir in _all_topic_dirs(repo_root):
        render.remove_paper_from_readme(repo_root, topic_dir.name, meta)
    rejected.add(repo_root, primary_id=primary_id, comment=title)

    git_ops.run(["add", "-A"])
    git_ops.run(["commit", "-m", f"drop: paper-bot {primary_id}"])

    _post_comment(
        f"🗑️ Dropped paper `{primary_id}` and added to "
        f"`{rejected.REJECTED_REL_PATH.as_posix()}` so it won't be re-scanned. "
        "Squash-merge the PR to keep `main` clean."
    )
    return 0


def do_move(args: str, repo_root: Path) -> int:
    parts = args.strip().split(None, 1)
    if len(parts) != 2:
        _post_comment("⚠️ Usage: `/move <id|path> <new-topic>`")
        return 1
    target_token, new_topic = parts[0], parts[1].strip().strip("/")

    # Validate new_topic against the configured allowlist.
    sources_path = repo_root / ".github" / "paper-bot" / "sources.yaml"
    try:
        cfg = yaml.safe_load(sources_path.read_text(encoding="utf-8")) or {}
    except Exception:
        cfg = {}
    allowed = list(cfg.get("topics") or [])
    if new_topic not in allowed:
        _post_comment(
            f"⚠️ Unknown topic `{new_topic}`. Allowed: {', '.join(allowed) or '(none configured)'}"
        )
        return 1

    resolved = _resolve_paper(target_token, repo_root)
    if not resolved:
        return 1
    target, meta, _ = resolved
    rel = target.relative_to(repo_root)
    if len(rel.parts) < 2:
        _post_comment(f"⚠️ Can't infer current topic from path `{rel}`.")
        return 1
    old_topic = rel.parts[0]
    if old_topic == new_topic:
        _post_comment(f"ℹ️ `{rel}` is already under `{new_topic}`; nothing to do.")
        return 0

    system_dir = rel.parts[1] if len(rel.parts) >= 3 else "misc"
    new_rel = Path(new_topic) / system_dir / rel.name
    new_full = repo_root / new_rel
    new_full.parent.mkdir(parents=True, exist_ok=True)

    git_ops.run(["mv", str(rel), str(new_rel)])

    render.remove_paper_from_readme(repo_root, old_topic, meta)
    render.append_readme_entry(
        repo_root, new_topic, system_dir, new_rel.stem,
        title=str(meta.get("title") or ""),
        abs_url=str(meta.get("abs_url") or ""),
        venue=str(meta.get("venue") or ""),
        year=meta.get("year") or "",
    )

    primary_id = str(meta.get("arxiv_id") or meta.get("paper_id") or "").strip()
    trailer_lines = []
    if meta.get("paper_id"):
        trailer_lines.append(f"paper-id: {meta['paper_id']}")
    if meta.get("arxiv_id"):
        trailer_lines.append(f"arxiv-id: {meta['arxiv_id']}")
    commit_msg = f"move: paper-bot {primary_id} → {new_topic}"
    if trailer_lines:
        commit_msg += "\n\n" + "\n".join(trailer_lines)
    git_ops.run(["add", "-A"])
    git_ops.run(["commit", "-m", commit_msg])

    _post_comment(f"📦 Moved `{rel}` → `{new_rel}`.")
    return 0


_DISPATCH = {
    "/refine": do_refine,
    "/regenerate": do_regenerate,
    "/reject": do_reject,
    "/move": do_move,
}


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    body = (os.environ.get("COMMENT_BODY") or "").strip()
    if not body:
        return 0
    cmd, _, rest = body.partition(" ")
    cmd = cmd.strip()
    handler = _DISPATCH.get(cmd)
    if not handler:
        log.info("ignoring non-command body: %r", body[:60])
        return 0
    git_ops.configure_identity()
    log.info("handling %s", cmd)
    return handler(rest, _repo_root())


if __name__ == "__main__":
    raise SystemExit(main())
