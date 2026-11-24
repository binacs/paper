---
title: 'Reconciling High Server Utilization and Sub-millisecond Quality-of-Service'
authors:
- Jacob Leverich
- Christos Kozyrakis
affiliations: 'Stanford University'
venue: 'EuroSys'
year: 2014
doi: 10.1145/2592798.2592821
abs_url: https://dl.acm.org/doi/10.1145/2592798.2592821
pdf_url: https://mast.stanford.edu/pubs/reconciling_high_server_utilization_and_sub_millisecond_quality_of_service/paper.pdf
code_url: https://github.com/leverich/mutilate
note_type: deep-read
written_at: '2026-11-25'
---

# Reconciling High Server Utilization and Sub-millisecond Quality-of-Service

> **Why it matters:** It shows, with a request-level breakdown of memcached on stock Linux, that co-locating a sub-millisecond service with batch work fails for three specific, fixable reasons (queuing delay, thread load imbalance, scheduler wakeup delay), and that fixing them makes co-location pay off in TCO terms.

## Problem

Operators keep latency-critical (LC) services on dedicated or heavily over-reserved servers because co-location threatens tail latency, which leaves clusters badly underutilized (the paper cites industry utilization in the single digits to low tens of percent, and a Google trace where reservations far exceed use). The question is whether a service whose QoS target is a 95th-percentile latency of a few hundred microseconds can share a server with other work, and if not, exactly what breaks. Prior co-location work mostly detected and avoided interfering pairs; this paper instead dissects *how* interference turns into tail latency in a low-latency, event-driven, kernel-heavy service.

## Core design

The paper is an analysis-plus-mitigation study, not a new system. Memcached 1.4.15 is the case study (Sec. 3.2), chosen for its tiny nominal latency, common epoll/libevent architecture and small code base; most of its time is in the kernel (Sec. 3.2.2).

### Methodology (Sec. 3.1, 3.2.1)
- QoS metric: 95th-percentile latency. Load is expressed as a fraction of peak QPS.
- Load from **mutilate**, the authors' load generator, replaying Facebook-like (ETC) distributions with exponential inter-arrivals, fixed 200 B values, 30 B keys drawn from 1M keys, no pipelining, connections spread over 20 client machines.
- Server: 2x 6-core Xeon L5640, 48 GB, 10GbE, Linux 3.5.0, C6 and DVFS off, irqbalance off, IRQ affinity set manually.
- Table 1 decomposes one request across the pipeline (RX, TCP/IP, epoll, libevent, read, memcached, write) under four conditions: unloaded, context switching, loaded, and loaded plus L3 interference.

### Three QoS vulnerabilities (Sec. 3.2.3–3.3)
1. **Queuing delay.** At low load, interference (e.g., heavy L3 thrashing) barely shows; at high load it lowers the service rate and queuing dominates (Fig. 2, Table 1: under load almost all time sits in epoll/libevent waiting, not in processing). Interference effectively moves the knee of the latency-vs-load curve left.
2. **Load imbalance.** Memcached assigns connections to threads statically. With more threads than cores, or even one thread per core when Linux's affine-wakeup migration stacks two threads on a core, tail latency spikes around 50% of peak load (Fig. 3).
3. **Scheduling delay.** Under CFS, a waking task's vruntime is clamped to `max(vruntime(T), min_vruntime − L)`, with L half the 24 ms target latency, i.e. 12 ms (Sec. 3.3, Fig. 7). A bursty antagonist (6 ms busy / 42 ms sleep) that wakes up can preempt memcached and make it wait up to L, far beyond its deadline. Memcached's tail spikes at low load even though total CPU use is low (Fig. 5). Two LC services (memcached and a synthetic 1 ms service) on one core under CFS cannot both meet a "95th < 5x low-load 95th" target except in a narrow range (Fig. 6).

Context switching itself and cache/TLB pollution from timesharing with SPEC were *not* major factors (Sec. 3.2.5, Fig. 4), and network-heavy co-runners interfered less than expected because memcached saturates CPU before the 10GbE link (Sec. 3.4).

### Mitigations (Sec. 4)
- **Interference-aware provisioning (Sec. 4.1).** Accept lower per-server throughput under interference: provision each server only for the load it can sustain at QoS *with* the co-runner, add servers to make up the difference, and use the freed capacity for batch work.
- **Fixing imbalance (Sec. 4.2).** A ~20-line memcached patch reads the allowed CPU set at startup and pins threads round-robin with `sched_setaffinity()` (Fig. 8). Guidelines: at most N threads on N cores, pin to distinct cores, if sharing cores share all of them, and use UDP where imbalance is unavoidable.
- **Fixing scheduling delay (Sec. 4.3).** Four options compared (Fig. 9):
  - CFS with very high shares/nice for the LC task: protects it, but the single knob couples preemption and throughput share, so a load spike or bug in the LC task starves the co-runner. Acceptable only for best-effort co-runners.
  - POSIX `SCHED_FIFO/RR` with rate-monotonic priorities: works up to moderate aggregate load but a misbehaving high-priority task can starve the rest.
  - CFS bandwidth limits (quota/period, period 24 ms, quotas proportional to offered QPS): enforces fairness but is not work-conserving, so it degrades at higher aggregate load.
  - **BVT (Borrowed Virtual Time).** A ~150-line CFS patch adds a per-task or per-cgroup *warp*, a static offset subtracted from vruntime only for preemption decisions (effective virtual runtime, Fig. 10). Warp decouples short-term wakeup priority from long-term fair share; warp 0 is plain CFS. An HRTICK-based grace period re-checks preemption when a waking task barely misses preempting. BVT keeps both LC services within QoS up to high aggregate load and removes the low-load spike of Fig. 5.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| memcached peak throughput | ~1.1M QPS non-pipelined; >3.0M QPS pipelined | 2x L5640, 10GbE | Sec. 3.2.1 |
| Kernel vs user time | 83% kernel, 17% user | memcached runtime | Sec. 3.2.2 |
| Request latency, unloaded | 21.5 µs server total; 49.8 µs client end-to-end | Table 1 | Table 1 |
| Request latency, loaded | 5,872 µs server; 6,011 µs end-to-end | high load | Table 1 |
| Request latency, loaded + L3 interference | 8,349 µs server; 8,460 µs end-to-end | high load | Table 1 |
| CFS wakeup offset L | 12 ms (half of 24 ms target latency) | Linux 3.5 CFS | Sec. 3.3 |
| Bursty antagonist | 6 ms on / 42 ms off (~12.5% of a CPU) | square wave | Sec. 3.2.5, Fig. 5 |
| memcached tail spike under CFS | from ~12% of peak QPS | with square-wave antagonist | Sec. 3.2.5, Fig. 5 |
| After thread pinning | up to near 90% of peak (>900,000 QPS) at 95th < 1 ms | 20-line patch | Sec. 4.2, Fig. 8 |
| SCHED_FIFO + bandwidth limits | at least one service degrades above ~70% aggregate load | memcached + 1 ms service | Sec. 4.3.3, Fig. 9 |
| BVT | both services meet QoS up to 80–90% aggregate load | memcached + 1 ms service | Sec. 4.3.4, Fig. 9 |
| BVT patch size | ~150 lines changed in CFS | Linux | Sec. 4.3.4 |
| memcached 95th, no co-runner | 122 / 387 µs | 10% / 90% load, timeshared | Table 2 |
| memcached 95th with 470.lbm | 325 / 642 µs | 10% / 90% load, timeshared | Table 2 |
| Perf/TCO-$ improvement (geomean) | 52% / 29% / 18% / 11% / 18% | memcached load 10/30/50/70/90%, Facebook scenario | Table 2, Sec. 5.1 |
| Max provisionable memcached load | 60% of peak | 500 µs 95th, ≤10% SPEC slowdown, distinct cores | Sec. 5.2, Table 3 |
| Extra memcached capacity | up to 3,600 servers' worth | 12,000-server Google-like cluster | Sec. 5.2 |
| TCO improvement, Google scenario | 17% | memcached assumed always at 100% power | Sec. 5.2 |
| TCO model inputs | $2,000 server, 3-year life, $0.08/kWh, PUE 1.25, 300 W peak, 50% static | Patel and Shah cost model | Sec. 5.1, Table 2 |

## Limitations

- **One LC workload, one platform.** Everything is memcached on a 2010-era dual-socket Xeon with Linux 3.5. Services with longer, CPU-bound request handling or deep fan-out are not studied.
- **Antagonists are mostly SPEC CPU2006 and microbenchmarks.** Memory-bandwidth and network-heavy batch jobs are touched only lightly (Sec. 3.4); Table 3 shows memory-intensive co-runners (429.mcf, 459.GemsFDTD, 470.lbm, an L3 microbenchmark) blowing the tail into milliseconds at 80–90% load even on distinct cores, and the paper offers no mechanism for shared LLC or memory bandwidth beyond provisioning lower load.
- **Static provisioning.** The load cap (e.g., 60% of peak) is chosen offline per co-runner mix; there is no online controller reacting to diurnal load or to a new batch job's interference.
- **BVT needs a kernel patch and per-task warp values**, which the paper does not give numerically; it suggests rate-monotonic assignment.
- **TCO results are model-based**, not measured at cluster scale. The headline "up to 52%" is the Facebook-scenario geomean at only 10% memcached load (Table 2); the Google scenario yields 17% (Sec. 5.2).
- **Inconsistencies noticed in the paper.** In Table 3 several saturated rows are non-monotone (e.g., 470.lbm 95th latency is lower at 90% load than at 80%; GemsFDTD and the L3 microbenchmark also wobble), which suggests saturation-regime measurement noise rather than a real trend. In Table 2 the Perf/TCO-$ geomean is higher at 90% load than at 70%. The printed formula for the "34% discount" in Sec. 5.1 does not extract cleanly from the PDF, so it is left out here.

## Relation to other systems

- **Bubble-Up / Bubble-Flux (Mars, Tang et al.)** measure interference sensitivity and avoid or throttle bad co-location pairs. This paper instead explains the mechanism of the latency hit and folds interference into the load provisioned per server (Sec. 6).
- **Paragon (Delimitrou and Kozyrakis)** classifies workloads to pick interference-compatible placements cluster-wide; this paper works one level below, on the server's scheduler and thread layout (Sec. 6).
- **Chronos, RAMCloud** cut tail latency by bypassing the kernel with user-level networking; the paper argues this complicates consolidation and wastes cores during diurnal troughs (Sec. 6).
- **Tessellation, Akaros** get QoS via new OS abstractions; BVT is a small patch to an existing scheduler (Sec. 6).
- **Pisces** gives multi-tenant QoS inside one key-value store, not co-location of different workloads (Sec. 6).
- **Heracles (Lo et al., ISCA 2015, same group)** is the natural successor: an online feedback controller that partitions cores, LLC ways, memory bandwidth and network for LC plus best-effort co-location, addressing exactly the shared-resource gap Table 3 exposes. Later dataplane-style systems such as Shenango and Caladan move the core-allocation decision to microsecond timescales instead of tuning CFS (Own analysis).

## Takeaways for practice

- Treat "LC service + batch on one box" as a **provisioning problem first**: measure the latency-vs-load knee *with* the intended co-runner and cap per-server LC load below it; spend the saved hardware on extra LC replicas.
- **Pin LC threads and never run more threads than allotted cores.** Kernel wakeup migration can silently stack threads and create load-imbalance tails at moderate load; the same holds for inference servers' worker or polling threads.
- **Wakeup placement, not context-switch cost, is the CFS tail hazard.** A bursty co-runner can cost an LC task milliseconds of wait. Decouple preemption priority from throughput share (BVT-style warp, a low-priority class for batch, or dedicated cores) (Own analysis).
- Prefer **work-conserving** isolation for LC pairs; hard CPU quotas protect fairness but waste idle cycles and hurt at high aggregate load.
- Memory-intensive batch jobs need **hardware partitioning or exclusion** (LLC/memory-bandwidth controls), not just CPU scheduling; a scheduler should label jobs by memory intensity before co-placing them with LC services (Own analysis).
- Report co-location wins as **performance per TCO dollar** under explicit power and capex assumptions, and state the LC load at which the number holds.

## References

- Paper: https://dl.acm.org/doi/10.1145/2592798.2592821 (PDF: https://mast.stanford.edu/pubs/reconciling_high_server_utilization_and_sub_millisecond_quality_of_service/paper.pdf; group page: https://mast.stanford.edu/pubs/reconciling_high_server_utilization_and_sub_millisecond_quality_of_service/)
- Code: https://github.com/leverich/mutilate (mutilate load generator, cited in the paper's footnote 1); the paper also links a BVT kernel patch in footnote 3 (not opened, so not listed)
