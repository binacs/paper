---
title: 'Large-scale cluster management at Google with Borg'
authors:
- Abhishek Verma
- Luis Pedrosa
- Madhukar R. Korupolu
- David Oppenheimer
- Eric Tune
- John Wilkes
affiliations: 'Google'
venue: 'EuroSys'
year: 2015
paper_id: 3a043714354fe498752b45e4cf429dbae0fb2558
doi: 10.1145/2741948.2741964
abs_url: https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/
pdf_url: https://research.google.com/pubs/archive/43438.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Large-scale cluster management at Google with Borg

> **Why it matters:** The first detailed public account of a production, centralised, priority-and-quota cluster manager that co-locates services and batch on shared 10k-machine cells, plus a reusable way (cell compaction) to measure what a scheduling policy actually saves.

## Problem

Google runs hundreds of thousands of jobs from thousands of applications on tens of thousands of machines, mixing latency-sensitive services with batch. Borg must hide resource management and failure handling from users, stay highly available, and use hardware efficiently. The paper describes the design and quantifies which policies (sharing, large cells, fine-grained requests, reclamation) matter for utilisation.

## Core design

### User model (§2)
- **Cell:** a set of heterogeneous machines managed as one unit. **Job:** name, owner, task count, hard or soft constraints. **Task:** Linux processes in a container on one machine, with a fine-grained resource vector rather than fixed slots. Updates roll out as an undoable, non-atomic transaction with a cap on disruptions.
- **Alloc / alloc set:** a reserved slice of one machine (or of several) that stays assigned whether used or not; tasks run inside it. Used for helpers such as log savers; the ancestor of the Kubernetes pod.
- **Priority bands:** monitoring > production > batch > best effort. Higher preempts lower, but production tasks never preempt each other, to avoid preemption cascades. "Prod" = monitoring + production.
- **Quota:** a resource vector at a priority for a period (typically months), checked at **admission**: jobs without quota are rejected at submit, not left pending. Priority-zero quota is unlimited but often unsatisfiable. Quota allocation itself sits outside Borg, tied to capacity planning.
- **Naming:** stable BNS names (cell/job/task index), with host:port written to Chubby.

### Borgmaster / scheduler split (§3.1–3.3)
- **Borgmaster:** logically one process, replicated five times on a Paxos-based store; the elected leader handles all mutations. Checkpoints (snapshot + change log) drive **Fauxmaster**, a simulator running the real Borgmaster code against stubbed Borglets.
- **Scheduler:** a separate process working on a cached copy of cell state; it submits assignments and the master rejects any based on stale state (optimistic concurrency, "similar in spirit" to Omega). Pending tasks are scanned high to low priority, round-robin across users within a priority.
- **Feasibility checking:** machines that meet constraints and have enough "available" resources, counting resources held by evictable lower-priority tasks as available.
- **Scoring:** minimise number and priority of preempted tasks, prefer machines that already hold the task's packages (startup is dominated by package install), spread across failure domains, and mix high and low priority on a machine so the high one can absorb spikes. The paper contrasts E-PVM (spreading/worst fit, fragments for large tasks) with best fit (tight, punishes misestimates and bursty load) and uses a hybrid that minimises stranded resources. Victims are preempted lowest priority first and requeued.
- **Borglet:** per-machine agent. The master **polls** it every few seconds, which controls the rate and avoids recovery storms; per-replica stateless **link shards** aggregate and diff Borglet state. Running tasks survive a master or Borglet outage.

### Scheduler scalability (§3.4)
- **Score caching:** feasibility/scores are cached until machine or task properties change; small resource changes are ignored to reduce invalidation.
- **Equivalence classes:** feasibility and scoring run once per group of tasks with identical requirements and constraints, not per task.
- **Relaxed randomisation:** examine machines in random order until enough feasible candidates are found, then pick the best of that sample instead of scoring the whole cell.

### Resource reclamation (§5.5)
Each task has a **limit** (its request) and a **reservation** (predicted use). The reservation starts at the limit, decays after 300 s towards usage plus a safety margin, is recomputed every few seconds from Borglet data, and jumps up if usage exceeds it. Prod tasks are scheduled against limits, so they never depend on reclaimed capacity; non-prod tasks are scheduled against existing tasks' reservations and are throttled or killed, never prod, if estimates are wrong. A live four-week experiment with tighter margins showed slightly more OOMs; the medium setting was rolled out.

### Isolation (§6)
cgroup containers; compressible resources (CPU, disk I/O) are throttled, non-compressible ones (memory, disk) trigger kills from lowest priority up; latency-sensitive tasks can preempt batch in a modified CFS.

### Cell-compaction methodology (§5.1)
Instead of average utilisation, ask **how small a cell can be and still fit its workload**. In Fauxmaster, using real checkpoints from 15 cells, machines are removed at random and the whole workload is repacked from scratch at each step until it no longer fits. Machine-pinned server/storage tasks are excluded; hard constraints become soft for jobs larger than half the original cell; a small fraction of very picky tasks may stay pending. Each experiment runs with several seeds and the 90th-percentile size is reported (a conservative administrator's view). Alternative policies are then expressed as extra machines needed relative to this baseline.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Median cell size | ~10k machines | excluding test cells | §2.2 |
| Prod share | ~70% CPU allocated / ~60% CPU used; ~55% RAM allocated / ~85% RAM used | representative cell | §2.1 |
| Borgmaster failover | 5 replicas; election ~10 s, up to ~1 min in big cells | Paxos store | §3.1 |
| Median task startup | ~25 s, ~80% package installation | — | §3.2 |
| Hybrid scoring vs best fit | ~3–5% better packing | — | §3.2 |
| Busy Borgmaster | 10–14 CPU cores, up to 50 GiB RAM | — | §3.4 |
| Task arrivals | >10,000 tasks/min in several cells | — | §3.4 |
| Full-cell schedule from scratch | few hundred seconds; >3 days without §3.4 optimisations (did not finish) | — | §3.4 |
| Borgmaster availability | 99.99% | in practice | §4 |
| Compaction setup | 15 cells, 11 seeds, 90th percentile; ≤0.2% picky tasks may stay pending | Fauxmaster, 2014-10-01 checkpoints | §5.1 |
| Segregating prod / non-prod | 20–30% more machines | median cell | §5.2, Fig. 5 |
| Splitting off large users | 2–16× as many cells, 20–150% more machines | 10 TiB / 100 TiB RAM thresholds | §5.2, Fig. 6 |
| Interference from sharing | mean CPI 1.58 shared vs 1.53 dedicated (~3%) | — | §5.2 |
| Power-of-two request buckets | 30–50% more resources | median | §5.4, Fig. 9 |
| Work on reclaimed resources | ~20% of workload | median cell | §5.5 |
| Machine density | 50% of machines run ≥9 tasks; 90%ile ~25 tasks, ~4,500 threads | — | §6 |

### What changed by 2019 ("Borg: the Next Generation", EuroSys 2020)

Read through the full prose (an open-access copy); values shown only in charts were not available. From the May 2019 trace vs the 2011 trace:
- 8 cells, 96.4k machines, 31 days vs 1 cell, 12.6k machines; priorities 0–450 grouped into free, best-effort batch (beb), mid, production and monitoring tiers (Table 1, §2–3).
- Alloc sets are 2% of collections but 20% of CPU and 18% of RAM allocations (§5.1).
- CPU and memory allocations routinely exceed 100% of capacity (over-commit); beb uses about 20% of capacity, absorbing work that was in the free tier (§4).
- Median job submission rate up ~3.7× (885 → 3,309 jobs/hour per cell); resubmitted-to-new task ratio 0.66:1 → 2.26:1 (§6.1–6.2).
- More heavy-tailed: top 1% of jobs use 99.2% of CPU (97.3% in 2011) (Table 2, §7).
- New: job dependencies, a batch queueing scheduler, Autopilot vertical scaling (§3, §8).

## Limitations

- **Jobs are the only grouping:** no first-class multi-job service; topology is encoded in job names (§8.1).
- **One IP per machine:** ports become a scheduled resource (§8.1).
- **Power-user spec:** ~230 BCL parameters (§8.1).
- **Per-cell scope:** cross-cell placement, quota allocation and capacity planning are outside the paper.
- **User-set limits:** reclamation (and later Autopilot) mitigate over-requesting instead of removing it, at the cost of some OOMs (§5.5).
- **One built-in policy:** no batch queueing or gang semantics in the 2015 design; no accelerator or network-topology-aware placement described.

## Relation to other systems

- **Omega (EuroSys 2013):** parallel schedulers over shared state. Borg uses optimistic commit for its scheduler process but keeps one "one size fits all" scheduler and state machine (§7).
- **Mesos (NSDI 2011):** two-level offers, frameworks place, DRF fairness. Borg centralises request-based placement and uses priority plus quota instead of DRF.
- **YARN (SoCC 2013):** Hadoop-centric per-app masters against a central RM; Borg ran a similar MapReduce pattern from ~2008, but its core targets long-running services.
- **Kubernetes ("Borg, Omega, and Kubernetes", ACM Queue 2016):** pods = allocs, labels instead of job-name grouping, IP per pod, label-selector services, and an API server with composable controllers replacing the monolithic master: the fixes for §8.1.
- **Twine (OSDI 2020, Facebook):** one control plane per region (up to ~1M machines) instead of per cell, moving jobs between clusters; TaskControl lets applications take part in container lifecycle events, and host profiles retune machines. Borg's update policy is not application-aware.
- **Gödel (SoCC 2023, ByteDance):** Kubernetes-based unified online/offline scheduler with a dispatcher, scheduler shards over node partitions using optimistic concurrency, and a conflict-resolving binder: Omega-style sharding on a Kubernetes substrate, chasing the same co-location gains Borg measured.

## Takeaways for practice

- Evaluate policies with **compaction** (machines needed to fit a real workload, repacked from scratch, several seeds, high percentile), not average utilisation.
- **Co-locate** services and batch; segregation cost 20–30% more machines. Make batch the only victim via priority bands and throttle/kill rules.
- Split **limit** from **reservation** and run lower tiers in the gap; tune the margin with live experiments.
- Enforce **quota at admission** and priority at scheduling; forbid preemption inside the top band.
- **Equivalence classes, score caching and sampled feasibility** turn days into minutes; identical tasks in GPU gang jobs benefit the same way.
- Keep requests fine-grained; power-of-two buckets cost 30–50% more resources.
- Ship a **simulator running production scheduler code** on real checkpoints.

## References

- Paper: https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ (PDF: https://research.google.com/pubs/archive/43438.pdf)
- Borg: the Next Generation (EuroSys 2020, DOI 10.1145/3342195.3387517): https://research.google/pubs/borg-the-next-generation/
- Twine (OSDI 2020): https://www.usenix.org/conference/osdi20/presentation/tang
- Gödel scheduler (CNCF blog): https://www.cncf.io/blog/2024/04/02/godel-scheduler-open-sourced-a-unified-scheduler-for-online-and-offline-workloads
