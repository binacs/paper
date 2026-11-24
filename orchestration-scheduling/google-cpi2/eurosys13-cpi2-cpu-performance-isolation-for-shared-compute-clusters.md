---
title: 'CPI2: CPU performance isolation for shared compute clusters'
authors:
- Xiao Zhang
- Eric Tune
- Robert Hagmann
- Rohit Jnagal
- Vrigo Gokhale
- John Wilkes
affiliations: 'Google'
venue: 'EuroSys'
year: 2013
paper_id: 8df87f9f18dc58c2cc88474c2b9e1c30654c60e8
doi: 10.1145/2465351.2465388
abs_url: https://research.google/pubs/cpi2-cpu-performance-isolation-for-shared-compute-clusters/
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/40737.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# CPI2: CPU performance isolation for shared compute clusters

> **Why it matters:** Google's CPI² showed that interference can be detected and contained in production with cheap, always-on hardware counters, using job-level statistics and a CPU cap and no hardware partitioning. It is the baseline later co-location controllers measure themselves against.

## Problem

Google's clusters mix latency-sensitive production jobs, which are provisioned for peak load, with overcommitted batch work running in the spare capacity (§2). Cgroups isolate CPU time and memory, but Linux does little to protect shared processor resources such as caches and memory buses. A co-runner's cache or memory-bus behaviour can therefore slow a victim without changing the victim's CPU allocation. At this scale, operators cannot chase these outliers by hand.

The paper covers CPU-level interference between jobs only. Network and disk interference, and root-causing the exact hardware resource, are out of scope (§2).

## Core design

### Why CPI is the signal

- Most of Google's work runs as large jobs of identical tasks. 96% of tasks belong to jobs with at least 10 tasks, and 87% to jobs with at least 100 (§2). A job's own tasks therefore give a statistical baseline for "normal" on each platform.
- For many jobs, CPI tracks application-level performance closely. Batch transactions per second track instructions per second (Fig. 2), and web-search leaf latency tracks CPI (Fig. 3). The application needs no instrumentation.
- CPI works poorly for jobs whose latency is dominated by other nodes, such as a search root that waits on leaves (Fig. 4).

### Collection and aggregation (§3, Fig. 6, Table 2)

- CPI is computed as `CLK_UNHALTED.REF / INSTRUCTIONS_RETIRED`, counted per cgroup with `perf_event` in counting mode, not sampling mode.
- Each machine's agent samples for 10 s once a minute. Each record holds job name, platform, timestamp, CPU usage and CPI.
- A central aggregator builds a "CPI spec" (mean and standard deviation) for each job on each hardware platform, keyed by job × CPU type. It needs at least 5 tasks and 100 samples per task.
- Specs are recomputed every 24 hours (hourly was the goal). The previous day's value is weighted by about 0.9 before it is averaged with new data, so older history decays.
- The CPI distributions are skewed. A generalised extreme value (GEV) distribution fit best of the candidates tried: normal, log-normal, Gamma and GEV (Fig. 7, §4.1).

### Outlier detection (§4.1)

- A sample is an outlier if its CPI is above the job's mean + 2σ for that platform, which flags about 5% of samples.
- Samples from tasks using less than 0.25 CPU-sec/sec are ignored. Case 3 (§6.1) motivated this floor: a task's own bimodal CPU usage made its CPI swing, and that looked like interference.
- A task is declared a victim only after at least 3 outlier flags within 5 minutes. This damps transient noise.

### Antagonist identification by correlation (§4.2)

- The method is passive. Over a 10-minute window, the victim's CPI is correlated with each co-tenant's CPU usage, instead of throttling suspects one at a time to test them.
- Each suspect's usage series `u_i` is normalised to sum to 1. For each time-aligned sample, the score adds `u_i · (1 − c_thr/c_i)` when the victim's CPI `c_i` is above the threshold, and `u_i · (c_i/c_thr − 1)` when it is below. The score lies in [−1, 1].
- A suspect becomes an antagonist when its score is at least 0.35. One analysis costs about 100 µs, and at most one runs per second.
- The method cannot see a group of antagonists that cause harm only together.

### Remedy: hard-capping, and the policy around it (§5)

- The antagonist's cgroup is hard-capped with CPU bandwidth control: for example, 25 ms of CPU in every 250 ms window, about 0.1 CPU-sec/sec. Best-effort batch is capped at 0.01 CPU-sec/sec and other jobs at 0.1. Each cap lasts 5 minutes.
- The policy favours latency-sensitive jobs over batch. A cap is applied automatically only when the antagonist choice is confident and the victim is eligible, meaning latency-sensitive or explicitly opted in.
- If the victim's CPI stays high, the analysis reruns, and a suspect that was already throttled is less likely to be picked again.
- Operators can cap suspects manually and switch protection on or off per cluster. Killing or migrating a persistent antagonist is left to operators and the scheduler, not automated.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| CPI vs. latency correlation | 0.97 | Web-search leaf job | §3, Fig. 3 |
| TPS vs. IPS correlation | 0.97 | 2,600-task batch job | §3, Fig. 2 |
| CPI vs. performance, compute-heavy jobs | 0.68–0.75 | Several production jobs | §3, Fig. 4 |
| Tasks in jobs with ≥10 / ≥100 tasks | 96% / 87% | Production clusters | §2 |
| Sampling overhead | < 0.1% CPU | 10 s of counting each minute | §3 |
| Outlier rule | > 2σ; 3 flags in 5 min | Per job × platform | §4.1, Table 2 |
| Correlation threshold / analysis cost | 0.35 / ~100 µs | 10-minute window | §4.2, Table 2 |
| Cap | 0.1 CPU-sec/sec (0.01 for best-effort) for 5 min | Antagonist cgroup | §5, Table 2 |
| Antagonist identifications | 0.37 per machine-day | All production machines | §7 |
| Manual caps evaluated | ~400 | 5-minute caps | §7 |
| Victim CPI after one cap | 0.82× non-production, 0.52× production | True-positive cases | §7.2, Fig. 15(b) |
| L3 misses/instruction vs. CPI improvement | 0.87 correlation | Throttling events | §7.2 |
| Antagonist identification true-positive rate | ~70% | Production jobs | §7.2, Fig. 16(a) |
| Median production victim CPI | 0.63× of pre-throttle | Top suspect capped | §7.3, Fig. 16(d) |
| Case 2 victim CPI | ~2.0 → ~1.0 | Cap from ~15:35 to 15:49 | §6.1, Fig. 9 |

## Limitations

- **CPU-only and indirect.** It covers neither disk nor network I/O. It finds a culprit job but never names the contended resource, though the L3-miss correlation hints at the cache.
- **Requires replicated jobs.** Specs need at least 5 tasks. Small or one-off jobs, and jobs whose behaviour varies (many non-production jobs), get weak baselines. Jobs bounded by remote latency, such as a root node, correlate poorly with CPI.
- **Correlation, not causation.** True-positive rate is about 70% for production jobs (§7.2). Groups of antagonists go unseen. In Case 4 (§6.1), several suspects scored high, only one could be throttled, and migrating the victim would have worked better.
- **Crude actuator.** Fixed caps of fixed length. Antagonists react: in Case 5 a batch job grew from about 8 to about 80 threads under the cap (Fig. 12), and in Case 6 a MapReduce worker exited (Fig. 13). Feedback-driven throttling is listed as future work (§9).
- **Partial rollout.** Detection ran on all production machines, but automatic enforcement was not widely deployed. The capping results come from manual caps (§7).

## Relation to other systems

- **Heracles (ISCA 2015, Google/Stanford).** Heracles is a feedback controller for one latency-critical service plus best-effort tasks. It manages CPU, memory and network isolation together and reports 90% average server utilization with no latency violations (abstract). CPI² is reactive: it detects a victim, then caps a culprit. Heracles is proactive: it keeps adjusting allocations against an SLO signal from the service itself.
- **PARTIES (ASPLOS 2019).** PARTIES handles multiple latency-critical services per server. Every 500 ms it measures each service's tail-latency slack, then resizes cores (cpusets), LLC ways (Intel CAT), per-core frequency, memory capacity, disk and network. It reports about 61% higher throughput under QoS than existing managers. CPI² has one actuator (a CPU cap on the antagonist) and protects victims without partitioning. PARTIES partitions every major resource continuously and migrates a service when QoS can't be met within a minute.
- **Borg (EuroSys 2015).** Borg is the cluster manager CPI² runs under. Its abstract cites "process-level performance isolation" alongside overcommit and machine sharing, and it is the overcommit that makes CPI² necessary. CPI² is the per-node safety net for Borg's packing decisions. Borg-level placement, such as migration or antagonist-aware scheduling, is what CPI² §9 asks for.
- **Quasar (ASPLOS 2014).** Users give performance targets, not reservations. Quasar profiles each job briefly and uses collaborative filtering to estimate scale-up, scale-out, heterogeneity and interference sensitivity, then allocates and places jobs together. It reports 47% higher utilization on a 200-server EC2 cluster. Quasar tries to avoid interference at placement time. CPI² accepts any placement and repairs interference at run time. The two are complementary.
- **Linux CFS bandwidth control (kernel.org docs).** This is the kernel mechanism CPI²'s cap maps onto. In cgroup v1, a group gets `cpu.cfs_quota_us` of runtime per `cpu.cfs_period_us`: the default period is 100 ms, the bounds are 1 ms to 1 s, and the default quota of −1 means no limit. Threads that exhaust the quota are throttled until the next period. In cgroup v2 the same control is `cpu.max` (`$MAX $PERIOD`, default `max 100000`), and `cpu.stat` reports `nr_throttled` and throttled time. CFS bandwidth control is only the actuator: it decides neither whom to throttle nor when. CPI² supplies that policy.

## Takeaways for practice

- Large replicated jobs give each job its own control group. Baselining per job × hardware platform beats any global threshold. Keep the platform in the key, because CPI is not comparable across CPU generations.
- Always-on counting-mode PMU sampling (10 s per minute, < 0.1% overhead) is affordable. Collect it everywhere, even before enforcement exists.
- Require persistence before acting (3 flags in 5 min), filter low-usage noise, and gate automatic action on victim class and confidence. Ship with manual and per-cluster switches.
- Passive correlation is cheap enough to run every second. Accept a ~70% hit rate, but make the actuator reversible and short-lived.
- Throttling triggers reactions such as thread explosions and task exits. Watch what antagonists do under caps, and prefer graduated, feedback-driven throttling or migration for chronic cases.

## References

- Paper: https://research.google/pubs/cpi2-cpu-performance-isolation-for-shared-compute-clusters/ (PDF: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/40737.pdf)
- Heracles: https://research.google/pubs/heracles-improving-resource-efficiency-at-scale/
- PARTIES: https://www.csl.cornell.edu/~delimitrou/papers/2019.asplos.parties.pdf
- Borg: https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/
- Quasar: https://www.csl.cornell.edu/~delimitrou/papers/2014.asplos.quasar.pdf
- CFS bandwidth control: https://docs.kernel.org/scheduler/sched-bwc.html ; cgroup v2: https://docs.kernel.org/admin-guide/cgroup-v2.html
