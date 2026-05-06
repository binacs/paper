"""Entrypoint: ``python -m paper_bot.main``.

Reads sources / prompts from ``.github/paper-bot/`` at the repo root, runs the
pipeline, and writes ``.paper-bot-pr-body.md`` if any analyses succeeded.

Environment variables consumed:
- ``DEEPSEEK_API_KEY``   required unless ``DRY_RUN=1``
- ``DEEPSEEK_BASE_URL``  optional, defaults to https://api.deepseek.com
- ``DEEPSEEK_MODEL``     optional, defaults to ``deepseek-chat``
- ``DRY_RUN``            if ``1``, fetch + filter only, no API calls, no writes
- ``MAX_CANDIDATES``     optional override of ``max_candidates_per_run``
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from . import pipeline, render


def _repo_root() -> Path:
    # scripts/paper_bot/main.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    repo_root = _repo_root()
    bot_dir = repo_root / ".github" / "paper-bot"
    sources_path = bot_dir / "sources.yaml"
    classify_prompt = bot_dir / "prompts" / "classify.md"
    analyze_prompt = bot_dir / "prompts" / "analyze.md"

    dry_run = os.environ.get("DRY_RUN") == "1"
    raw_max = (os.environ.get("MAX_CANDIDATES") or "").strip()
    max_override = int(raw_max) if raw_max else None

    new_count = pipeline.run(
        repo_root=repo_root,
        sources_path=sources_path,
        classify_prompt_path=classify_prompt,
        analyze_prompt_path=analyze_prompt,
        dry_run=dry_run,
        max_override=max_override,
    )
    if dry_run:
        return 0

    # Always regenerate the PR body from the FULL branch state (not just this
    # run's additions): if a previous run left commits on the branch without a
    # PR body, this run will pick them up too.
    body_path = render.write_pr_body(repo_root)
    if body_path:
        logging.info("wrote PR body covering all paper-bot commits on branch (this run added %d)", new_count)
    else:
        logging.info("no paper-bot commits on branch yet; skipping PR body")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
