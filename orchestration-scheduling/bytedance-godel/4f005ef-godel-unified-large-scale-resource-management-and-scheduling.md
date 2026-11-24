---
title: 'Gödel: Unified Large-Scale Resource Management and Scheduling at ByteDance'
authors:
- Wu Xiang
- Yakun Li
- Yuquan Ren
- Fan Jiang
- Chaohui Xin
- Varun Gupta
- Chao Xiang
- Xinyi Song
affiliations: 'ByteDance'
venue: 'SoCC'
year: 2023
paper_id: 4f005efd52334f68cace00980c69fba6326e79f8
doi: 10.1145/3620678.3624663
abs_url: https://dl.acm.org/doi/10.1145/3620678.3624663
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3620678.3624663
code_url: https://github.com/kubewharf/godel-scheduler
note_type: deep-read
written_at: '2026-11-25'
---

# Gödel: Unified Large-Scale Resource Management and Scheduling at ByteDance

> **Why it matters:** It shows how to put online microservices, batch and ML training into one Kubernetes-compatible resource pool of tens of thousands of nodes. It does this by splitting the scheduler into a dispatcher, partitioned optimistic schedulers and a single conflict-checking binder, with gang semantics built in.

*Provenance:* the ACM full text could not be fetched for this note. The design and numbers below come from the paper's abstract, ByteDance's own Chinese write-up of the paper (Volcano Engine developer blog, "SoCC 论文解读"), the CNCF open-sourcing post, the KubeCon NA 2024 talk slides, and the repo docs. Section references point to those sources, not to paper sections. On 2026-11-25 every number was re-checked against the write-up, the CNCF post, the KubeCon slides and the repo (two matching fetches each). The ACM abstract page could not be re-read then, so figures are now cited to the sources that could.

## Problem

ByteDance ran separate, per-business-group clusters on Kubernetes (online) and YARN (offline). Moving capacity from offline to online before traffic peaks was done by hand: slow, planned in advance, and expensive to operate. The split also capped utilization (abstract; Volcano Engine write-up, "Motivation"). No existing scheduler covered both worlds:

- kube-scheduler: flexible semantics for microservices, but per-pod only, weak for offline work, and limited in throughput and cluster size.
- YARN: high throughput and gang-style semantics at scale, but a poor fit for long-running microservices.
- Volcano: gang and queue semantics on Kubernetes, but low throughput and no online support.

The target: one Kubernetes-compatible pool with high utilization and elasticity, over 1,000 pods/s, and topology-aware placement (Volcano Engine write-up, "Motivation").

## Core design

### Unified pool on Kubernetes
Gödel is built on Kubernetes, with the scheduler and some components replaced or extended (abstract). Node-side resource state, including micro-topology such as per-socket CPU and memory, comes from a separate CRD, CNR (Custom Node Resource), which ByteDance's node agent Katalyst keeps up to date. This lets the scheduler place topology-sensitive pods correctly instead of failing kubelet admission (Volcano Engine write-up). Load-aware filtering and NUMA-level placement also depend on Katalyst (KubeCon slides). Online and offline capacity is shared, and resource reservation lets offline work borrow idle online capacity off-peak while online services keep fast scale-up.

### Dispatcher / Scheduler / Binder split
- **Dispatcher (single instance):** the entry point. It holds a sort policy manager (FIFO in production; DRF/FairShare implemented but not used in production per CNCF post; priority queuing planned) and a pluggable dispatching policy (default: load balancing across scheduler instances). Its Node Shuffler partitions nodes so that each node belongs to exactly one partition and each scheduler instance owns one. A Scheduler Maintainer tracks instance health, load and partition size, and a Reconciler periodically checks Pods, Nodes, Schedulers and SchedulingUnits for inconsistencies.
- **Scheduler (N instances):** computes placement and preemption decisions but does not execute them. It runs three phases: node organizing (locating plugins narrow nodes, grouping plugins group them by resources or job-level affinity), unit scheduling (filter and score plugins, as in the kube-scheduler framework), and unit preempting (victim search, plus node and victim sorting). Each instance searches its own partition first and falls back to other partitions.
- **Binder (single instance):** the commit point. Its ConflictResolver checks optimistically in cross-node and single-node modes. On conflict the unit is rejected and goes back for rescheduling; it is never partially committed. If several schedulers want to preempt the same victim, only the first request is honoured. The PreemptionOperator deletes victims. The UnitBinder does pre-bind work (e.g. dynamic volume creation) and then binds.

ByteDance's write-up notes that partition-local decisions are only locally optimal and that conflicts grow with instance count, so instance count is a tuning knob.

### Unit (gang) semantics
Gödel uses two levels. A **Scheduling Unit** is a deployment or job (a PodGroup or a ReplicaSet). A **Running Unit** is a pod. A unit is admitted only if at least `Min_Member` pods find feasible nodes; otherwise the whole unit is rejected. `Min_Member = 1` gives kube-scheduler-like behaviour for microservices. `Min_Member = N` gives all-or-nothing gangs for batch and training, and intermediate values are set from the workload type or template (Volcano Engine write-up, "Two-level scheduling"). In the open-source API this is a `PodGroup` CRD with `spec.minMember` and `spec.scheduleTimeoutSeconds`, and pods join it via a label and annotation (repo `docs/features/gang-scheduling.md`). Job-level affinity adds hard and soft constraints that keep a whole job inside one topology domain.

### Throughput techniques
- **Candidate-node caching:** pods of one unit usually have identical requirements. Feasible nodes found for the first pod are reused, and the cache is invalidated on cluster change or when a pod's requirements differ.
- **Reduced scan:** the scheduler scans the number of Running Units plus a buffer of 50 nodes, and scans that much again only if nothing fits. This trades global optimality for latency.
- **Discretized node lists** replace kube-scheduler's NodeList maintenance, for performance and node dispersion at very large scale.
- **Preemption pruning:** multi-dimensional pruning over pods and nodes, because evening-peak online scale-ups trigger mass preemption of offline work.

### Migration from YARN and Kubernetes
According to the abstract, Gödel replaced the fragmented Kubernetes and YARN clusters. ByteDance's write-up says it has been rolled out in batches in ByteDance data centers since 2022. None of the public sources read for this note (write-ups, CNCF post, KubeCon slides, podcast) describe how YARN jobs were moved: no compatibility layer, cutover steps or cluster counts. Read the full paper before claiming anything more specific.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Production cluster size | tens of thousands of nodes | production | Volcano Engine write-up |
| Largest production cluster | 20,000+ nodes, 1,000,000+ pods | production | CNCF blog |
| Peak scheduling throughput | about 5,000 pods/s (write-up); 5,000+ pods/s across multiple shards, 2,000+ in one shard (CNCF) | production / multi-instance | Volcano Engine write-up; CNCF blog |
| Resource utilization at peak | >60% CPU, >95% GPU | production | Volcano Engine write-up |
| Utilization by time of day | >60% evening peak, ~40% daytime trough (average) | production | Volcano Engine write-up, "Results" |
| kube-scheduler baseline | <200 pods/s, clusters of at most 5,000 nodes | ByteDance's comparison | Volcano Engine write-up, "Motivation/Results" |
| Single-instance throughput | ~2,600 pods/s at 5,000 nodes; ~2,000 pods/s at 20,000 nodes; over 10x kube-scheduler | microservice benchmark | Volcano Engine write-up, "Results" |
| Multi-instance peak | ~4,600 pods/s; declines beyond 5 instances | 10,000 nodes, 1–6 scheduler instances | Volcano Engine write-up, "Results" |
| Mixed online/offline | ~2,000 pods/s, roughly flat across offline share | varying online/offline mix | Volcano Engine write-up, "Results" |
| Gang throughput vs. YARN | nearly 2x | gang workloads | Volcano Engine write-up, "Results" |
| Ablation | caching ~60% of gain, reduced scan ~30% | microbenchmark | Volcano Engine write-up, "Results" |
| CPU utilization before/after | ~30% before; ~50% average, up to 60% in an ultra-large cluster | production | KubeCon NA 2024 slides, "Achievements" |
| Scheduling requirements (slides) | P99 scheduling latency < 1 min; throughput ≤ 1,000 pods/s | as worded on the slide; the write-up states the requirement as > 1,000 pods/s | KubeCon NA 2024 slides, "Scheduling at Hyper-Scale Infrastructure" |

## Limitations

- A single dispatcher and a single binder are central serialization points. Throughput peaks at a few scheduler instances and then falls as conflicts rise, so the design does not scale out without limit.
- Partition-local search and the bounded scan give locally optimal placements. There is no global packing or rebalancing after placement; a separate Gödel Rescheduler is listed as future work.
- Throughput under high deployment rates and heavy preemption is named as an open problem. The SoCC 2025 follow-up (below) targets exactly the latency spikes seen during surges.
- Queueing is FIFO in production. Fair-share and priority queuing are not yet in use, so multi-tenant fairness relies on quota elsewhere.
- Topology and load-aware features depend on Katalyst and CNR; the open-source scheduler alone does not reproduce the co-location story. The repo README states support for Kubernetes 1.21.4 up to 1.24.6.

## Relation to other systems

- **kube-scheduler:** a single scheduler running a per-pod cycle (filter/score, assume, async bind). Gödel keeps the plugin style but adds unit-level scheduling, gang admission, horizontally sharded schedulers and a separate binder that resolves conflicts.
- **Omega (EuroSys 2013):** parallel schedulers over shared cell state with optimistic transactions. Gödel uses the same concurrency model, but node partitions and a fall-back search cut down conflicts, and one binder process validates commits instead of a transactional store.
- **Borg (EuroSys 2015):** mixes prod and non-prod in one cell, with priority-based preemption and scoring shortcuts (equivalence classes, relaxed randomization). Gödel's unified pool, offline-preempted-by-online model, candidate caching and bounded scan are close analogues, rebuilt on the Kubernetes API.
- **Twine (OSDI 2020):** one control plane over large shared pools, with entitlements and host-level customization. Gödel's goal, retiring per-team pools, is similar. Gödel stays per-cluster and Kubernetes-native rather than region-wide.
- **YARN (SoCC 2013):** a two-level RM plus per-application AM, strong for batch. Gödel folds gang and batch semantics into the scheduler itself (the unit framework), so no per-job AM negotiates containers, and it serves long-running services too.
- **Volcano / Kueue:** Volcano is a batch scheduler on Kubernetes with PodGroups and queues; Gödel claims far higher gang throughput and also covers online pods. Kueue is admission-level job queueing in front of kube-scheduler and does not place pods. Gödel's unit framework does placement plus gang admission, but its queueing and quota are less developed in production.
- **Follow-up, "From Bottleneck to Breakthrough" (SoCC 2025, DOI 10.1145/3772052.3772240):** only the abstract was read when the note was written, and the DOI page could not be re-read for the 2026-11-25 check, so this summary is unverified. It targets scheduling delays in Kubernetes clusters above 10,000 nodes under sudden surges. It reports up to two orders of magnitude lower delay from redesigned data structures, algorithms and runtime strategies, deployed in production.

## Takeaways for practice

- Separate deciding from committing. Make placement computation stateless and sharded, and put all conflict checks, preemption execution and binding behind one validating commit point.
- Partition nodes across scheduler shards to make optimistic conflicts rare, but measure: the best shard count is small and workload-dependent.
- Make the gang the unit of scheduling, with a tunable `minMember`, so services and training jobs share one code path and one pool.
- Exploit homogeneity within a job: per-unit candidate caching and bounded scans brought most of the speed-up.
- Preemption is the throughput killer in a co-located pool (online surges evict offline work), so prune the victim search aggressively.
- Topology-aware placement needs accurate node-level state (CNR/Katalyst-style reporting). The scheduler alone is not enough.

## References

- Paper: https://dl.acm.org/doi/10.1145/3620678.3624663
- Code: https://github.com/kubewharf/godel-scheduler
- ByteDance write-up of the paper (Chinese): https://developer.volcengine.com/articles/7359515064715935753
- CNCF blog (ByteDance): https://www.cncf.io/blog/2024/04/02/godel-scheduler-open-sourced-a-unified-scheduler-for-online-and-offline-workloads/
- KubeCon NA 2024 slides: https://hosted-files.sched.co/kccncna2024/cd/KCNA24%20-%20Godel%20Scheduler.pdf
- Follow-up (SoCC 2025): https://doi.org/10.1145/3772052.3772240
