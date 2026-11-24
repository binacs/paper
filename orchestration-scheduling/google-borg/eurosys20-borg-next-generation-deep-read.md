---
title: 'Borg: the Next Generation'
authors:
- Muhammad Tirmazi
- Adam Barker
- Nan Deng
- Md E. Haque
- Zhijing Gene Qin
- Steven Hand
- Mor Harchol-Balter
- John Wilkes
affiliations: 'Google, Harvard University, University of St Andrews, Carnegie Mellon University'
venue: 'EuroSys'
year: 2020
doi: 10.1145/3342195.3387517
abs_url: https://dl.acm.org/doi/10.1145/3342195.3387517
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/5532.pdf
code_url: https://github.com/google/cluster-data
note_type: deep-read
written_at: '2026-11-25'
---

# Borg: the Next Generation

> **Why it matters:** It publishes and characterizes the 2019 Borg trace (eight cells, May 2019), and its findings (extreme heavy tails, heavy over-commitment, kills that are really dependency cleanup, effective vertical autoscaling) correct conclusions that a decade of work drew from the 2011 trace.

## Problem

The 2011 Google trace (one cell, one month) became a standard input for cluster-scheduling research, but it was old, covered a single cell, and lacked information needed to interpret it. For example, it carried no job-dependency data, so prior studies read many terminations as failures (§5.2). Borg had also gained new features since 2011: alloc sets, a mid tier, multiple schedulers including a batch scheduler, and Autopilot vertical scaling (§2, §3). The paper describes a new trace covering these features and asks what changed in utilization, scheduling load, job-size distribution and autoscaling between 2011 and 2019.

## Core design

This is a measurement paper. The "design" is the trace's data model and the Borg mechanisms it exposes.

**Borg model (§2).**
- A *cell* is a logically centralized Borgmaster plus many machines, each running a local agent. Users submit *jobs* made of *tasks*. The scheduler places each task on a machine with enough free resources.
- Each task has a resource *limit*. Memory limits are generally hard bounds, while CPU is usually work-conserving.
- Priority tiers in the 2019 trace: free (≤99), best-effort batch "beb" (110–115), mid tier (116–119, new since 2011), production (120–359) and monitoring (≥360). The paper folds monitoring into production.

**New trace content (§3, Table 1).**
- *Alloc sets*: reserved resource slots ("alloc instances") on machines that jobs' tasks can be placed into. They are used to reserve capacity ahead of a workload, hold it while jobs restart, or co-locate tasks of different jobs. Jobs and alloc sets together are called *collections*.
- *Parent–child dependencies*: a child job is killed automatically when its parent terminates. This simplifies cleanup for MapReduce-style pipelines. Kills are either direct (a user RPC to the Borgmaster) or indirect (the parent exited).
- *Batch queueing*: multiple schedulers, including a batch scheduler; the paper says Omega inspired this. Jobs may wait in a queued state on purpose (§6.3).
- *Vertical scaling*: each job is marked as not autoscaled, fully autoscaled, or constrained (autoscaled within limits) by Autopilot (§8).
- *CPU usage histograms*: a 21-element histogram of CPU utilization per 5-minute sample, biased toward high percentiles.
- *Units*: Borg allocates CPU in Google Compute Units (GCUs), mapped onto physical cores per machine type. The trace rescales by the largest machine, so Normalized Compute Units (NCU) and memory units (NMU) lie in 0–1. Only relative comparisons are meaningful.
- *Format*: BigQuery tables instead of CSV files. Raw sparse priorities (0–450) replace the 2011 mapping onto 0–11.

**Analysis method.**
- §4–§6 measure usage and allocation by tier, evictions and kills, arrival rates, and scheduling delay (ready until first task running, excluding deliberate batch-queue waits).
- §7 integrates each job's usage over time (NCU-hours, NMU-hours), fits a Pareto tail to "large" jobs (>1 unit, up to the 99.99th percentile), and reasons about queueing with the M/G/1 Pollaczek–Khinchine formula, where E[delay] grows with (C²+1)/2.
- §8 compares peak NCU slack (allocation minus peak observed usage in a 5-minute sample, floored at 0, as a fraction of allocation) across the three autoscaling modes.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Trace scope | 8 cells, 31 days, 96.4k machines (12.0k per cell) | 2019 vs 2011: 1 cell, 30 days, 12.6k machines | Table 1 |
| Hardware platforms / machine shapes | 7 / 21 | 2019 (2011: 3 / 10) | Table 1 |
| Trace size | ~350 GiB compressed per cell; 2.8 TiB total | 2019 (2011: ~40 GiB per cell) | §3, §9 |
| beb tier usage | ~20% of cell capacity | CPU and memory | §4 |
| Allocation level | "well above 100%" of deployed capacity | CPU and memory, all tiers | §4 |
| beb memory allocation in one cell | ~140% of cell memory capacity | cell c, beb tier only | §4 |
| Production usage vs allocation | ~30% (CPU), ~65% (memory) | production tier | §4 |
| Median machine utilization increase | 20–40% (CPU), 3–30% (memory) | 2019 vs 2011 | §4.1 |
| Alloc-set share | 2% of collections; 20% of CPU and 18% of RAM allocations | 2019 | §5.1 |
| Jobs in alloc sets | 15% of jobs, 95% of which are production tier | 2019 | §5.1 |
| Avg memory utilization | 73% (jobs in allocs) vs 41% (other jobs) | 2019 | §5.1 |
| Collections with any eviction | 0.79M of 24.8M; 96.6% of those non-production | 2019 | §5.2 |
| Production collections with any eviction | <0.2% | priority ≥120 | §5.2 |
| Kill rate by parent status | 87% (has parent) vs 41% (no parent) | jobs, 2019 | §5.2 |
| Job arrival rate, mean | 964 → 3360 jobs/hour (3.5×) | 2011 → 2019, per cell | §6.1 |
| Job arrival rate, median | 885 → 3309 jobs/hour (3.7×) | 2011 → 2019 | §6.1 |
| Median task scheduling rate increase | ~3.6× | all tasks | §6.2 |
| Resubmitted : new task rate (medians) | 0.66:1 → 2.26:1 | 2011 → 2019 | §6.2 |
| Tasks per job, 95th percentile | 498 (beb), 67 (mid), 21 (free), 3 (production) | 2019 | §6.3 |
| C² of per-job usage | 23k (CPU), 43k (memory) | 2019 | §7 |
| Compute–memory correlation | Pearson 0.97 | jobs bucketed by 1 NCU-hour | §7.2 |
| Autoscaling effect | peak NCU slack reduced by >25% for the vast majority of jobs | fully autoscaled vs manual | §8 |

## Limitations

- Resource values are normalized to 0–1 and obfuscated, so absolute capacity, cost or per-core figures cannot be recovered (§3).
- Many key results (tier utilization and allocation over time, per-cell CCDFs, scheduling-delay distributions, slack CCDFs) appear only in figures. The text gives few absolute delay values; §6.3 says only that median delays decreased while the tail is longer for "the last 28% of jobs."
- The paper explains implications rather than solving them: §7.3 explicitly stops short of a scheduler design, and §10 lists open problems (explainable scheduling, limits of over-commitment, gang scheduling, why average utilization stays low, mice/hog isolation, inter-cell variation).
- §9 admits that most logical invariants checked during trace generation (e.g., instance usage below machine capacity) were occasionally violated, so the data carries some known inconsistencies.
- One month in eight Google cells, with considerable variation between cells.
- Internal inconsistencies:
  - The Introduction says tasks to schedule rose "by a factor of 7," while §6.2 gives about 3.6× for all tasks.
  - The Introduction's "3.7×" job-rate increase is the median; the mean in §6.1 is 3.5×.
  - Table 2 prints the 2011 mean as exactly 3.00 for both NCU-hours and NMU-hours, which may be a copy error.
  - §7.1 says 2011 C² is "about 4 times lower" than 2019. The Table 2 C² row did not extract cleanly, so this note does not check the factor.

## Relation to other systems

- **2011 Google trace and its analyses:** same scheduler lineage, but one cell, no dependency, alloc or autoscaling data, and mapped priorities. The paper argues this missing data inflated reported failure rates (§5.2). The 2011 trace's "1.4–6.8× higher" unsuccessful-termination claim from prior work is attributed to user kills rather than failures.
- **Omega:** the paper credits Omega with inspiring Borg's multiple-scheduler support, which the 2019 trace exposes through batch queueing (§3).
- **Autopilot:** Borg's vertical autoscaler, described in a companion paper. Here it is studied only through its outcome, slack reduction (§8). The paper uses "vertical autoscaling" in the same sense as Kubernetes.
- **Azure / Resource Central traces:** the paper notes that Azure's VM traces (2017 and 2019, ~2M and ~2.6M VMs over 30 days) support history-based prediction, likened to Autopilot (§11). (Own analysis) Azure's traces are VM-level, while Borg's are job/task-level with priorities and dependencies.
- **Alibaba traces:** 2017 (~1,300 machines, 12 hours) and 2018 (~4,000 machines, 8 days), the latter used for task-dependency analysis (§11). (Own analysis) Borg 2019 is far larger per cell and longer, and adds explicit tiering and autoscaling labels.
- **Mesos and YARN:** cited only as other modern cluster managers (§1). The paper makes no workload comparison with them.

## Takeaways for practice

- (Own analysis) Plan for over-commitment as the normal state: allocation sits well above capacity, while production CPU usage is ~30% of its allocation. Admission and eviction policies need to treat limits as soft for CPU.
- (Own analysis) Isolate or prioritize "mice" against "hogs." With C² in the tens of thousands, M/G/1 reasoning (§7.3) says FIFO-like queueing hurts small jobs even at low load. Because CPU and memory hogs are the same jobs (Pearson 0.97), one hog-handling policy can cover both.
- (Own analysis) Record dependency and kill-cause metadata. Without parent links, cascaded cleanup kills look like failures and distort reliability metrics.
- (Own analysis) Reservation primitives (alloc sets) take a share of allocation far larger than their share of collections. They also show higher memory utilization, so they deserve first-class scheduler support.
- (Own analysis) Default to vertical autoscaling: fully autoscaled jobs show clearly lower peak slack than manually sized ones (§8).
- (Own analysis) Size scheduler throughput for rescheduled tasks, not only new submissions, and validate trace-driven results across several cells.

## References

- Paper (ACM DL): https://dl.acm.org/doi/10.1145/3342195.3387517
- Paper (Google Research): https://research.google/pubs/borg-the-next-generation/
- PDF: https://storage.googleapis.com/gweb-research2023-media/pubtools/5532.pdf
- Trace data and documentation (cited as [37] in the paper): https://github.com/google/cluster-data
