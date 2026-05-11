# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository nature

This is a **documentation-only repository**: a curated index of research papers (and a few blog posts) organized by topic. There is no source code, no build system, no tests, and no language tooling. Every change is a Markdown edit.

Top-level topic directories, each containing a single `README.md` index:

- `distributed-system/` — classic distributed systems papers (GFS, MapReduce, Bigtable, Spanner, F1, …)
- `orchestration-scheduling/` — cluster scheduling / resource management (Borg, Omega, Mesos, YARN, Apollo, Twine, MAST, Gödel, …); contains placeholder subdirectories with `.gitkeep` files reserved for per-system deep-dive notes
- `gpu-training/` — large-scale ML training systems (MegaScale, …)
- `ai/` — AI/ML reading list (Ilya's "30u30" reference list)
- `profile/` — repo owner's academic profile links (ORCID, ACM, Google Scholar)

## How to make changes

The dominant operation in this repo is **adding a new paper to an existing topic README**. Match the established format inside that file:

```markdown
## <Paper / System Name>

Paper link: [<Title>](<URL>)
```

Some sections include extra links (Blog, GitHub, alternate HTML version) — follow the surrounding pattern of the file you are editing rather than imposing a new one. The orchestration-scheduling README uses `## *` to flag emphasized / featured entries (e.g. `## * ByteDance Gödel`); preserve that convention.

When adding an entirely new topic, create a new top-level directory with a `README.md` whose first line is `# <Topic Title>`.

## Commit message style

Follow the existing log conventions — short, lowercase, prefixed by intent and (often) topic:

- `add: <paper or system>` — new paper entry
- `<topic>: add <thing>` — e.g. `scheduling: add gke`
- `fix: <what>` — corrections to existing entries
- `init: <topic>` — first commit for a new topic

## paper-bot (automated PRs + reviewable interaction)

Two workflows under `.github/workflows/`:

- **`paper-bot.yml`** (scheduled + manual): weekly cron pulls papers from top systems venues via Semantic Scholar's API, calls DeepSeek to classify + analyze them, and opens a PR. Each paper is its own commit on a per-week branch (`paper-bot/YYYY-wWW`). Candidates are sorted by citation count so classics surface first.
- **`paper-bot-review.yml`** (PR-comment-driven): listens for slash commands you post on the PR and rewrites the branch in place.

Slash commands (posted as PR comments; only repo-owner comments trigger):

- `/refine <id|path> <free-form instructions>` — DeepSeek revises that paper's analysis with your feedback. The new content is folded into the **original commit** (`git commit --fixup` + `git rebase --autosquash`), then force-pushed.
- `/regenerate <id|path>` — re-fetches the paper from Semantic Scholar and runs the full analyzer. Same overwrite-original-commit semantics.
- `/reject <id|path>` — deletes the analysis file, sweeps every topic's README to remove that paper's section (handles previously `/move`d papers), and appends its id to `.github/paper-bot/rejected.txt`. All bundled into one `drop: paper-bot <id>` commit. The manifest is a sorted plaintext list of arxiv ids / SS paperIds; `pipeline.hard_filter` consults it so a rejected paper is never re-scanned even after the .md is gone from the worktree. The file is also manually editable for pre-rejecting known noise.
- `/move <id|path> <new-topic>` — relocates the analysis to a different topic directory. Updates both topic READMEs (removes from old, adds to new) and creates a `move: paper-bot <id> → <topic>` commit. `<new-topic>` must be in the `topics:` allowlist in `sources.yaml`.

The review workflow has a `concurrency: group: paper-bot-review-<pr#>` lock so back-to-back comments on the same PR serialize instead of racing on force-push.

The scan also performs **cross-source dedup**: a candidate is dropped if its `paper_id` or `arxiv_id` already appears in any existing analysis file's frontmatter. This prevents double-coverage when a paper exists both as an arXiv preprint and a peer-reviewed venue copy with different filename prefixes.

`<id>` accepts: arXiv id (`2401.09670`), Semantic Scholar paperId (40-hex or its 7-char prefix), or a repo-relative file path.

How the bot finds the right commit: each per-paper commit has a `paper-id: <ss_paperId>` trailer and (when available) an `arxiv-id:` trailer in its message; `git_ops.find_by_trailer` greps for either.

- Config (venues, since_year, blocklist, per-run cap, allowed topics): `.github/paper-bot/sources.yaml` — edit this rather than the Python code for routine tuning.
- Prompts: `.github/paper-bot/prompts/{classify,analyze,refine}.md`.
- Code: `scripts/paper_bot/` (pure Python, stdlib + openai/pyyaml only). Layered as `semscholar.py` (Semantic Scholar Graph API fetcher) → `pipeline.py` (orchestration) → `deepseek.py` (LLM client) → `render.py` (markdown) → `git_ops.py` (commits/fixups/reverts) → `main.py` (scan entry) / `review.py` (review entry).
- Bot output goes to `<topic>/<system-slug>/<short-id>-<title>.md` (`<short-id>` is arxiv id when present, else 7-char paper-id prefix) and a link is appended to `<topic>/README.md` *above* a `<!-- paper-bot:end -->` marker. Hand-curated entries should stay above that marker.
- Dedup is filesystem-based: a paper's short-id existing anywhere outside `.git/`, `.github/`, `scripts/` means "already processed". Deleting a generated file → it gets re-analyzed next run.
- Local dry-run: `PYTHONPATH=scripts DRY_RUN=1 python -m paper_bot.main` (fetch + sort + filter only, no DeepSeek calls, no key needed). Real run requires `DEEPSEEK_API_KEY` env var.
- Required repo secret: `DEEPSEEK_API_KEY`. Semantic Scholar API is key-less. PR creation, comment posting, and force-push all use the default `GITHUB_TOKEN`; no PAT needed.

## What this repo is *not*

The placeholder subdirectories under `orchestration-scheduling/` (e.g. `google-borg/`, `apache-mesos/`) currently contain only `.gitkeep` — treat them as reserved space for hand-written or bot-generated deep-dives, not as missing implementation. Do not add build/CI/linter scaffolding for the *content* layer (markdown index); the only code in this repo is the paper-bot pipeline above.
