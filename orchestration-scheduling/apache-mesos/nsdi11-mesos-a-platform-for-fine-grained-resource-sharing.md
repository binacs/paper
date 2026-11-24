---
title: 'Mesos: A Platform for Fine-Grained Resource Sharing in the Data Center'
authors:
- Benjamin Hindman
- Andy Konwinski
- Matei Zaharia
- Ali Ghodsi
- Anthony D. Joseph
- Randy Katz
- Scott Shenker
- Ion Stoica
affiliations: 'University of California, Berkeley'
venue: 'NSDI'
year: 2011
paper_id: 3e375c8d996b8c46c83b9d3f72732d7477e5fd86
abs_url: https://www.usenix.org/conference/nsdi11/mesos-platform-fine-grained-resource-sharing-data-center
pdf_url: https://www.usenix.org/event/nsdi11/tech/full_papers/Hindman.pdf
code_url: https://github.com/apache/mesos
note_type: deep-read
written_at: '2026-11-25'
---

# Mesos: A Platform for Fine-Grained Resource Sharing in the Data Center

> **Why it matters:** Mesos introduced two-level scheduling via *resource offers*: a thin, framework-agnostic kernel decides how much each framework gets and the framework decides what to run where. It is the reference point for every later debate on monolithic vs. two-level vs. shared-state cluster schedulers.

## Problem

By 2010 a single organisation ran several cluster frameworks (Hadoop, MPI, Pregel-like systems, and new ones such as Spark) on the same machines. Static partitions or per-framework VMs waste capacity and block data sharing. Fine-grained sharing is attractive because workloads are short: in Facebook's 2,000-node Hadoop warehouse the median job is 84 s and the median task 23 s (§2, Fig. 1). A global scheduler that understood every framework's needs would be complex and would have to anticipate frameworks not yet written. Mesos instead defines a minimal interface and leaves task scheduling to frameworks.

## Core design

**Components (§3.1–3.2, Fig. 2).** A master (with hot standbys) manages slave daemons on every node. Each framework has a *scheduler* that registers with the master and an *executor* process launched on slaves to run its tasks. Long-lived executors are what let Spark cache data in memory across iterations (§5.3).

**Resource offers (§3.2, Fig. 3).** The master's *allocation module* decides which framework should receive a node's free resources and sends that framework an offer, e.g. `<slave1, 4 CPU, 4 GB>`. The framework replies with tasks and their per-task resource vectors (in the example, 2 CPU/1 GB and 1 CPU/2 GB); the master launches them via the executor and the remainder (1 CPU/1 GB) can be offered to another framework. Mesos never sees framework placement preferences; frameworks express them by accepting or declining.

**Allocation module (§3.3).** Pluggable. Two were implemented: fair sharing via a generalisation of max-min fairness to multiple resources (the DRF work, ref. [21]) and strict priorities. Because offered resources count against a framework's allocation, a framework that holds offers it cannot use loses share, which pushes it to respond quickly (§3.5).

**Revocation and guaranteed allocations (§3.3).** If long tasks fill the cluster, the allocator may revoke (kill) tasks, after a grace period. Each framework has a *guaranteed allocation*: below it, none of its tasks are killed; above it, any may be. Allocators must make all guarantees simultaneously satisfiable; frameworks query theirs with `getGuaranteedShare()`. The Torque port stays within its guarantee so non-fault-tolerant MPI jobs are never revoked (§5.2).

**Filters and offer hygiene (§3.5).** Frameworks install Boolean *filters* to skip offers they would reject: "only offer nodes from list L" and "only offer nodes with at least R resources free". Unanswered offers are *rescinded* after a timeout and re-offered.

**Isolation (§3.4, §5).** Mesos relies on OS containers (Linux Containers, Solaris Projects) to limit CPU, memory, network and, on newer kernels, I/O of an executor's process tree. The implementation at publication isolated only CPU cores and memory.

**Fault tolerance (§3.6).** The master keeps only soft state, rebuildable from slaves and schedulers when they reconnect. Several masters run hot-standby with ZooKeeper leader election. Node failures and executor crashes are reported to the framework schedulers, which decide how to react. A framework can register multiple schedulers; on failure the master notifies another to take over (sharing scheduler state is the framework's job).

**API (Table 1).** Scheduler: `resourceOffer`, `offerRescinded`, `statusUpdate`, `slaveLost` callbacks; `replyToOffer`, `setNeedsOffers`, `setFilters`, `getGuaranteedShare`, `killTask` actions. Executor: `launchTask`, `killTask`, `sendStatus`.

**Analytical model (§4).** Frameworks are *elastic* (Hadoop) or *rigid* (MPI: needs a fixed allocation before starting); task durations are constant or exponential with mean T. With homogeneous tasks, ramp-up is T (constant) or T ln k (exponential, k slots), and an elastic job of duration βT completes in (1/2+β)T or (1+β)T with utilisation 1, while rigid frameworks waste resources while waiting, e.g. utilisation β/(1/2+β) for constant durations (Table 2). With preferences for a subset of nodes, lottery scheduling in proportion to intended share s_i approximates weighted fair allocation of preferred slots without knowing preferences (§4.3). With mixed long/short tasks, the chance a node is filled only with long tasks is φ^S (0.4% for S=8 slots, φ=0.5); (§4.4). Limits (§4.6): fragmentation (bounded by largest task/node size; fix with a minimum offer size), interdependent cross-framework constraints that need a global view, and pushing scheduling complexity into frameworks.

**Ports (§5).** Mesos ~10,000 lines of C++; Hadoop port ~1,500 lines (TaskTrackers as executors, delay scheduling, per-node file server for map output); Torque 360 lines of Python plus 3 changed lines; MPI wrapper 200; Spark ~1,300.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Facebook median job / task | 84 s / 23 s | 2,000-node Hadoop warehouse | §2, Fig. 1 |
| Macrobenchmark cluster | 96 nodes vs. four 24-node static partitions | EC2, 4 cores / 15 GB per node | §6.1 |
| Utilisation gain | +10% CPU, +17% memory | Mesos vs. static partitioning | §6.1.2, Fig. 7 |
| Large Hadoop mix | 3,143 s → 1,494 s (2.10×) | 10 text-search jobs | Table 4 |
| Facebook Hadoop mix | 7,235 s → 6,319 s (1.14×) | 100 jobs over 25 min | Table 4 |
| Spark ALS | 1,684 s → 1,338 s (1.26×) | 5 jobs | Table 4 |
| Torque/MPI | 3,210 s → 3,352 s (0.96×) | 8 tachyon jobs, 24 tasks each | Table 4 |
| Mesos overhead | LINPACK 50.9→51.8 s; WordCount 160→166 s (<4%) | 50 EC2 nodes | §6.2 |
| Data locality | 18% static; >90% with 1 s delay; 95% with 5 s | 16 Hadoop instances, 93 nodes, 100 GB | §6.3, Fig. 8 |
| Job speedup from locality | 1.7× (5 s delay vs. static) | same | §6.3 |
| Spark vs. Hadoop | 127 s/iter Hadoop; Spark 174 s first, ~6 s later; up to 10× | logistic regression, 29 GB, 20 nodes | §6.4, Fig. 9 |
| Scalability | <1 s added task-launch overhead at 50,000 emulated slaves, 200 frameworks | 99 EC2 nodes | §6.5, Fig. 10 |
| Master failover MTTR | 4–8 s | 200–4,000 slaves, 5-node ZooKeeper, 62 nodes | §6.6 |
| Container isolation | Apache latency +30% with LXC vs. +550% without | CPU hog colocated | §6.7 |

Ramp-up: fine-grained frameworks exceed their 1/4 static share (large Hadoop reaches 7/8 of the cluster) and resources move within tens of seconds when a new job arrives (§6.1.2, Figs. 5–6).

## Limitations

- Works best for short, elastic, homogeneous tasks. Rigid frameworks lose: Torque/MPI was 4% slower, with ~12 s per job spent waiting to gather 24 tasks (§6.1.2), and small Facebook jobs slowed (0.84×) because Hadoop's internal fair sharing interacts with Mesos's framework-level sharing (Table 5).
- Frameworks see only what they are offered; interdependent or cross-framework constraints need a global allocator (§4.6).
- Fragmentation and starvation of large-task frameworks require a minimum offer size (§4.6).
- Isolation covered only CPU and memory; network/I/O were future work (§5).
- Scale results use emulated slave daemons, not real nodes; production lessons (Twitter test deployment, 40-node lab cluster) were deferred (§8).

## Relation to other systems

- **Omega (EuroSys 2013).** Omega's paper argues that two-level offers give each framework only a view of currently free resources, which rules out preemption and policies needing whole-cluster state, and that offering a resource to one framework at a time is *pessimistic* concurrency control. Gang-scheduled "picky" jobs must hoard offers, which wastes capacity and can deadlock (§1, §3.3). In its simulations, slow service-scheduler decisions hold offered resources, raise batch scheduler busyness and cause many jobs to be abandoned at the retry limit; Omega attributes this to Mesos assuming fast decisions, small jobs and high churn (§4.2, Fig. 7). Omega gives every scheduler the full shared cell state and resolves conflicts with optimistic, lock-free transactions.
- **YARN (SoCC 2013).** YARN calls itself request-based where Mesos is offer-based: a per-job ApplicationMaster sends ResourceRequests with counts, sizes, locality and priority, and pulls container leases on heartbeats (§3.2, §6). It argues this suits locality-aware allocation and rolling upgrades, conceding a per-job AM may cost more than Mesos's long-running framework schedulers (§6).
- **Borg (EuroSys 2015).** Borg describes the Mesos master as "somewhat like Borgmaster minus its scheduler"; Borg keeps a centralised, request-based scheduler (feasibility checking plus scoring, preempting lower priorities) over a Paxos-replicated Borgmaster, and uses priorities and quotas rather than DRF (§3, §7).
- **DRF (NSDI 2011).** Companion paper from the same group: DRF generalises max-min fairness to multiple resources (strategy-proof, envy-free, Pareto efficient) and was implemented in Mesos; it is the fair-sharing allocation module behind Mesos offers.
- **Kubernetes.** Per *Borg, Omega, and Kubernetes* (ACM Queue 2016), Kubernetes keeps Omega's shared persistent store with optimistic concurrency (object versions), fronted by an API server, with controllers reconciling desired and observed state: shared state, not offers. The article does not discuss Mesos.

## Takeaways for practice

- Separate *how much* (fair share/priority/quota) from *where and what* (framework placement logic); this split remains useful even inside a monolithic scheduler.
- Offers work when tasks are short and elastic; for gang-scheduled or long-running work (MPI, large GPU training jobs), plan for reservations, guaranteed shares or a scheduler with global visibility instead of hoarding offers.
- Count held-but-unused resources against a tenant's share, and time out pending offers or reservations; otherwise slow schedulers lock capacity (exactly Omega's simulation finding).
- Keep the control plane soft-state and rebuildable from agents (4–8 s failover).
- Delay scheduling is a cheap locality win (18% → 95%) for short tasks.
- Use multi-resource fairness (DRF) once tasks have heterogeneous CPU/memory/GPU demands.

## References

- Paper: https://www.usenix.org/conference/nsdi11/mesos-platform-fine-grained-resource-sharing-data-center (PDF: https://www.usenix.org/event/nsdi11/tech/full_papers/Hindman.pdf)
- Code: https://github.com/apache/mesos (Apache Mesos; the paper itself gives no code URL)
- Omega: https://research.google/pubs/omega-flexible-scalable-schedulers-for-large-compute-clusters
- YARN: Vavilapalli et al., SoCC 2013
- Borg: https://research.google/pubs/pub43438
- DRF: https://usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types
- Borg, Omega, and Kubernetes: https://research.google/pubs/pub44843/
