---
title: 'MAST: Global Scheduling of ML Training across Geo-Distributed Datacenters at Hyperscale'
authors:
- Arnab Choudhury
- Yang Wang
- Tuomas Pelkonen
- Kutta Srinivasan
- Abha Jain
- Shenghao Lin
- Delia David
- Siavash Soleimanifard
affiliations: 'Meta Platforms, The Ohio State University, LinkedIn'
venue: 'OSDI'
year: 2024
paper_id: c2862748733b65b261a5770eeee890803af31e01
abs_url: https://www.usenix.org/conference/osdi24/presentation/choudhury
pdf_url: https://www.usenix.org/system/files/osdi24-choudhury.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# MAST: Global Scheduling of ML Training across Geo-Distributed Datacenters at Hyperscale

> **Why it matters:** It shows how to remove "pick a region" from the ML training user interface at hyperscale: a global job queue, region-level allocation, and a separate daily data-placement optimizer together keep GPU demand and supply balanced across tens of regions.

## Problem

Users used to pick regions for training data and jobs, as in public clouds, leaving some regions with long queues while others sat idle (§1). Incremental hardware purchases made the storage/GPU/CPU mix uneven across regions (Fig. 2). Two things make "just move the job" hard:

- **Data locality.** Cross-region bandwidth is ~10x below intra-region bisection bandwidth (§2); ML jobs must read inputs locally (§3.3). Partitions are shared by 3 / 17 / 45 workloads at P50 / P90 / P99 (Fig. 3), so moving one job's data moves many jobs.
- **Scale.** Exabytes in millions of tables and billions of partitions (§2); tens of thousands of workloads a day on O(100K) GPUs (§5.1). One fully global allocator does not scale.

A single workload never spans regions (gang-scheduled within one region, §2, §4.1); MAST balances *across* workloads.

## Core design

Three principles (§1): **temporal decoupling** (a slow path places data and machines ahead of time; a fast path places jobs in real time), **scope decoupling** (queueing is global, allocation is regional, container orchestration is per cluster), and **exhaustive search** (every eligible region computes a plan and the best one wins).

### Design space (Table 1, §4.1)
A 3x3 grid of queue scope × allocation scope (cluster/region/global). Borg, Hydra and Yugong are (1) cluster/cluster, the latter two binding jobs early by estimated load. MAST is (6): global queue, regional allocation; (9) is ideal but unscalable. MAST uses **late binding**: dispatch only when a cluster can start the job now.

### Slow path
- **RAS** (separate, cited system) pre-assigns a region's machines to *dynamic clusters* via a MIP about every 30 min (§2); RMS searches only ML dynamic clusters.
- **Tetris** (§3) runs daily and chooses each table's home region R(table_i). The MIP (Fig. 4) has:
  - Soft objectives: cross-region read volume (Expr. 1); per-GPU-type, per-priority GPU demand/supply balance with a sigmoid overload term that penalizes overload more than underload (Expr. 2, 7–8); storage balance (Expr. 3, 9).
  - Hard constraints: regional storage capacity (Expr. 4), per-application CPU quota (Expr. 5), and a threshold of high-priority GPU demand trained in its data's home region (Expr. 6, "training-at-home-region").
  - Key choice: **GPU balance is soft only.** A hard GPU constraint "often renders the problem unsolvable" because GPUs are scarce. Overload is absorbed by preempting low-priority work. Storage gets a hard quota plus soft balance. A hard storage balance was tried and rejected because it blocks moves toward high-demand regions.
  - Solver: NP-hard, so hill climbing (partly for interpretability), with daily moves capped by a cross-region bandwidth quota; replicate-then-delete (§3.4).
  - Replicas (§3.5): a DR replica per table plus extra replicas for hot tables (per GPU type) and non-colocated jobs. Replicas are what give a workload several candidate regions.

### Fast path
- **Global ML Scheduler (GMS, §4.2)** owns one queue ordered by `<priority, credit>`. Within quota a workload gets its tenant's priority; over quota it drops to lowest and runs preemptibly. Credit grows with age (capped) and favors tenants below average recent usage (Eq. 10–11). A periodic GMS-scan pass recomputes all tuples; GMS computes no placements.
- **Regional ML Schedulers (RMS, §4.3)** each take the top workload, check with Tetris's real-time component that the region has the data and GPU type, then plan: per job, evaluate every ML dynamic cluster and keep the best; the workload's Pscore is the sum over jobs. Machines are allocated in nearby-rack batches. RMSs **auction** the workload and the highest Pscore wins. Free-resource plans beat preemption plans; among the latter, fewer, lower-priority, longer-running victims win and new jobs are protected (one 12-GPU victim beats a 4- plus a 5-GPU victim for a 10-GPU ask). If no region can start it now, it waits.
- **Negative cache (§4.3):** within a scan, a failed request makes same-or-larger requests fail fast (~80% hit rate).
- **Twine (§4.4):** the winning RMS tells Twine to checkpoint/preempt victims, create containers and restore preempted jobs.
- **Fault tolerance (§4.5):** every layer is stateless over a replicated database.

The authors argue single-workload decisions match a global optimum, but concede joint multi-workload placement is not optimal (§4.1).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Most-overloaded region, high-priority GPU demand/supply | 2.63 → 0.98 | Tetris V0 (manual placement) → V1 (automated, 2022) | Abstract, §5.6 |
| Std. dev. of that ratio across regions | 0.76 → 0.30 | V0 → V1 | §5.6 |
| Collocation rate (redefined, high-priority GPU-hours) | 78% → 96% | V1 → V2 | §5.6 |
| Average GPU allocation rate | 98% | two-week window | §5.2, Fig. 5 |
| Data/GPU non-collocation | usually < 0.1% | production | §5.3, Fig. 6 |
| Workloads with ≥4 candidate regions | ~40% | 30 days | §5.3, Fig. 7 |
| Workloads executed in >1 region over the window | ~30% | 30 days | §5.3, Fig. 7 |
| Data moved by Tetris | hundreds of PB/day | production | §5.3, Fig. 8 |
| Extra storage from DR + hot replicas | ~75–125% | production | §3.5 |
| Table move time P50/P90/P99 | 2.1 h / 3.7 h / 4.9 h | daily migration | §3.4 |
| Tetris solve time | ~5 h, daily | hill climbing | §3.4, §5.3 |
| GPUs per GPU workload P50/P90/P99 | 16 / 64 / 128 | production | §5.1 |
| Scheduling attempts | ~100K/day | ~1 preemption per workload on average | §5.1 |
| GMS-scan pass | ~34 s for 6K–10K workloads; 8.8x headroom at a 5-min period | Python implementation | §5.4, Fig. 9 |
| RMS per-workload decision (slowest RMS) | ~1.3 ms without / 5.5 ms with preemption | production | §5.4, Fig. 10 |
| RMS headroom | ~12x (≈15M/day capacity vs 100K; sqrt due to quadratic growth) | analytic estimate | §5.4 |
| SLO-violation rate, MAST vs federated | < 1.3% vs up to 50% (high-priority, busy hours) | 8-hour trace, simulator | §5.6 |

## Limitations

- **No cross-region jobs.** A workload is confined to one region, and a job to one dynamic cluster. Spanning clusters needs Twine "virtual jobs", which are not integrated (§4.6). The largest LLM pretraining runs (tens of thousands of GPUs, §5.1) are therefore bounded by single-region capacity.
- **Serial RMS.** Each RMS decides one workload at a time (§4.6). RMS cost grows as O(D×J), quadratic in hardware (§4.3.1). GMS is in Python. Headroom is about 12x, not unlimited.
- **Greedy multi-workload placement.** Each workload goes to its best region, with no joint optimization (§4.1).
- **Slow path lags the fast path.** About 70% of jobs are first-time (§3.1). Unexpected one-off jobs can invalidate daily placements; feeding fast-path placements back into Tetris is future work (§6). Storage quota and cross-region bandwidth are still hard constraints, and replica count and home region are not chosen jointly (§6).
- **Evaluation caveats.** The headline 2.63 → 0.98 is Tetris V0 vs V1, not a full-system counterfactual; the federated comparison is simulated, with the SLO-violation criterion not precisely defined.

## Relation to other systems

- **Borg:** solution (1); the user picks the cell. MAST keeps Borg-style priority/quota/preemption but lifts the queue to global scope and owns region (and data) choice.
- **Twine (Meta, OSDI'20):** MAST runs *on* Twine, which orchestrates containers per dynamic cluster; ML policy lives above it in GMS/RMS (§2).
- **Kubernetes + Kueue-style queueing:** quota-aware admission queues (cohorts, borrowing) per cluster, roughly (1)/(3) here. Kueue's multi-cluster mode keeps whichever worker cluster admits first: late binding but first-fit rather than a scored auction, and with no Tetris-like data placement. The paper mentions Kubernetes only as a cluster manager one might keep unmodified under a global queue (§6).
- **Gödel (ByteDance, SoCC'23):** a unified Kubernetes-based online/offline scheduler *within* one very large cluster (dispatcher, optimistic-concurrency scheduler shards, conflict-resolving binder). It addresses the CM/RMS level; MAST addresses inter-region queueing and data placement. Complementary layers.
- **Hydra (Microsoft) / Yugong (Alibaba):** the closest prior work (§7). Both use early binding at cluster scope, ignore GPUs, and dispatch with simple heuristics. Yugong places data at the namespace/project level with hard quotas, which become infeasible under scarcity. Tetris places data at partition level, an optimization about 10⁶ times larger.
- **Singularity (Microsoft):** planet-scale preemptive, elastic AI scheduling via transparent checkpoint/migration; its policy is undisclosed, so the paper cannot compare (§7). Singularity bets on job mobility, MAST on data placement plus checkpoint restart.

## Takeaways for practice

- Separate **where data lives** from **where jobs run** in time: a slow optimizer (hours or a day) shapes the feasible set, and a fast scheduler (milliseconds) picks within it. Replicas are the lever that turns one feasible region into several.
- **Late binding beats load-estimate dispatch** when resources are gang-scheduled and scarce. Hold jobs in a global queue until some region can start them now. Federated early binding produced far more SLO violations in their simulator (§5.6).
- Make **GPU balance a soft objective** and back it with preemption. Hard GPU constraints make the solver infeasible under scarcity.
- Fan the plan computation out to regions and **auction** on a placement score. This scales better than one global allocator and keeps placement quality close to it for each decision.
- Plan for the quadratic: exhaustive search grows as O(D×J). Know your headroom and have sharding or parallel-RMS options ready.
- Single-region shops don't need this (§6); a global queue over unmodified cluster managers is the cheap first step.

## References

- Paper: https://www.usenix.org/conference/osdi24/presentation/choudhury
- PDF: https://www.usenix.org/system/files/osdi24-choudhury.pdf
- Code / blog: none official
