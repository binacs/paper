# paper-bot: why PRs piled up, and what changed

_Written 2026-11-25 as part of the `duet/paper-bot-dedup` PR._

## What went wrong (2026-w37 → 2026-w48)

Ten paper-bot PRs were open at once (#14, #15, #17–#24). Looking at their files:

| Paper | PRs that carried it |
|---|---|
| Elastic Sketch (SIGCOMM 2018) | #15 #17 #18 #19 #20 #21 #22 #23 #24 |
| Chameleon video analytics (SIGCOMM 2018) | #15 #17 #18 #19 #20 #21 #22 #23 #24 |
| ShrinkBench / pruning (MLSys 2020) | #15 #17 #18 #19 #20 #22 #23 #24 |
| Pond (ASPLOS 2023) | #15 #18 #19 #20 #22 #23 #24 |
| Philly GPU cluster analysis (ATC 2019) | #14 #17 #21 |
| Tiresias, SOCK, SAND | #21 |

So the backlog was really **one batch of ~8 papers, re-proposed every week**. Causes:

1. **Dedup only saw `main`.** Each week's branch starts from `main`; papers still sitting in last week's unmerged PR looked "new" again. The highest-cited unanalysed papers therefore won every week.
2. **Hand-curated README entries were invisible to dedup.** Only analysis-file frontmatter/filenames were checked, so e.g. MAST, MegaScale or Borg (README links, no analysis file) could be proposed again.
3. **Ranking was citations-only from 2018.** That surfaces old, well-cited but off-focus papers (video analytics, network sketches) ahead of recent cluster-scheduling / LLM-systems work.
4. **Abstract-only analyses.** When Semantic Scholar has a short or missing abstract (Tiresias, SOCK), the analysis is generic and partly wrong — e.g. the Tiresias note describes "consolidation/packing" but misses its actual core (2D-LAS / Gittins-index scheduling with discretised priority queues).
5. **Unstable classification.** The same paper got different folders across weeks (`google-pond` / `microsoft-pond`; Pond is a Microsoft Azure paper), so the PRs also disagree with each other.
6. **Review cost.** 4–8 papers per PR, each needing a judgment call, with no summary of where each would be filed. The PR body's copy-pasteable example (`/reject gpu-training/misc/2024-some-paper.md`) was posted verbatim once (#14).

## What this PR changes

| Change | Where | Effect |
|---|---|---|
| Dedup index (`dedup.py`) over analysis frontmatter **and** every topic README (arXiv ids, DOIs, Semantic Scholar ids, normalised titles) **and** the commit trailers of other open paper-bot PRs | `dedup.py`, `pipeline.hard_filter` | A paper is proposed at most once, and never if it is already hand-curated |
| Backlog guard `max_open_bot_prs: 1` | `sources.yaml`, `pipeline.run` | While an older paper-bot PR is open, the weekly run does nothing (no DeepSeek spend, no new PR). Merge/close it to resume |
| `max_candidates_per_run: 8 → 3` | `sources.yaml` | One small, reviewable batch per week |
| `min_abstract_chars: 400` | `sources.yaml`, `hard_filter` | Skips papers whose abstract is too thin for an abstract-only analysis |
| `focus_keywords` ranking | `sources.yaml`, `pipeline.rank` | Scheduling / GPU / LLM-serving / sandbox papers first; citations order within a group |
| PR body: summary table (id, title, venue, proposed topic/folder), placeholder-only command examples | `render.write_pr_body` | One-glance review |
| Prompt: only prefix `system_slug` with an org when it is unambiguous | `prompts/analyze.md` | Fewer `google-pond`-style misfilings |
| `rejected.txt`: Elastic Sketch, Chameleon, ShrinkBench (separate commit) | `rejected.txt` | Stops the three off-focus papers from coming back; drop that commit if you disagree |

**Not changed:** `.github/workflows/*.yml` (triggers, permissions, secrets all untouched). The new GitHub API read uses the `GH_TOKEN` that the scan job already exports, with the existing `pull-requests: write` permission (which includes read). If the token is missing or the call fails, the bot falls back to the old behaviour (no open-PR dedup, guard disabled).

## Operating it

- **To catch up:** merge or close the old paper-bot PRs; the next Monday run resumes automatically.
- **To get a bigger batch once:** run the workflow manually with `max_candidates` set.
- **To widen/narrow focus:** edit `focus_keywords` / `keyword_blocklist` in `sources.yaml`.
- Local dry-run (no key needed): `PYTHONPATH=scripts DRY_RUN=1 python -m paper_bot.main`. Without `GITHUB_REPOSITORY`/`GH_TOKEN` set locally, open-PR dedup and the guard are skipped.

## Further ideas (not implemented)

- Fetch the full text (arXiv HTML) for the analysis instead of the abstract only, or at least the introduction; would fix most "generic" notes.
- Add a one-line `why_it_matters` field to the analysis JSON and show it in the PR table.
- Mix a recency slot into each batch (e.g. 2 classics + 1 paper from the last 18 months) instead of a pure citation sort.
- Auto-close superseded paper-bot PRs with a comment (needs a policy decision; today closing is left to the owner).
