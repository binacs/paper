---
title: 'Apollo: Scalable and Coordinated Scheduling for Cloud-Scale Computing'
authors:
- Eric Boutin
- Jaliya Ekanayake
- Wei Lin
- Bing Shi
- Jingren Zhou
- Zhengping Qian
- Ming Wu
- Lidong Zhou
affiliations: 'Microsoft, Microsoft Research'
venue: 'OSDI'
year: 2014
abs_url: https://www.usenix.org/conference/osdi14/technical-sessions/presentation/boutin
pdf_url: https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-boutin_0.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Apollo: Scalable and Coordinated Scheduling for Cloud-Scale Computing

> **Why it matters:** Apollo showed in production that one scheduler per job, sharing a loosely synchronised view of per-server queue state, can place more than 10,000 tasks/s on clusters of more than 20,000 machines while minimising estimated completion time rather than chasing locality.

## Problem

Cosmos runs SCOPE jobs. SCOPE is SQL-like with user code; its optimizer compiles each job into a DAG of stages, each made of parallel tasks (§2). The workload is extreme (§2.3, Fig. 2):

- more than 100k jobs per day;
- stage parallelism from single digits to tens of thousands;
- inputs from GBs to tens of PBs;
- task runtimes from under 100 ms to hours, half under 10 s;
- peaks above 100k scheduling requests/s.

Locality also depends on cached executables and lookup tables, not only on input data. A first centralised attempt became a bottleneck as scale grew. The old scheduler had no global load view, relaxed locality over time, and spawned duplicates for queued tasks (§4). The goal is scale, high utilisation, and low latency while keeping per-group capacity guarantees.

## Core design

**Architecture (§3.1, Fig. 3).** Each job has a Job Manager (JM): a full scheduler for its own DAG, handling priorities, placement, failures, and dependencies. Each server runs a Process Node (PN) with a local task queue. A Paxos-replicated Resource Monitor (RM) aggregates PN load and gives every JM a global view. The RM is off the critical path: if it is down, JMs keep scheduling on staler data. After dispatch, a JM gets status directly from the PN.

**Tokens (§2.1).** A token is the right to run one regular task of bounded CPU and memory. Each user group has a virtual cluster with a token quota and a job queue.

**Wait-time matrix (§3.2).** Each PN publishes expected queueing delay indexed by (CPU cores × memory); Fig. 3 gives 10 s for a 4-core, 12 GB request. The PN computes it by simulating its queue and sends it, timestamped, to the RM and to JMs with tasks there. Wait time normalises heterogeneous hardware. PNs fetch a task's files while it is queued, hiding initialisation. The queue is mostly FIFO; a small task may fill a gap if no one is delayed.

**Estimation-based placement (§3.3, Fig. 4).**
- `E_succ = I + W + R`: initialisation (zero if cached), matrix wait, and runtime (I/O + CPU).
- `C = P_succ·E_succ + K_fail·(1−P_succ)·E_succ`: P_succ comes from failure history and maintenance; K_fail is tuned empirically and not given.
- In Fig. 4 the server holding the largest input has a 40 s queue and ranks worst. A rack-local server with a 5 s wait beats two idle servers.
- Runtime estimates start from optimizer statistics and are refined by measurements from finished tasks in the same stage.
- Stage priority comes from the critical path; within a stage, larger inputs go first.
- Candidate servers: those holding large inputs, their rack-mates, and two random lightly loaded servers kept in the background.
- Batches of similar-priority tasks use a capped stable-matching variant (Fig. 5): tasks propose to their best server, contested servers keep the task saving the most time, and at most one task per server per batch.

**Correction mechanisms (§3.4).** Unlike Omega, which resolves conflicts at commit time, Apollo resolves them after dispatch, since local queues absorb many conflicts.
- *Duplicate scheduling*: on a fresh matrix, re-check queued tasks. Duplicate if the new expected wait is much higher, the expected wait exceeds the stage average, or the elapsed wait does. The first copy to start wins.
- *Randomisation*: a small jitter, scaled to the JM–PN update interval, spreads JMs across near-equal servers.
- *Confidence*: older matrices are trusted less, and the JM reads a pessimistic (larger-request) cell.
- *Stragglers*: compare progress against same-stage peers and duplicate when a rerun would finish much sooner. Slow input I/O can trigger re-running the upstream task.

**Opportunistic scheduling (§3.5).** Regular tasks hold tokens and have priority. Opportunistic tasks use no tokens, run at low priority, and can be preempted or killed. A job uses opportunistic tasks only after exhausting its tokens, up to c·n for n tokens (c not given). Idle PNs pick opportunistic tasks randomly, not FIFO, so late jobs get a share; jobs may weight tasks within their allowance. When a token frees up, a running opportunistic task is upgraded in place, preferring servers with few regular tasks. Every job holds at least one token, so none starves.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Scheduling rate | above 10,000/s, up to about 20,000/s in one cluster | production, hourly peaks | §5.1, Fig. 6 |
| Cluster size | over 20,000 servers | production since late 2013 | §1, §5 |
| Concurrency | 750 jobs, 140,000 regular tasks | two weeks | §5.1, Fig. 7(a) |
| CPU utilisation | above 90% at weekday peaks; 3% gap between 20th and 80th percentile | production | §5.1, Fig. 7(b) |
| Regular share of workload | about 70% on weekdays | production | §5.1, Fig. 7(c) |
| Regular-task queueing delay | under 1 s at p95 | whole cluster | §5.1 |
| Tasks / I/O by locality | server 28% / 46%; rack 56% / 47%; cross-rack 16% / 7% | production | Table 1 |
| Recurring jobs vs baseline | about 80% faster, up to 3x | about 40% of jobs, over 75% of resources | §5.2, Fig. 8(b) |
| Hourly critical job | about 22% lower latency; within 4.5% of capacity-bound oracle | about 10k tasks | §5.2, Fig. 9 |
| Wait estimate accuracy | error under 1 s for over 95% of tasks | production | §5.3 |
| CPU-time estimate accuracy | within 25% for 75% of tasks | production | §5.3, Fig. 10 |
| Duplicate triggers (i)/(ii)/(iii) | 0.12% / 0.12% / 0.17%; success 81.3% / 81.3% / 83.0% | production | Table 2 |
| Duplicates overall | under 0.5% of creations, about 82% successful | production | §5.4 |
| Stragglers detected | over 70% | production | §5.4 |
| Duplicates vs old scheduler | 98% fewer, no loss of performance | Apollo in isolation | §4 |
| Stable vs greedy matching | stable within 5% of optimal; greedy 57% slower | simulation, 100 servers | §5.5, Fig. 12 |

The baseline is Microsoft's previous in-house scheduler, not an external system.

## Limitations

- Quality depends on estimates. CPU-time error exceeds 25% for a quarter of tasks, and early-exit or input-dependent user code is hard to predict (§5.3).
- Key parameters are not published: K_fail, c, and the thresholds for duplicates and jitter.
- Opportunistic priority was enforced by the OS but not by the distributed file system, so I/O contention slowed regular tasks (§4).
- The failure model overreacted after a power-transformer outage and slowed recovery (§4).
- The design is tied to SCOPE and token-based tenancy. It offers no multi-framework interface and does not address long-running services.
- There is no head-to-head comparison with Omega, Sparrow, or YARN.

## Relation to other systems

- **Omega (EuroSys 2013):** Omega's schedulers also share state, but use lock-free optimistic concurrency control and retry on conflict at commit. Apollo lets conflicts through and fixes them afterwards with duplicates. Apollo notes that Omega's evaluation was simulation-based.
- **Sparrow (SOSP 2013):** Sparrow is stateless and uses batch sampling (d·m probes) and late binding for sub-second tasks. On 110 machines it came within 12% of ideal. Apollo uses a global RM view, includes locality in its cost model, and binds early so that file downloads overlap queueing; it argues late binding would add too much initialisation cost.
- **YARN (SoCC 2013):** YARN has a central ResourceManager that grants container leases against locality-aware ResourceRequests from per-application ApplicationMasters. Apollo's JM resembles an ApplicationMaster that places tasks itself; the RM only publishes load.
- **Borg (EuroSys 2015):** Borg is a general cluster manager (admission control, packing, over-commitment, isolation) for hundreds of thousands of jobs. Apollo is a narrower batch placer that gets utilisation from opportunistic tasks rather than over-commitment.
- **Mercury (ATC 2015, Microsoft):** Mercury is a hybrid of central and distributed scheduling on YARN. Applications trade scheduling overhead for guarantees, spare capacity is used opportunistically, and task throughput improves by more than 35%. In my reading, it generalises Apollo's guaranteed/opportunistic split; Mercury's abstract does not cite Apollo.
- **Hydra (NSDI 2019, Microsoft):** Hydra is a federated manager on YARN in which loosely coordinated sub-clusters place tasks and a central layer enforces tenant shares. It reports almost a trillion tasks scheduled. Its abstract does not name Apollo, so no succession is claimed here.

## Takeaways for practice

- Advertise expected wait per resource shape, not free capacity. This is compact, makes heterogeneous servers comparable, and looks ahead.
- Score placements by completion time (initialisation + wait + runtime, weighted by failure risk); a short rack-local queue often beats data locality.
- Keep global-state services off the critical path.
- Optimistic placement plus cheap after-the-fact correction works when servers have queues. Add jitter and staleness-aware confidence to prevent herding.
- Separate guaranteed from opportunistic work, upgrade tasks in place, and enforce priority in every shared layer, storage I/O included.
- Validate in production with staged, side-by-side rollouts, because small test clusters misled the team (§4).

## References

- Paper: https://www.usenix.org/conference/osdi14/technical-sessions/presentation/boutin (PDF: https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-boutin_0.pdf)
- Omega: https://research.google/pubs/omega-flexible-scalable-schedulers-for-large-compute-clusters
- Sparrow: https://amplab.cs.berkeley.edu/wp-content/uploads/2013/11/p69-ousterhout.pdf
- YARN: https://opencourse.inf.ed.ac.uk/sites/default/files/2023-10/yarn-socc13.pdf
- Borg: https://research.google/pubs/pub43438/
- Mercury: https://www.usenix.org/conference/atc15/technical-session/presentation/karanasos
- Hydra: https://www.usenix.org/conference/nsdi19/presentation/curino
