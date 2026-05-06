"""Apply slash commands posted as PR comments.

Triggered by .github/workflows/paper-bot-review.yml when a comment on a PR
labeled ``paper-bot`` starts with one of:

- ``/refine <arxiv-id|path> <free-form instructions>``  — overwrite original commit
- ``/regenerate <arxiv-id|path>``                       — re-analyze from scratch, overwrite original commit
- ``/reject <arxiv-id|path>``                           — revert the paper's commit

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

from . import deepseek, git_ops, render, slugs
from .arxiv import fetch_one
from .pipeline import analyze

log = logging.getLogger(__name__)

ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
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


def _resolve_target(token: str, repo_root: Path) -> Path | None:
    """Resolve an arxiv id or repo-relative path to a Path under repo_root."""
    if ARXIV_ID_RE.match(token):
        for p in repo_root.rglob(f"{token}-*.md"):
            if any(part in _DEDUP_SKIP_PARTS for part in p.parts):
                continue
            return p
        return None
    p = (repo_root / token).resolve()
    try:
        p.relative_to(repo_root)
    except ValueError:
        return None
    return p if p.is_file() else None


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta_dict, body_after_frontmatter). meta_dict is empty if no FM."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, text[m.end():]


def _emit_frontmatter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n"


def _arxiv_id_from(target: Path) -> str | None:
    meta, _ = _split_frontmatter(target.read_text(encoding="utf-8"))
    aid = meta.get("arxiv_id")
    return str(aid) if aid else None


def _strip_code_fence(text: str) -> str:
    """Trim a single leading/trailing markdown fence if the model added one."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text, count=1)
        text = re.sub(r"\n```\s*$", "", text, count=1)
    return text


def _resolve_paper(token: str, repo_root: Path) -> tuple[Path, str, str] | None:
    """Common prefix for /refine, /regenerate, /reject: resolve token to
    (path, arxiv_id, commit_sha). Posts a comment + returns None on failure.
    """
    target = _resolve_target(token, repo_root)
    if not target:
        _post_comment(f"⚠️ Couldn't resolve `{token}` to a file in this PR.")
        return None
    arxiv_id = _arxiv_id_from(target)
    if not arxiv_id:
        _post_comment(f"⚠️ `{target.name}` has no `arxiv_id` in frontmatter.")
        return None
    commit = git_ops.find_by_arxiv_id(arxiv_id)
    if not commit:
        _post_comment(
            f"⚠️ No commit on this branch carries `arxiv-id: {arxiv_id}`. "
            "Was the paper added by a different bot run?"
        )
        return None
    return target, arxiv_id, commit


def do_refine(args: str, repo_root: Path) -> int:
    parts = args.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        _post_comment("⚠️ Usage: `/refine <arxiv-id|path> <instructions...>`")
        return 1
    target_token, instruction = parts[0], parts[1].strip()

    resolved = _resolve_paper(target_token, repo_root)
    if not resolved:
        return 1
    target, arxiv_id, commit = resolved

    meta, body = _split_frontmatter(target.read_text(encoding="utf-8"))
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
        f"✅ Refined `{target.relative_to(repo_root)}`. Folded into commit `{commit[:7]}`."
    )
    return 0


def do_regenerate(args: str, repo_root: Path) -> int:
    token = args.strip().split(None, 1)[0] if args.strip() else ""
    if not token:
        _post_comment("⚠️ Usage: `/regenerate <arxiv-id|path>`")
        return 1
    resolved = _resolve_paper(token, repo_root)
    if not resolved:
        return 1
    target, arxiv_id, commit = resolved

    entry = fetch_one(arxiv_id)
    if not entry:
        _post_comment(f"⚠️ Couldn't fetch `{arxiv_id}` from arXiv.")
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
        f"♻️ Regenerated `{rel}` from a fresh arXiv fetch. Folded into commit `{commit[:7]}`."
    )
    return 0


def do_reject(args: str, repo_root: Path) -> int:
    token = args.strip().split(None, 1)[0] if args.strip() else ""
    if not token:
        _post_comment("⚠️ Usage: `/reject <arxiv-id|path>`")
        return 1
    resolved = _resolve_paper(token, repo_root)
    if not resolved:
        return 1
    _, arxiv_id, commit = resolved

    if git_ops.revert_commit(commit):
        _post_comment(
            f"🗑️ Reverted commit `{commit[:7]}` for `{arxiv_id}`. "
            "Squash-merge the PR when done to keep `main` clean."
        )
        return 0
    _post_comment(
        f"⚠️ Couldn't auto-revert `{commit[:7]}` (likely a downstream conflict). "
        "Please drop the paper manually."
    )
    return 1


_DISPATCH = {
    "/refine": do_refine,
    "/regenerate": do_regenerate,
    "/reject": do_reject,
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
