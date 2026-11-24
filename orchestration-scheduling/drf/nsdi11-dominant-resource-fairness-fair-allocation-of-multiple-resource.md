---
title: 'Dominant Resource Fairness: Fair Allocation of Multiple Resource Types'
authors:
- Ali Ghodsi
- Matei Zaharia
- Benjamin Hindman
- Andy Konwinski
- Scott Shenker
- Ion Stoica
affiliations: 'University of California, Berkeley'
venue: 'NSDI'
year: 2011
paper_id: b1a47759dbcf87ed132838be39f8ab244e78e2d6
abs_url: https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types
pdf_url: https://www.usenix.org/legacy/event/nsdi11/tech/full_papers/Ghodsi.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Dominant Resource Fairness: Fair Allocation of Multiple Resource Types

> **Why it matters:** DRF is the standard way to extend max-min fairness from one resource to vectors of resources (CPU, memory, later GPUs). Mesos and YARN both implement it, and it is the baseline that nearly every later multi-resource and GPU fairness paper argues against.

## Problem

Max-min fairness is well understood for one resource, but cluster tasks have heterogeneous demand vectors. In a 2000-node Facebook Hadoop cluster most tasks are CPU-heavy while some, notably reduces, are memory-heavy (§2, Fig. 1). The slot-based Hadoop and Dryad fair schedulers of the time left tasks under- or over-using their slots (Fig. 2). The paper asks what "fair" means when users want different resource mixes, and which policy keeps the properties operators need, above all that no user gains by lying about its demands.

## Core design

### Allocation properties (§3)

Four required properties, then four desirable ones:

- **Sharing incentive:** each user does at least as well as it would with a static 1/n slice of every resource.
- **Strategy-proofness:** misreporting demands cannot increase a user's allocation.
- **Envy-freeness:** no user prefers another user's allocation.
- **Pareto efficiency:** no user's allocation can be increased without decreasing another's.
- **Single-resource fairness:** with one resource, the policy reduces to max-min fairness.
- **Bottleneck fairness:** if every user's most-demanded resource is the same one, the policy reduces to max-min on that resource.
- **Population monotonicity:** when a user leaves, no remaining user's allocation decreases.
- **Resource monotonicity:** adding resources never decreases any user's allocation.

### DRF definition and algorithm (§4)

A user's **dominant share** is the largest of its shares across resources, and the user's **dominant resource** is the one that attains it. DRF applies max-min fairness to dominant shares: it maximises the minimum dominant share across users.

- **Worked example (§4.1, Table 1):** 9 CPUs and 18 GB; A's tasks need ⟨1 CPU, 4 GB⟩ (memory-dominant), B's need ⟨3 CPU, 1 GB⟩ (CPU-dominant). DRF gives A 3 tasks and B 2 tasks, a dominant share of 2/3 each.
- **Algorithm 1 (§4.2):** keep capacity R, consumed vector C, allocations U_i and dominant shares s_i. Repeatedly pick the user with the lowest s_i; if its next task D_i fits (C + D_i ≤ R), launch it and update C, U_i, s_i, otherwise stop. A heap on s_i gives O(log n) per decision.
- **Progressive filling (Appendix A.1):** the continuous version. All dominant shares rise at the same rate, other resources growing in proportion to each demand vector, until a resource saturates; users needing it freeze and the rest keep filling.
- **Weighted DRF (§4.3):** per-user, per-resource weights; dominant share becomes max_j(u_ij / w_ij). With equal weights per user, dominant shares are proportional to weights; all-ones weights give plain DRF.

### Alternatives (§5) and property analysis (§6)

- **Asset fairness (§5.1)** equalises the sum of each user's shares (example: A ≈2.52, B ≈2.16 tasks, Fig. 4). It violates sharing incentive (Thm 1, §6.1.1), bottleneck fairness and resource monotonicity (Table 2; the extracted table was misaligned, so which policy breaks which property is rebuilt from the theorems in §6).
- **CEEI (§5.2)**, competitive equilibrium from equal incomes (equivalently, maximising the Nash product), gives A 45/11 and B 18/11 tasks (Fig. 4) and uses all 9 CPU and 18 GB, where DRF leaves 4 GB idle (§5.3). Market clearance is what makes it manipulable (Thm 4, §6.1.2); it also violates population monotonicity (Table 2).
- **DRF** satisfies every Table 2 property except resource monotonicity; Thm 6 (§6.1.3) shows no policy has sharing incentive, Pareto efficiency and resource monotonicity together. Its leximin form is a lexicographic Kalai–Smorodinsky solution (§8).
- **Discrete tasks (§6.2, Thm 7):** machine-by-machine DRF stays within one max-task of the continuous allocation.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| DRF allocation in the worked example | A: 3 tasks (3 CPU, 12 GB); B: 2 tasks (6 CPU, 2 GB); dominant share 2/3 each | 9 CPU, 18 GB; A ⟨1,4⟩, B ⟨3,1⟩ | §4.1, Table 1 |
| Asset-fairness allocation, same example | A ≈ 2.52 tasks, B ≈ 2.16 tasks | same | §5.1, Fig. 4 |
| CEEI allocation, same example | A 45/11 tasks, B 18/11 tasks | same | §5.2, Fig. 4 |
| Cost per scheduling decision | O(log n) for n users | binary heap on dominant shares | §4.2 |
| CEEI manipulation | user 1 gains from ≈3.2 to ≈4.2 tasks; user 2 falls from ≈48.8 to ≈33.3 | 100 units of each resource; demands ⟨16,1⟩, ⟨1,2⟩ | §6.1.2, Thm 4 |
| Asset-fairness sharing-incentive violation | user 1 gets 6 tasks, user 2 gets 12 (below 50% of each resource) | 30 units of each resource; demands ⟨1,3⟩, ⟨1,1⟩ | §6.1.1, Thm 1 |
| Discrete-allocation gap | at most one max-task between any two users | K machines, each fits ≥1 max-task | §6.2, Thm 7 |
| Dynamic sharing on Mesos | job 1 ≈70% of RAM and job 2 ≈75% of CPU (both dominant shares above 50%) | 48-node EC2 Mesos cluster, 4 CPU / 14 GB allocatable per node, first 2-min phase | §7.1, Fig. 8 |
| Slot baselines compared | 3, 4, 5 and 6 slots per machine, plus CPU-only fair sharing | 48 nodes, 8 CPU / 6 GB per node, 80 tasks per job | §7.2, Figs. 9–12 |
| Job completion time vs. Hadoop fair scheduler | −3% for small jobs (no gain); up to 66% reduction for larger jobs | Facebook trace (2000 nodes, 1 week, Oct 2010) replayed on 400 simulated nodes with 12 slots, 16 cores and 32 GB each | §7.3, Fig. 14 |

§7.2 states DRF has the lowest response times and highest throughput: slots under- or oversubscribe nodes, and CPU-only fairness completes far fewer large jobs by overcommitting memory (bar values omitted as unreadable). Fig. 13 shows higher CPU and memory utilisation than slot fairness, with no single figure given.

## Limitations

- Leaves capacity idle (4 GB in §5.3) and is not resource monotonic (§6.1.3).
- Theory assumes a fixed per-task demand vector and unbounded tasks per user; real demands drift and are misestimated (Quasar's premise).
- Treats the cluster as one pooled vector: fragmentation, locality and placement constraints are future work (§9.1).
- Fairness is instantaneous; no treatment of preemption cost, gang scheduling or finish-time fairness, all central for GPU training.
- Open: is DRF the only strategy-proof, Pareto-efficient policy (§9.1)?

## Relation to other systems

- **Mesos (NSDI 2011):** the master decides what to offer each framework via a pluggable allocation module; frameworks accept or reject offers and can set filters. Its fair-sharing module, a multi-resource generalisation of max-min fairness, cites DRF. DRF's §7 runs as Mesos allocation modules that offer freed resources to the framework with the smallest dominant share.
- **YARN:** the Capacity Scheduler's `yarn.scheduler.capacity.resource-calculator` defaults to `DefaultResourceCalculator` (memory only); `DominantResourceCalculator` "uses Dominant-resource to compare multi-dimensional resources such as Memory, CPU etc." The Fair Scheduler offers `drf` as a queue `schedulingPolicy`. Here DRF is a comparator inside hierarchical queues, not a full mechanism with the paper's guarantees.
- **Tetris (SIGCOMM 2014):** argues strictly fair allocations hurt performance; packs tasks by multi-dimensional bin-packing over CPU, memory, disk and network and favours jobs with less remaining work, reporting over 30% better makespan and job completion time (250-node YARN plus simulation) with near-perfect fairness. It targets the fragmentation DRF defers.
- **Quasar (ASPLOS 2014):** drops user-declared reservations; users give performance targets and classification infers scale-up, scale-out, hardware and interference effects to drive joint allocation and placement (47% higher utilisation on 200 EC2 servers). DRF takes demands as given; Quasar estimates them.
- **Gandiva (OSDI 2018):** uses the predictability of mini-batch iterations to time-slice GPUs, introspect and migrate jobs (26% higher utilisation on 180 GPUs). Its goal is efficiency for placement-sensitive DL jobs, not vector fairness.
- **Themis (NSDI 2020):** argues existing disciplines misfit long-running, gang-scheduled, placement-sensitive ML jobs; defines finish-time fairness and runs a two-level GPU auction (over 2.25× fairer, 5–250% more efficient on a production trace). Like Mesos it is two-level, but fairness is over finish times, not dominant shares.

## Takeaways for practice

- Weighted dominant shares are a cheap default for multi-resource fairness: a heap on dominant share fits any offer or queue scheduler.
- Strategy-proofness matters in practice: market-clearing schemes like CEEI reward inflated requests; DRF trades some idle capacity for honest ones.
- Schedule against demand vectors, not slots, but handle fragmentation and placement separately (e.g., Tetris-style packing).
- The sharing-incentive guarantee (weighted dominant share ≥ 1/n) is the tenant contract for a shared cluster.
- For GPU training, DRF is the baseline, not the answer: gang scheduling and long jobs push toward finish-time fairness (Themis) and introspection (Gandiva).

## References

- Paper: https://www.usenix.org/legacy/event/nsdi11/tech/full_papers/Ghodsi.pdf
- Landing page: https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types
- Slides (USENIX): https://static.usenix.org/events/nsdi11/tech/slides/ghodsi.pdf
- Mesos (NSDI 2011): https://www.usenix.org/conference/nsdi11/mesos-platform-fine-grained-resource-sharing-data-center
- YARN Capacity Scheduler docs: https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/CapacityScheduler.html
- YARN Fair Scheduler docs: https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/FairScheduler.html
- Tetris (SIGCOMM 2014): https://www.doi.org/10.1145/2619239.2626334
- Quasar (ASPLOS 2014): https://doi.org/10.1145/2541940.2541941
- Gandiva (OSDI 2018): https://www.usenix.org/conference/osdi18/presentation/xiao
- Themis (NSDI 2020): https://www.usenix.org/conference/nsdi20/presentation/mahajan
