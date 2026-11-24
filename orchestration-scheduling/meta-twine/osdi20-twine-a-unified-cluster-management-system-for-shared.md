---
title: 'Twine: A Unified Cluster Management System for Shared Infrastructure'
authors:
- Chunqiang Tang
- Kenny Yu
- Kaushik Veeraraghavan
- Jonathan Kaldor
- Scott Michelson
- Thawan Kooburat
- Aravind Anbudurai
- Matthew Clark
affiliations: 'Facebook'
venue: 'OSDI'
year: 2020
abs_url: https://www.usenix.org/conference/osdi20/presentation/tang
pdf_url: https://www.usenix.org/system/files/osdi20-tang.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Twine: A Unified Cluster Management System for Shared Infrastructure

> **Why it matters:** Twine runs a whole region of about one million machines as one shared pool under one sharded control plane. Machines, sometimes reconfigured on the way, move to workloads; jobs are not pinned to fixed clusters.

## Problem

Facebook's fleet had grown into per-workload private pools tied to physical clusters, each with its own control plane. Jobs could not move between clusters, so capacity got stranded. A hardware refresh meant manual migration tickets: for a 2016 refresh, P50 time to close one was 7.5 days and P100 was 87 days (Fig. 1). Services also wanted specific kernel, sysctl, hugepage or Turbo settings, which is easy in a private pool and hard in a shared one. And generic rolling updates and maintenance don't know replica placement, so they can take down several replicas of a shard at once. The goal was fungible hardware across a region: one shared pool (twshared) that still meets per-application needs.

## Core design

### Allocator/scheduler split (§2.1–2.4, Fig. 4)
- **Scheduler**: manages job and task lifecycle, failure handling and change pacing, and talks to TaskControllers. The paper maps it to Kubernetes *controllers*.
- **Allocator**: assigns machines to entitlements and tasks to machines. The paper maps it to the Kubernetes *scheduler*. It runs regionally on an in-memory write-through cache of machine state. Multiple threads allocate concurrently with optimistic concurrency control, and job-level results are cached, with a hit ratio typically above 99% (§2.3).
- **ReBalancer**: runs asynchronously with a constraint solver to improve the allocator's decisions (spread, fragmentation, swapping machines between entitlements), keeping slow global optimization off the critical path (§2.2, §3.2).
- **Resource Broker (RB)**: one per data center. It is the source of truth for machine assignment and unavailability, fed by a Health Check Service. Supporting components: an Agent on each machine, Sidekick (switches host profiles), SRM (autoscaling), Front End and Capacity Portal.

### Entitlements as pseudo-clusters (§2.2)
- An entitlement is a quota, in machine counts or Relative Resource Units, backed by dynamically allocated machines that act as a "pseudo cluster". Jobs bind to entitlements, not clusters, and tasks stack on the entitlement's machines.
- An entitlement can span the data centers of a region and holds 0 machines up to its quota. Free machines form a regional pool that the allocator draws from and returns to.
- Spreading tasks across fault domains shrinks buffers. Losing one of 12 main switchboards (MSBs) in a single DC needs about 8.3% buffer; spreading across 60 MSBs in five DCs needs about 1.7% (§2.2, Fig. 6).
- A job moves between clusters by machine reassignment plus a task stop and restart. There is no live migration (§2.2).

### Sharding instead of federation (§3–4)
- Schedulers and allocators are sharded **by entitlement**. Each job belongs to exactly one shard, and an entitlement can move between shards without restarting its tasks (§3.1).
- Every component is sharded and scales on its own. Stateful components use external persistent stores, "like Kubernetes and unlike Borg" (§3.2).
- Availability principles (§4): a shard failure affects only a slice of the region; tasks keep running even if all of Twine fails; destructive operations are rate-limited by fail-safes.
- Short-lived batch work goes to application-level schedulers. They hold and reuse Twine tasks and can nest containers. This gives three levels: RB manages machines, Twine manages containers, and application schedulers manage workloads (§3.2, §8).

### TaskControl (§2.5, Fig. 8)
- The scheduler sends an application's TaskController proposed operations (restarts, moves, updates), completions, maintenance notices with deadlines, and unhealthy-task lists. The controller acks the subset it allows, so it can delay or batch operations. Before a maintenance deadline it can move tasks, stop and restart them, or leave them running.
- **Shard Manager** (§2.7), the scheduler for sharded services, uses TaskControl so that replicas of one shard don't go down together.

### Host profiles (§2.6)
- Each entitlement has one host profile covering the kernel, sysctls, hugepages, cgroup v2, storage and NIC configuration, Turbo Boost and prefetch. Sidekick applies it when a machine joins the entitlement. P90 switching time is 3.0 s for Turbo versus 244 s for hugepages (Fig. 17).

### Autoscaling and small machines (§2.8, §5)
- SRM scales jobs horizontally, and the machines it frees go back to the pool.
- Facebook standardized on single-socket machines with one 18-core CPU and 64 GB RAM. Under the same rack power budget, a rack holds 92 small or 30 big machines (§2.8). Few hardware types keep the pool fungible.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Machines under one control plane | ~1M | One region | Abstract, §1 |
| twshared share of fleet | 56% (vs 15%) | Oct 2020 (vs Jan 2019) | Fig. 3 |
| Largest scheduler shard | ≈170K machines, up to 40 cores and 80 GB memory | Production | §3.1 |
| Planned sharding | 50K machines per shard, 20 shards for 1M | Projection | §3.1 |
| Largest entitlement / job | ≈60K machines / ≈15K tasks | Production | §3.1 |
| Allocator peak | ≈1,000 job allocations/s, 36 tasks per job on average | Large allocator | §3.1 |
| TaskControl experiment | 15,000 shards × 3 replicas on 1,000 tasks | Cache rolling update | §5.1, Fig. 14 |
| Autoscaling | ≈800 services; up to 25% of web machines freed off-peak | Production | §5.2 |
| Host-profile churn | one change per machine every two days on average | Production | §5.3 |
| Regression without host profiles | web 11%, memcache 10.2% | — | §7.2 |
| Small machines | 83% average RTCO (17% TCO savings), including 18% power savings | Fleet-wide | §5.4, Fig. 19 |
| twshared gains | ≈3% utilization (buffer consolidation), ≈2% (Turbo), ≈2% capacity (autoscaling) | 2020 | §6.1 |
| twshared utilization | ≈40% memory, ≈30% CPU | Oct 2020 | §6.1 |
| Global jobs | 8% of jobs | Production | §7.3 |

## Limitations

- **One job, one shard.** A job must fit in a single scheduler shard (§3.1). The authors call this non-binding today, but it is a hard ceiling.
- **No live migration.** Every move is a stop and restart, which is costly for long-running stateful jobs.
- **Entitlements doing double duty.** They serve as both partitioning and quota, which fragments capacity. The team is splitting them into "materializations" and "stackable reservations" (§7.1).
- **Customization versus fleet optimization.** Per-task customization hurt autoscaling and fleet-wide optimization and is being removed (§7.2).
- **The region is the fungibility boundary.** Global jobs are moving to a federation over regional deployments (§7.3).
- **Modest utilization.** About 30% CPU (§6.1). CPU and memory are not overcommitted by default, only power, and vertical autoscaling is future work (§8). Opportunistic capacity has no SLO (§6.1).
- **Hardware bet.** Re-architecting memory-bound services for small machines cost more than expected (§7.4).
- **No accelerators.** GPUs are not discussed; batch and ML go to application-level schedulers.

## Relation to other systems

- **Borg.** Borg runs a control plane per cell. Twine runs one sharded control plane per region, uses external state stores (§3.2), and moves *machines* between entitlements rather than jobs between cells (§3.3). Borg overcommits CPU and memory; Twine by default overcommits only power (§8).
- **Kubernetes.** The paper cites the central API server and store as limiting a cluster to about 5K machines (§3.2). Federation splits jobs across static clusters through a Federation Manager; Twine shards one control plane instead (§3.3, §8). The authors know of no custom controller that offers lifecycle allow/delay hooks like TaskControl's (§8).
- **Mesos / YARN.** Entitlements resemble resource offers, and scheduler shards resemble Application Masters. Those systems' bottom layer is single-cluster, while Twine's spans a region. TaskControl negotiates *lifecycle operations*, not resources (§8).
- **Omega.** The paper does not cite Omega; this comparison is my own. The allocator's optimistic concurrency over a shared machine view resembles Omega's shared-state design, but Twine partitions control by entitlement shard rather than having full schedulers contend over one cell state.
- **MAST (OSDI 2024).** From the same organization, with Chunqiang Tang as a co-author. Its abstract describes a global scheduler that places ML training jobs *and data* across regions, built on temporal decoupling, scope decoupling and exhaustive search. It cut the most overloaded region's high-priority GPU demand-to-supply ratio from 2.63 to 0.98. This targets exactly what Twine leaves out: cross-region placement and GPU training. The MAST paper itself (§2, §4.4) says MAST runs on top of Twine: MAST's region schedulers decide placement, then tell Twine to preempt or checkpoint victims, create containers and restore jobs within each dynamic cluster (see the [MAST deep read](../meta-mast/c286274-mast-global-scheduling-of-ml-training-across-geo-distributed.md)).

## Takeaways for practice

- **Decouple quota from physical location.** Entitlements filled from a regional free pool remove manual capacity moves and shrink failure buffers.
- **Split fast placement from global optimization.** Use a cached, optimistically concurrent allocator for placement, plus an asynchronous solver to repair fragmentation and spread.
- **Shard by tenant unit.** Sharding by entitlement keeps each job in one shard and is simpler than federating independent clusters.
- **Give applications a lifecycle veto.** Allow/delay acks and maintenance deadlines make sharded stateful services, inference replicas and checkpoint-aware training safe on shared infrastructure.
- **Make node configuration part of allocation.** Apply host profiles just in time, budget for slow switches, and watch the churn that autoscaling drives.
- **Survive control-plane loss.** Tasks must keep running if the control plane is down, and every destructive operation needs a rate limit.
- **Homogeneity enables fungibility.** Heterogeneous, topology-sensitive GPU fleets are why systems like MAST add higher-level schedulers.

## References

- Paper: https://www.usenix.org/conference/osdi20/presentation/tang
- PDF: https://www.usenix.org/system/files/osdi20-tang.pdf
- Related: MAST, OSDI 2024: https://www.usenix.org/conference/osdi24/presentation/choudhury
