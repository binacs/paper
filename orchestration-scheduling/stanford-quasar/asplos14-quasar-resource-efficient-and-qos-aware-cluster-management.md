---
title: 'Quasar: Resource-Efficient and QoS-Aware Cluster Management'
authors:
- Christina Delimitrou
- Christos Kozyrakis
affiliations: 'Stanford University'
venue: 'ASPLOS'
year: 2014
doi: 10.1145/2541940.2541941
abs_url: https://doi.org/10.1145/2541940.2541941
pdf_url: https://mast.stanford.edu/pubs/quasar_resource_efficient_and_qos_aware_cluster_management/paper.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Quasar: Resource-Efficient and QoS-Aware Cluster Management

> **Why it matters:** Quasar replaces user resource reservations with performance targets and uses collaborative filtering over a few seconds of profiling to decide jointly how much of which resources each job gets and where it runs. That made "performance-centric" scheduling a concrete, reproducible design point.

## Problem

Reservation-based cluster managers (Mesos, Borg, Torque, Omega) ask users how many cores and how much memory a job needs. Users get this badly wrong. On a Twitter production cluster managed with Mesos, aggregate CPU utilization stays below 20% while reservations reach up to 80% of capacity. 70% of workloads overestimate reservations by up to 10x, and 20% underestimate by up to 5x (Sec. 1, Fig. 1). A cited Google/Borg study reports 25-35% CPU and 40% memory utilization, against reservations above 75% and 60% (Sec. 1).

The deeper issue (Sec. 2.2, Fig. 2) is that a job's performance depends on many coupled factors: server type, co-located interference, resources per node (scale-up), node count (scale-out) and dataset. Treating sizing (allocation) and placement (assignment) as separate steps, or leaving sizing to users, loses both efficiency and QoS.

## Core design

### Performance-centric interface (Sec. 3.1)
Users state a target instead of a reservation:
- Latency-critical services: a QPS target plus a latency QoS constraint.
- Distributed batch frameworks (Hadoop, Spark, Storm): execution time.
- Single-node jobs: an instructions-per-second target.
- Best-effort, low-priority jobs fill leftover capacity. They "may be migrated or killed at any point" (Sec. 5) and are evicted when a high-priority job needs the server (Sec. 4.1).

### Classification via collaborative filtering (Sec. 3.2)
- The problem is split into four independent classifications that run in parallel: **scale-up**, **scale-out**, **heterogeneity** and **interference**. Each is a sparse matrix with workloads as rows and configurations as columns (resource vectors, node counts, server types, interference sources and intensities).
- Missing entries are filled by SVD plus PQ-reconstruction trained with SGD, the Netflix-style recommender approach. Earlier, densely profiled workloads supply the latent structure.
- Profiling of a new job is short and sandboxed:
  - **Scale-up:** two random allocations on the highest-end platform. memcached runs 5-10 s under live traffic. Hadoop runs 2-6 map tasks until they reach 20% completion.
  - **Scale-out:** one extra run, on one to four nodes online.
  - **Heterogeneity:** one run on a different, randomly chosen server type.
  - **Interference:** reuses a scale-up copy and injects contentious microbenchmarks (cache, memory capacity/bandwidth, storage/network bandwidth, CPU), raising intensity until QoS drops by about 5%.
- Two entries per row is the chosen density: one entry gives high error, and gains flatten after 4-5 (Fig. 3).
- Splitting into four small problems is more accurate than one exhaustive joint classification (Table 2).

### Greedy joint allocation and assignment (Sec. 3.3)
- Classification output ranks servers by decreasing "resource quality" (fast platform, little interference for this job's sensitivities).
- The scheduler looks for the smallest allocation that meets the target. It scales up first, packing work into few high-quality servers, then scales out. In the paper's example, a webserver needing 100K QPS on servers that each deliver at most 20K QPS gets five servers.
- Decisions take a few ms even with thousands of servers. Admission control prevents oversubscription.
- Jobs are placed one at a time in arrival order. Global reshuffling is not implemented.

### Runtime adaptation and implementation (Sec. 4)
- **Monitoring loop:** a job that falls below its target has had a phase change or was misclassified. Quasar first scales resources up or down in place, and only then scales out or migrates, adjusting "in a conservative manner" (Sec. 4.1).
- **Proactive phase detection:** periodically re-profiles a sample of active workloads (Sec. 4.1).
- **Sandboxed profiling:** Linux containers with chroot and copy-on-write filesystem snapshots, so training copies have no side effects (Sec. 4.2).
- **Straggler detection for Hadoop:** flags tasks at least 50% slower than the median, reclassifies them in place, and marks them as stragglers if the result differs from the original by more than 20% (Sec. 4.3).
- **Integration:** 100-600 LOC per framework, with no application changes (Sec. 4).
- **Scheduler fault tolerance:** a single scheduler server with master-slave mirroring and hot standbys. ZooKeeper is suggested for multiple active schedulers (Sec. 4.4).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Twitter/Mesos aggregate CPU utilization | consistently below 20%, reservations up to 80% | 30-day production trace | Sec. 1, Fig. 1a |
| Reservation misestimation | 70% overestimate (up to 10x), 20% underestimate (up to 5x) | Twitter cluster | Sec. 1, Fig. 1d |
| Performance variability from server configuration | up to 7x | Hadoop | Sec. 2.2, Fig. 2 |
| Classification error | avg < 8%, max < 17% | 40-server local cluster validation | Sec. 3.2, Table 2 |
| Profiling time | < 5 min in all cases, 10-15 s for non-stateful batch | per new workload | Sec. 3.4 |
| Classification / scheduling decision time | a few ms | thousands of apps/servers | Sec. 3.2, 3.3 |
| Single Hadoop job execution time | -29% avg, up to -58%, within 5.8% of target (Hadoop default deviation 23%) | 10 Mahout jobs | Sec. 6.1, Fig. 5 |
| Multi-framework mix performance | +27% avg, within 5.3% of constraints | 16 Hadoop + 4 Storm + 4 Spark + single-node jobs | Sec. 6.2, Fig. 6 |
| CPU utilization, multi-framework | 62% (Quasar) vs 34% (framework schedulers) | same | Sec. 6.2, Fig. 7 |
| HotCRP best-effort runtimes | within 5% of min (Quasar) vs 24% (auto-scale) | flat load | Sec. 6.3, Fig. 8a |
| HotCRP QPS under fluctuating load | auto-scale 18% lower QPS on avg | fluctuating load | Sec. 6.3, Fig. 8b |
| Requests meeting latency QoS | memcached 98.8% vs 80%; Cassandra 98.6% vs 93% (Quasar vs auto-scale) | 24 h runs, 1 TB / 4 TB state | Sec. 6.4, Fig. 9 |
| Performance vs target, large scale | 98% (Quasar), 83% (reservation+Paragon), 62% (reservation+LL) | 1,200 workloads, 200 EC2 servers, 14 types | Sec. 6.5, Fig. 11 |
| CPU utilization, large scale | 62% (Quasar) vs 15% (reservation+LL) | same | Sec. 6.5 |
| Allocated minus used | roughly 10% | same | Sec. 6.5 |
| Management overhead | 4.1% of execution time avg, up to 9% for short batch jobs | same | Sec. 6.5 |
| Phase-change detection | 94% (reactive), 78% proactively with 8% false positives | sampling 20% of workloads every 10 min | Sec. 4.1 |
| Straggler detection | 19% earlier than Hadoop, 8% earlier than LATE | Hadoop | Sec. 4.3 |

**Inconsistency note:** The abstract says Quasar "improves resource utilization by 47%" in the 200-server EC2 cluster. Sec. 6.5 says the reservation+LL baseline reaches 15%, "47% lower than Quasar," whose average is 62%. The paper never says whether the 47% is a relative change or a percentage-point gap. (Own analysis) Given the two stated averages, the percentage-point reading looks more likely, so treat "47%" with care. The "62%" figure also appears in both Sec. 6.2 and Sec. 6.5, against different baselines (34% and 15%) in different experiments.

## Limitations

- **Arrival-order greedy placement.** Jobs are placed one at a time, so early arrivals can grab top-quality servers. Prioritized reassignment is only suggested (Sec. 3.3).
- **No load prediction** for user-facing services. Adaptation to load swings is reactive (Sec. 4.1).
- **No fault zones.** Placement ignores fault zones, and the scheduler is a single mirrored master (Sec. 4.4).
- **Stateful profiling is slow.** Services like Cassandra need setup to finish before profiling, at most 3-5 minutes (Sec. 3.2).
- **Workload-history assumption.** (Own analysis) Accuracy relies on enough densely profiled earlier workloads to fill the matrix. A cluster with a new kind of workload, such as accelerator jobs, starts cold.
- **Resource model.** (Own analysis) The model covers CPU, memory, storage and network on CPU servers. GPUs, NUMA topology and network locality between distributed tasks are not modeled.
- **Best-effort jobs absorb the slack.** Utilization gains come partly from co-located best-effort work that can be evicted or killed (Sec. 4.1, 5). How well this works depends on how much low-priority work the cluster has.
- **Short evaluation scale.** At most 200 EC2 servers in the evaluation. (Own analysis) Behaviour at Borg scale and the cost of the online SVD/SGD there are not shown.

## Relation to other systems

- **Mesos / Borg / Omega / Torque:** reservation-based. Mesos makes offers that frameworks accept or reject. Quasar removes the reservation and derives allocations from targets (Sec. 1, 2.1).
- **Paragon (same authors):** the closest prior work. It uses the same collaborative filtering, but only for heterogeneity and interference-aware *assignment* of a fixed-size request. Quasar adds scale-up and scale-out classification, so it also decides *size*. In Sec. 6.5, reservation+Paragon reaches 83% of target against Quasar's 98%.
- **Auto-scaling (RightScale-style):** adds instances when load crosses a threshold. It is the main baseline in Sec. 6.3-6.4 and loses on QoS because it ignores scale-up and interference.
- **Bubble-Flux / CPI2 / DeepDive / Q-Clouds:** detect or react to interference, by throttling (CPI2), online memory-pressure probing (Bubble-Flux) or feedback (Q-Clouds). Quasar instead predicts interference sensitivity up front and avoids bad co-locations (Sec. 2.1).
- **Whare-Map and heterogeneity-aware placement:** predict the best server type for a workload. Quasar folds that signal into a joint decision with sizing and interference (Sec. 2.1).
- **Dejavu:** groups workloads into a few classes and reuses past allocations. Quasar classifies each workload individually (Sec. 2.1).

## Takeaways for practice

- Ask for SLOs, not cores. User reservations are noisy enough that a scheduler which infers resource needs from a target can raise utilization a lot without hurting QoS.
- Low-rank structure in workload behaviour is real. A few seconds of sandboxed profiling plus matrix completion gives usable predictions of scale-up, scale-out, server-type and interference sensitivity. Four small factored problems beat one big joint one (Table 2).
- Decide sizing and placement together. Scale up on high-quality nodes before scaling out, and rank nodes per job by predicted quality rather than by free capacity.
- Keep a feedback loop. Prediction errors and phase changes are caught by monitoring against the target, and the cheap fix (in-place resizing) comes before migration.
- Utilization claims depend on best-effort filler. Make eviction cheap and let high-priority jobs reclaim resources quickly.
- (Own analysis) The design carries over to GPU/LLM serving clusters only if the classifiers are extended to accelerator-specific axes: GPU type, MIG/MPS partitions, interconnect topology and KV-cache memory. Expect a cold-start period while profiling history builds up.

## References

- Paper: https://mast.stanford.edu/pubs/quasar_resource_efficient_and_qos_aware_cluster_management/paper.pdf
- DOI: https://doi.org/10.1145/2541940.2541941
