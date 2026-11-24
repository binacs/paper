---
title: 'PARTIES: QoS-Aware Resource Partitioning for Multiple Interactive Services'
authors:
- Shuang Chen
- Christina Delimitrou
- José F. Martínez
affiliations: 'Cornell University'
venue: 'ASPLOS'
year: 2019
doi: 10.1145/3297858.3304005
abs_url: https://dl.acm.org/doi/10.1145/3297858.3304005
pdf_url: https://www.csl.cornell.edu/~delimitrou/papers/2019.asplos.parties.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# PARTIES: QoS-Aware Resource Partitioning for Multiple Interactive Services

> **Why it matters:** It extends per-node resource partitioning from "one latency-critical (LC) service plus best-effort (BE) filler" (Heracles-style) to many LC services on one server, using a simple online feedback controller with no offline profiling.

## Problem

Datacenter co-location had mostly meant one LC service alongside BE batch jobs. Earlier approaches either kept LC services isolated, avoided risky co-locations, or partitioned resources for a single LC service per host. The paper argues that with the move towards interactive services and microservices, many latency-sensitive containers have to share a host. Each has its own tail-latency target (99th percentile, Table 2), and interference can come through cores, caches, memory bandwidth and capacity, disk and network (characterized in Section 3).

The goal: keep every co-located LC service within its QoS target while maximizing aggregate load, with no a priori knowledge of the applications.

## Core design

### Characterization findings that shape the controller (Section 3)
- Most applications are most sensitive to the resource they saturate. Core allocation matters most for most services.
- Sharing a hyperthread (time-sharing) is unacceptable for every service except MongoDB. PARTIES therefore never shares a physical core, since L1/L2 contention cannot be isolated.
- The evaluated platform has no direct memory-bandwidth partitioning. LLC way partitioning (CAT) is used to limit bandwidth contention indirectly.
- **Resource fungibility** (Section 3.4.3): several resource tuples meet QoS for the same app and load. Moses at high load meets QoS with <10 cores, 11 ways, turbo>, <14 cores, 11 ways, 1.8 GHz> or <14 cores, 2 ways, 2.2 GHz>. The controller therefore only needs to find *some* valid point, not the optimum, which keeps the search short.

### Resources and isolation mechanisms (Table 3)
| Resource | Mechanism | Step (Sec. 4.2.4 / 4.3) |
|---|---|---|
| Cores | cpuset cgroups (pin core IDs) | 1 physical core |
| LLC | Intel CAT way partitioning | 1 way |
| Frequency | ACPI frequency driver (userspace/performance governor) | 100 MHz |
| Memory capacity | memory cgroups | 1 GB |
| Disk bandwidth | blkio cgroups (read throttling) | 1 GB/s (as stated, see Limitations) |
| Network bandwidth | qdisc with HTB | 0.5 Gbps, handled outside the 10-action FSM (Sec. 4.2.1) |

Memory bandwidth is not partitioned directly.

### Control loop (Section 4)
- **Initialization:** fair allocation, so each app gets an equal share of every managed resource. There is no profiling except a one-second disk-bandwidth check at app start that classifies an app as in-memory (no I/O) or not.
- **Monitoring:** tail latency and resource utilization are sampled every **500 ms**. Latency is measured on the client side, through each service's workload generator.
- **Decision rule per interval:** compute each LC app's tail-latency slack.
  - If the lowest slack is below **5%**, upsize that app.
  - If the highest slack is above **20%**, downsize that app.
  - Only one resource is adjusted per interval.
- **Action space:** ten actions, <UP/DOWN, CORE/CACHE/FREQ/MEM/DISK>. Figure 4 gives the transitions.
  - Within each direction the resources are grouped into a *compute wheel* (cores, cache, frequency) and a *storage wheel* (memory, disk). The first resource to try is picked at random.
  - If an action doesn't help, the next interval moves to the next resource in the wheel. When the current wheel's options run out, the controller moves to the other wheel. After each turn of the compute wheel it checks memory utilization before deciding whether to go round again or jump to the storage wheel.
  - **Asymmetric reverting:** a downsize that hurts is reverted immediately, and downsizing that app is then disabled for 30 s. An upsize is *not* reverted, because the app may be short of several resources at once.
- **Where resources come from:** on an upsize, resources are always reclaimed from BE jobs first. Otherwise the victim is usually the LC app with the highest slack. For <UP, MEM> the victim is the app with the most memory-capacity slack. If the upsized app and the victim fight over the same resource in the same UP wheel (ping-pong), the victim moves on to its next resource. Downsized resources go to BE jobs if any exist, and otherwise stay idle.
- **Migration as last resort:** if no allocation meets every app's QoS within **one minute**, one app is migrated. Stateless services are preferred. If all are stateful, the app with the most relaxed QoS target goes. The paper says migrations are rare in practice and happen only when the server is oversubscribed.
- **Implementation:** a user-level runtime pinned to core 0. Language and code size are not stated.

### Evaluation setup (Sections 3, 5.1)
- One dual-socket Xeon E5-2699 v4 (22 cores/socket, 2 threads per core) with a 55 MB 20-way LLC, 128 GB DRAM, a 1 TB 7200 RPM HDD and 10 Gbps networking. It runs Ubuntu 16.04 with LXC containers (Table 1).
- Six LC services (Table 2): Memcached (key-value), Xapian (web search), NGINX (web server), Moses (real-time translation), MongoDB (persistent DB) and Sphinx (speech recognition). Load comes from open-loop generators (an in-house generator similar to mutilate, Tailbench, wrk2 and YCSB converted to open-loop) with exponential inter-arrivals and Zipfian popularity.
- One BE container: 14 threads of compute-intensive and 14 threads of memory-thrashing microbenchmarks.
- Mixes of 2 to 6 LC apps, each at 10–100% of max load in 10% steps. A run fails if no QoS-satisfying allocation is found within 1 minute.
- Baselines:
  - **Unmanaged**
  - **Heracles**, adapted by treating the strictest-QoS app as "the" LC app and the others as BE, with no partitioning among them
  - **Oracle**, which finds a viable allocation, if one exists, by exhaustive offline profiling
- Metric: **EMU** (effective machine utilization), the maximum aggregate load of all co-located apps, each counted as a percentage of its own max load. It can exceed 100%.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| QoS target (p99) / max load: Memcached | 600 µs / 1,280,000 RPS | standalone, knee of load curve | Table 2 |
| Xapian | 5 ms / 8,000 RPS | same | Table 2 |
| NGINX | 10 ms / 560,000 RPS | same | Table 2 |
| Moses | 15 ms / 2,800 RPS | same | Table 2 |
| MongoDB | 300 ms / 240 RPS | same | Table 2 |
| Sphinx | 2.5 s / 14 RPS | same | Table 2 |
| Monitoring / decision interval | 500 ms | controller | Sec. 4.2, 4.3 |
| Upsize / downsize slack thresholds | 5% / 20% | defaults | Sec. 4.2, 4.3 |
| Migration trigger | no valid allocation within 1 min | controller | Sec. 4.2.1 |
| Downsize lockout after revert | 30 s | per app | Sec. 4.2 |
| EMU vs Heracles, 2-app mixes | ~13% higher on average | all 2-app mixes | Sec. 5.2.2, Fig. 7 |
| EMU vs Heracles, 6-app mixes | ~61% higher on average | 6-app mixes | Sec. 5.2.2, Fig. 7 |
| NGINX load vs Heracles | 10–30% higher | Memcached + Xapian at equal load | Sec. 5.2.3, Fig. 8 |
| Gap to Oracle | at most 10% lower EMU | Memcached/Xapian/NGINX | Sec. 5.2.3, Fig. 8d |
| Two MongoDB instances | cap at 160% aggregate | I/O contention | Sec. 5.2.1 |
| Recovery after load spike | ~20 s to a valid allocation | Memcached 10%→60% of max, Moses 10%, Xapian 20% | Sec. 5.3, Fig. 9 |
| Heracles reaction to the same spike | pauses other apps for 5 min | same | Sec. 5.3 |
| Controller overhead | 15% of core 0 (10% monitoring, 5% adjustment) | runtime pinned to core 0 | Sec. 5.4 |
| Convergence time | a few seconds up to ~60 s worst case | 6-app mixes worst | Sec. 5.4, Fig. 10 |
| Convergence growth 2→6 apps | 2.8x (average) | — | Sec. 5.4 |

The 3-, 4- and 5-app results appear only as heatmaps and violin plots (Figs. 6, 7) and are not tabulated here.

## Limitations

- **Single-node, single-platform study.** One server type and at most 6 LC apps were evaluated. The abstract's "server platforms" (plural) is broader than what Section 5.1 shows.
- **Client-side latency measurement.** The controller reads tail latency from the workload generators. (Own analysis) In production this needs server-side or proxy-side measurement, which adds noise and delay to the 500 ms loop.
- **No memory-bandwidth knob.** Bandwidth contention is handled only indirectly through CAT. (Own analysis) Later Intel MBA hardware makes this a direct knob that the paper does not use.
- **Migration is described but never evaluated.** No migration experiment or cost is reported. (Own analysis) The 1-minute migration timer is close to the ~60 s worst-case convergence, so slow convergence could trigger migration.
- **Thresholds are tuned but not shown.** The 5%/20% and 500 ms defaults come from a sensitivity study whose results are not shown.
- **Heuristic, not optimal.** At high load PARTIES can ping-pong between starved apps, and slow compute adjustments cause over-allocation (the stated reasons for the gap to Oracle).
- **Inconsistencies inside the paper:**
  - The repetition count is 5 in Sec. 3.2 and 3 in Sec. 5.1.
  - The "61%" headline is framed three ways: in the abstract as throughput under QoS "on average" against existing managers, in the introduction as "up to 61%" aggregate throughput, and in Sec. 5.2.2 as average EMU for 6-app mixes against Heracles only.
  - A 1 GB/s disk-bandwidth step (Secs. 4.2.4, 4.3) seems implausible for a 7200 RPM HDD whose only I/O-heavy tenant, MongoDB, uses 5.1 MB/s in Table 2.

## Relation to other systems

- **Heracles (ISCA 2015).** This is the paper's main baseline. It protects one LC service and treats everything else as BE, pausing BE work on violations, and does not partition memory capacity or disk bandwidth. PARTIES generalizes this to N LC services and partitions among them.
- **Oracle / exhaustive profiling.** This is the paper's upper bound. PARTIES gets within 10% of it with no offline profiling.
- (Own analysis) **Bubble-Up / Bubble-Flux.** These predict or measure interference sensitivity to decide whether to co-locate. PARTIES instead co-locates and then partitions resources online.
- (Own analysis) **Paragon / Quasar.** These are cluster-level, classification-based placement and sizing systems from the same group. PARTIES works below them, as a per-node controller, and could follow such a scheduler's placement.
- (Own analysis) **CLITE (HPCA 2020).** This later work replaced PARTIES's hand-written wheel heuristic with Bayesian optimization over the same kind of partitioning knobs and compared against PARTIES.
- (Own analysis) **Caladan (OSDI 2020).** This later work argued that partitioning at the scale of hundreds of milliseconds is too slow for microsecond-scale bursts, and reallocates cores at microsecond timescales.

## Takeaways for practice

- (Own analysis) A node agent can safely co-locate several latency-SLO services if it has per-tenant knobs (cpuset, CAT ways, DVFS, memcg, blkio, tc/HTB) and a short feedback loop on measured tail latency.
- (Own analysis) Fungibility is the key simplification. Searching one resource at a time with hysteresis (5% vs 20% slack) converges quickly because many allocations are "good enough".
- (Own analysis) Revert asymmetrically: undo a harmful downsize at once and back off further downsizing, but keep an upsize, because a starved service may need several resources.
- (Own analysis) Always take resources back from BE work first. Treat migration as a rare escape hatch with an explicit timeout, and prefer moving stateless or relaxed-SLO tenants.
- (Own analysis) Budget for the controller itself: the paper's runtime used 15% of one core.
- (Own analysis) Watch for unpartitioned shared resources (memory bandwidth, and in GPU nodes, PCIe/NVLink and HBM bandwidth). A controller with no direct knob for a bottleneck can only work around it.

## References

- Paper: https://dl.acm.org/doi/10.1145/3297858.3304005
- PDF (author's Cornell page): https://www.csl.cornell.edu/~delimitrou/papers/2019.asplos.parties.pdf
