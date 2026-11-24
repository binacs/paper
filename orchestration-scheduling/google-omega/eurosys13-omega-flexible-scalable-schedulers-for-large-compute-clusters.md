---
title: 'Omega: flexible, scalable schedulers for large compute clusters'
authors:
- Malte Schwarzkopf
- Andy Konwinski
- Michael Abd-El-Malek
- John Wilkes
affiliations: 'University of Cambridge, UC Berkeley, Google'
venue: 'EuroSys'
year: 2013
paper_id: 1407f94cfed1db0af188ec79b385c7f11ef0aac1
doi: 10.1145/2465351.2465386
abs_url: https://dl.acm.org/doi/abs/10.1145/2465351.2465386
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/3295.pdf
code_url: https://github.com/google/cluster-scheduler-simulator
note_type: deep-read
written_at: '2026-11-25'
---

# Omega: flexible, scalable schedulers for large compute clusters

> **Why it matters:** It defined the monolithic / two-level / shared-state taxonomy and showed on Google traces that parallel schedulers can share one cell through optimistic concurrency at low conflict cost, an idea later used in Borg and Kubernetes.

## Problem

Google's monolithic production scheduler had become hard to change. The paper says this software-engineering burden, more than throughput, drove the redesign (§3.1). Batch jobs are many and short, and they want fast turnaround. Service jobs need failure-aware placement, an NP-hard problem the old scheduler could take "tens of seconds" to solve (§2.1). One queue therefore causes head-of-line blocking. The two-level alternative (Mesos) hides global state and locks resources pessimistically. The paper asks whether a free-for-all over shared state is viable, and what interference costs.

## Core design

### Taxonomy (§3, Table 1)

Axes: work partitioning, resource choice, interference handling, allocation granularity (gang vs incremental), and cluster-wide policy.

- **Monolithic:** one serial scheduler over all resources, with strict priority and preemption. A *multi-path* variant adds a batch fast path but still handles one job at a time.
- **Statically partitioned:** fixed sub-clusters. These fragment the cluster and were dismissed (§3.2).
- **Two-level (Mesos):** a central allocator offers unused resources, in DRF order, to one framework at a time. That is a pessimistic lock for the length of the decision. Frameworks see only their offers, so there is no preemption or global policy, and gang scheduling needs hoarding, which can deadlock (§3.3).
- **YARN:** classified as *effectively monolithic*, because application masters manage jobs but do not schedule (§3.3).
- **Shared-state (Omega):** every scheduler sees the whole cell, with optimistic concurrency control.

### Cell state and transactions (§3.4)

- *Cell state* is the resilient master copy of all allocations. Each scheduler plans against a private, frequently refreshed local copy.
- A placement is an atomic commit to the shared copy, so sync-to-commit is a transaction, and at most one of several conflicting commits succeeds. After each attempt the scheduler resyncs and retries whatever is left.
- **Incremental transactions** (the default) accept every change except the conflicting ones: atomicity without independence. **All-or-nothing transactions** give gang scheduling without hoarding.
- There is no central allocator. Store validation enforces a few common rules: what "machine full" means, and a shared *precedence* scale. Per-scheduler caps limit the resources each may claim and the jobs it may admit. Fairness is left to emergent behaviour and post-facto auditing.
- Conflict detection is **fine-grained** (reject only if the machine would be overcommitted) or **coarse-grained** (reject if the machine's sequence number changed) (§5.2).

### Workload characterisation (§2.1, Figs 2–4)

The paper uses three Google clusters from May 2011: A (medium, busy), B (one of the largest) and C (behind the public trace). Batch means low-priority or best-effort jobs (bands 0–8 in the public trace), and everything else is service. Service jobs run far longer and have fewer tasks.

### Two simulators (§4, Table 2)

- **Lightweight:** samples jobs from the empirical distributions onto homogeneous machines, ignores constraints and places by randomized first-fit. It compares all three architectures and is open source.
- **High-fidelity:** replays real traces through the production scheduler code, with constraints. It models Omega only and is slow.
- Decision time is modelled as `t_decision = t_job + t_task × tasks_per_job`. Metrics are job wait time, scheduler busyness and conflict fraction (conflicts per successful transaction) (§4).

### MapReduce case study (§6)

A specialised scheduler reads the whole cell's utilisation and adds workers to MapReduce jobs from idle resources. A linear-speedup model built from historical map and reduce durations picks the allocation with the earliest predicted finish. Policies: **max-parallelism** (add workers while it helps), **global cap** (stop above a utilisation target) and **relative job size** (at most 4× the requested workers).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Share of jobs that are batch | >80% | Clusters A–C | §2.1, Fig 2 |
| Share of resources allocated to service jobs | 55–80% | Clusters A–C | §2.1, Fig 2 |
| Service jobs running more than a month | 20–40% | Clusters A–C | §2.1 |
| Default decision cost | t_job = 0.1 s, t_task = 5 ms | Conservative estimates from production | §4 |
| Job wait-time SLO | 30 s | Common production SLO | §4 |
| Simulator speed (24 h of simulated time) | ~5 min (lightweight) vs ~2 h (high-fidelity) | Both simulators | Table 2 |
| Scheduling attempts before a job is abandoned | 1,000 | Lightweight sim; triggered mainly by Mesos | §4, Fig 7c |
| Batch arrival-rate headroom before saturation | ~2.5× (A), 6× (B), 9.5× (C) | Omega, one batch and one service scheduler | §4.3, Fig 8 |
| Parallel batch schedulers before conflicts outweigh lower busyness | up to 32 | Lightweight, cluster B | §4.3, Fig 9 |
| Conflict fraction once t_job(service) ≈ 10 s | >1.0 (≥1 retry per service job) | High-fidelity, 7-day cluster B trace | §5.1, Fig 12b |
| Service busyness vs no-conflict baseline | ~40% higher | Same | §5.1, Fig 12c |
| Long per-task decision time tolerated | t_task(service) = 1 s with conflict fraction ≤ 0.2 | t_job(service) = 0.1 s | §5.1 |
| Gain from 3 hashed batch schedulers | ~3×; saturation moves from t_job(batch) ≈ 4 s to 15 s; conflicts ~0.1 | 24 h cluster C trace | §5.1, Fig 13 |
| All-or-nothing (gang) for all jobs | ~2× conflict fraction | Fine-grained detection, cluster C, 29 days | §5.2, Fig 14a |
| Coarse-grained conflict detection | 2–3× conflict rate and busyness | Same | §5.2, Fig 14 |
| MapReduce share of jobs at Google | ~20% | Google-wide | §6 |
| MapReduce jobs that benefit from opportunistic resources | 50–70% | Clusters A, C, D | §6.2, Fig 15 |
| Speedup at the 80th percentile | 3–4× | max-parallelism policy | §6.2 |
| Global-cap utilisation threshold | 60% | Little benefit except on lightly loaded cluster D | §6.2 |

## Limitations

- **All simulation.** There are no production metrics. The high-fidelity simulator leaves out failures and the gap between requested and used resources, and it **disables preemption** (§5).
- **Interference depends on the workload.** In cluster B, service decisions around 10 s miss the SLO purely because of conflicts (§5.1). The lightweight simulator under-reports interference because it ignores constraints (§5).
- **Global guarantees are emergent.** Fairness and starvation avoidance are future work (§8). YARN's authors argue this is a poor fit for open multi-tenant platforms.
- **Scale-out is sub-linear.** It "will not easily handle hundreds of schedulers" (§5.1).
- **The Mesos baseline is narrow.** It is the 0.9.0 simple allocator, which offers *all* free resources to one framework at a time (§3.3, footnotes 2–3). The authors concede fair-share offers could help.
- **The MapReduce speedup model is idealised and linear.** Tail speedups are unreliable and worker start-up cost is not modelled (§6.2).

## Relation to other systems

- **Borg (EuroSys 2015):** scheduler replicas work on a cached copy of cell state, and the Borgmaster rejects assignments based on stale state. Borg calls this "quite similar in spirit" to Omega (Borg §3.4). It contrasts Omega's specialised "verticals" over a shared store with its own one-size-fits-all interface and policy (Borg §7). ACM Queue's "Borg, Omega, and Kubernetes" says many Omega innovations, including multiple schedulers, were folded back into Borg.
- **Mesos (NSDI 2011):** the master decides what to offer and each framework decides what to accept (Mesos abstract). In Omega's simulation, slow service decisions hold the offers and batch jobs are abandoned (§4.2, Fig 7).
- **YARN (SoCC 2013):** a central ResourceManager grants container leases to per-application ApplicationMasters, so Omega calls it monolithic. YARN replies that Omega's design makes capacity, fairness and deadline guarantees harder, which suits closed Google more than open Hadoop.
- **Apollo (OSDI 2014):** distributed schedulers too, but loosely coordinated through shared cluster information and estimates of future availability rather than commits to one store (Apollo abstract).
- **Sparrow (SOSP 2013):** many *stateless* schedulers using batch sampling and late binding for sub-second tasks, within 12% of an ideal scheduler on 110 machines (abstract). It gives up the global view that Omega's §6 scheduler relies on.
- **Kubernetes:** inherits Omega's shared persistent store, with per-object version numbers for optimistic concurrency and reconciling controllers. Unlike Omega, all access goes through a central API server that adds validation and policy (ACM Queue).
- **Gödel (ByteDance, SoCC 2023):** a unified resource pool built on Kubernetes that replaces separate Kubernetes and YARN stacks and co-locates workloads. It reports tens of thousands of machines, >60% utilisation and up to 5,000 pods/s (abstract). The abstract does not say how its schedulers coordinate, so this note does not compare it with Omega's transactions.

## Takeaways for practice

- A versioned shared store with commit-time validation lets independent schedulers (batch, service, gang, elastic) evolve separately and removes head-of-line blocking.
- Default to fine-grained, incremental conflict checks. Per-machine sequence numbers, or gang commits everywhere, multiply retries 2–3× (§5.2).
- Track conflicts per successful commit as decision latency grows, not just throughput (§5.1).
- Scale batch scheduling by hashing jobs across a few replicas, and expect sub-linear gains.
- A view of the whole cell enables policies that offer-based or stateless designs cannot express, such as opportunistic elasticity for best-effort jobs.
- Pair a fast, abstract simulator with a slow one built on production code, and cross-check them (§5).
- Fairness is not free with shared state. Plan for quotas, precedence limits and auditing.

## References

- Paper: https://dl.acm.org/doi/abs/10.1145/2465351.2465386 (PDF: https://storage.googleapis.com/gweb-research2023-media/pubtools/3295.pdf; Google Research page: https://research.google/pubs/omega-flexible-scalable-schedulers-for-large-compute-clusters)
- Code: https://github.com/google/cluster-scheduler-simulator (the lightweight simulator; Omega itself is not open source)
- Related: Borg (EuroSys 2015) https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ ; Borg, Omega, and Kubernetes (ACM Queue 2016) https://research.google/pubs/pub44843/ ; Mesos (NSDI 2011) https://www.usenix.org/conference/nsdi11/mesos-platform-fine-grained-resource-sharing-data-center ; Apollo (OSDI 2014) https://www.usenix.org/conference/osdi14/technical-sessions/presentation/boutin ; Gödel (SoCC 2023) DOI 10.1145/3620678.3624663
