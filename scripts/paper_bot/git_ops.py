"""Git plumbing for the scan pipeline and the review handler.

Conventions:
- Each per-paper commit carries an ``arxiv-id: <id>`` trailer in its message;
  the review handler greps on this to locate the right commit when applying
  a `/refine`, `/regenerate`, or `/reject`.
- All operations assume cwd is the repo root and that ``user.name`` /
  ``user.email`` are configured (see :func:`configure_identity`).
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)


def configure_identity(
    name: str = "paper-bot[bot]",
    email: str = "paper-bot@users.noreply.github.com",
) -> None:
    subprocess.run(["git", "config", "user.name", name], check=True)
    subprocess.run(["git", "config", "user.email", email], check=True)


def _run(
    args: list[str],
    *,
    env: dict | None = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        env=env,
        check=check,
        text=True,
        capture_output=capture,
    )


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Public ``git <args>`` runner.  Thin wrapper around :func:`_run` for
    callers outside this module that need to stage/commit/etc. without
    re-implementing the subprocess plumbing."""
    return _run(args, **kwargs)


def head_sha() -> str:
    return _run(["rev-parse", "HEAD"]).stdout.strip()


def commit_files(paths: Iterable[Path], message: str) -> str:
    str_paths = [str(p) for p in paths]
    _run(["add", "--", *str_paths])
    _run(["commit", "-m", message])
    return head_sha()


def find_by_trailer(trailer: str, value: str, *, base: str = "origin/main") -> str | None:
    """Return the commit sha on the current branch (since `base`) whose message
    contains ``<trailer>: <value>``, or None if not found.

    Used to locate a paper's original commit for /refine, /regenerate, /reject.
    Accepts either ``paper-id`` (canonical SS paperId) or ``arxiv-id`` (when
    available) trailers.
    """
    out = _run(
        ["log", f"{base}..HEAD", f"--grep={trailer}: {value}", "--format=%H"],
    ).stdout.strip().splitlines()
    return out[0] if out else None


# Backwards-compat alias retained while review.py / older tooling migrates.
def find_by_arxiv_id(arxiv_id: str, *, base: str = "origin/main") -> str | None:
    return find_by_trailer("arxiv-id", arxiv_id, base=base)


def autosquash_into(target_sha: str, paths: Iterable[Path]) -> None:
    """Stage `paths`, create a fixup of `target_sha`, then rebase --autosquash.

    Result: `target_sha` is replaced (rewritten) with the changes folded in.
    Caller is responsible for force-pushing the branch afterwards.
    """
    str_paths = [str(p) for p in paths]
    _run(["add", "--", *str_paths])
    _run(["commit", f"--fixup={target_sha}"])
    env = {**os.environ, "GIT_SEQUENCE_EDITOR": "true"}
    _run(["rebase", "-i", "--autosquash", f"{target_sha}^"], env=env)


def revert_commit(
    target_sha: str,
    *,
    extra_paths: list[Path] | None = None,
    message: str | None = None,
) -> bool:
    """Create a revert commit for `target_sha`. Returns False on conflict.

    If ``extra_paths`` is given, the revert is staged with ``--no-commit``,
    those paths are also staged, and everything lands in a SINGLE commit.
    Used by /reject to fold the rejected-list update into the revert.
    """
    if not extra_paths:
        proc = subprocess.run(
            ["git", "revert", "--no-edit", target_sha],
            text=True, capture_output=True,
        )
        if proc.returncode != 0:
            log.warning("revert failed: %s", proc.stderr)
            subprocess.run(["git", "revert", "--abort"], check=False)
            return False
        return True

    proc = subprocess.run(
        ["git", "revert", "--no-commit", target_sha],
        text=True, capture_output=True,
    )
    if proc.returncode != 0:
        log.warning("revert (--no-commit) failed: %s", proc.stderr)
        subprocess.run(["git", "revert", "--abort"], check=False)
        return False
    _run(["add", "--", *[str(p) for p in extra_paths]])
    commit_msg = message or f'Revert "paper-bot: {target_sha[:7]}"'
    _run(["commit", "-m", commit_msg])
    return True


def commits_ahead_of(base: str = "origin/main") -> int:
    return int(_run(["rev-list", "--count", f"{base}..HEAD"]).stdout.strip() or "0")
