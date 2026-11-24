---
title: 'Protean: VM Allocation Service at Scale'
authors:
- Ori Hadary
- Luke Marshall
- Ishai Menache
- Abhisek Pan
- Esaias E Greeff
- David Dion
- Star Dorminey
- Shailesh Joshi
affiliations: 'Microsoft Azure, Microsoft Research'
venue: 'OSDI'
year: 2020
abs_url: https://www.usenix.org/conference/osdi20/presentation/hadary
pdf_url: https://www.usenix.org/system/files/osdi20-hadary.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Protean: VM Allocation Service at Scale

> **Why it matters:** This paper describes how a production IaaS VM scheduler stays explainable (an ordered rule list) and still places VMs in milliseconds over tens of thousands of machines. It does this by aggressive incremental caching and optimistic concurrency between allocation agents.

## Problem

Azure must place VM requests onto machines in an availability zone of 10k–100k servers (Abstract, §1). The VM catalog is large and skewed: more than 500 VM types (§1), a few types dominate a zone's workload (Table 2), and the hardware spans several generations (Table 1). Demand is diurnal and spiky (Figs. 3–4), and most requests are for a single VM (§2.2). Placement quality matters financially: the paper says a 1% reduction in fragmentation is worth on the order of $100M per year (§1). Latency matters too: an allocation is expected in about 20 ms (§3.1). Re-evaluating every constraint and preference over 10–15k candidate machines per request misses that budget once the candidate set grows past roughly a couple of thousand machines (§5.1). The policy also has to stay adaptable and interpretable to operators while it changes often (§3.1, §3.4).

## Core design

The central idea is to separate **policy** (rules) from **mechanism** (caching plus concurrency).

### Rule-based Allocation Agent (§3)
- **Validator rules** are Boolean hard constraints, `IsValid(x, v)`, over a cluster or machine x and a VM v. Examples are `AreNodeResourcesValid` and `IsTypeSupported`.
- **Preference rules** are soft scores where lower is better. Examples are `BestFit` (resource fit weighted by scarcity), `PreferNonEmptyMachines` (packing) and `PreferEmptierClusters` (balance across clusters).
- **Two-level hierarchy.** Cluster-selection rules filter and sort clusters and keep the best k, with k configurable in [8,16]. Machine-selection rules then filter and rank machines inside those clusters. A randomized tie-break picks the final machine (§3.2). There are about one hundred rules in total (§3.2).
- **Combining preferences.** Each rule exposes `Compare(x, y | v)`. Results are summed with exponentially spaced weights generated from the rule ranking, so the rules act as a strict lexicographic order: a lower rule only breaks ties left by the rules above it (§3.3).
- **Quantization.** Each score in [0,1] is bucketed into N levels with a ceiling transform. This deliberately creates ties, so lower-priority rules (and the random tie-break) still get a say. Rule order and bucket counts are tuned with simulation and production telemetry (§3.3, §6.3).

### Architecture (§4, Algorithm 1)
- Several **Allocation Agents (AAs)** run concurrently with optimistic concurrency. Each AA has a full but possibly stale view of the inventory.
- Each machine runs one process with one worker thread per AA. A load balancer routes requests to processes, and each process has a shared work queue. The number of AAs is sized for peak instantaneous demand.
- A replicated **placement store** is the authority on placements. It detects conflicts and serializes commits to the same node, while commits to different nodes run in parallel. A **pub/sub** service sends store changes, plus health and capability updates, back to the AAs. A conflict failure returns the latest state of the affected machines.
- **Algorithm 1.** ORDER the request's VMs to reduce fault-domain rejections, assign each VM in sequence, then COMMIT them all at once. On a conflict the AA rolls back and re-queues the request until MAX_RETRIES, which is set above 10. The next request can be processed while a commit is in flight.

### Caching (§5.2)
- **Rule objects** are cached per distinct value of the request traits the rule depends on, for example one object per VM type. Each object keeps per-machine state so that `IsValid` and `Compare` run in O(1) after an incremental `Update(x1..xm)`. The pool has a fixed size with LRU eviction plus age-based eviction.
- **RuleEvaluation objects** cache a whole evaluation for one trait vector: a sorted list of valid machines plus references to the rule objects. An update refreshes the rule objects, removes the changed machines, re-validates them and re-inserts them. The cost is M log N, where M is the number of changed machines, on the order of tens (§5.2.2).
- **Shared-Caches** hold state that several rules use, such as emptiness tracking. Dependencies are updated before the objects that depend on them.
- **Revision journal.** Each AA keeps the latest state per machine stamped with a global revision. Each cache records the last revision it consumed, so update cost scales with how many machines changed, not with inventory size. An idle AA refreshes caches in the **background** (§5.2.4).
- **Cells.** A rule that compares groups, such as racks, would dirty a whole group on any change. So the inventory is partitioned into cells (racks), caching is done per cell, and the per-cell winners are then compared (§5.2.5).

### Conflict handling (§5.3)
- **Fine-grained detection.** A commit made from a stale view still succeeds if it neither over-commits resources nor breaks an anti-colocation constraint. The valid placement is merged into the machine's current state.
- **Conflict avoidance.** With a probability proportional to the recent conflict ratio over a rolling window of commits, an AA picks randomly from the top N0 machines instead of the best set. This trades a little placement quality for fewer collisions during load spikes.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Zone size served | 10–100k machines | Production | Abstract, §1 |
| Typical allocation latency | ~20 ms per VM | Production | §1, §3.1 |
| Avg latency, RuleEvaluation cache hit | close to 20 ms | Production, large zone, 2 months | §6.2, Fig. 10 |
| Latency, cache miss | typically 70–80 ms | Same | §6.2, Fig. 10 |
| Peak production demand | up to 2,000 requests/s | Production | §1 |
| Machines updated per allocation | ~50 (hit) vs ~2,000 (miss, 6.6% of machines) | Production, ~30k-machine zone, 1 day | §6.2 |
| Share of machine updates done in background | 80–96% | Production | §6.2 |
| Cache memory | around 1 GB for 10k machines | Production | §1 |
| Memory per AA vs inventory size | sublinear, ~x^0.73 | Production, all zones | §6.2, Fig. 12 |
| Retries | 99.9th-percentile allocations succeed after three retries | Production | §4 |
| Conflict drop from fine-grained detection | 25% | One of the busiest zones, vs rejecting all stale decisions | §5.3 |
| Spike handling, 5 AAs vs 1 | more than 3x less time | Low-fidelity simulator, ~25k machines | §6.2, Fig. 13 |
| Scale-test throughput | over 10k requests/s, then plateaus | Simulator, trace sped up by up to 1000x, up to 500 AAs | §6.2, Fig. 15 |
| Packing density (PD), 1 / 3 / ∞ buckets | 83.5% / 86.3% / 89.1% | Low-fidelity simulator, one zone, 5-month trace | §6.3, Table 5 |
| P99 conflicts/min, 1 / 3 / ∞ buckets | 13.4 / 11.6 / 18.0 | Same | §6.3, Table 5 |
| Buckets used in production | 3 | Production | §6.3 |
| Key utilization metric | 85–90% | Production (metric not named) | Abstract |
| Single-VM requests | 94% (99% for ≤5 VMs) | Workload analysis | §2.2 |
| Requests with zero reuse distance | more than 80% | One zone, one day | §2.2, Fig. 2 |

Definitions (§6.3): packing density is allocated cores divided by (number of non-empty machines × cores per machine). CFR is the fraction of allocations that are successfully deployed, with a target of four nines. During the COVID-19 capacity crunch, cluster utilization limits were raised by 1%, and Protean was used to recommend migrations off fragmented machines (§6.3, Fig. 16; absolute values are not given).

**Inconsistencies and caveats in the paper's figures:**
- The abstract says allocations take "a few milliseconds", but §1 and §6.2 give ~20 ms per VM on average. §5.2.4 says "few ms" for a request with an up-to-date cache.
- For the NodeResources Shared-Cache, the §6.2 text gives a hit ratio "around 20%", while the Fig. 9 bar labels read 13%. The text does not say which label belongs to which cache.
- The simulator models a hit as 14 ms and a miss as 88 ms (§6.2). That miss figure differs from the 70–80 ms measured in production.
- §5.2.2 says the number of changed machines is "in the order of tens", while §6.2 reports ~50 on a hit.
- The abstract does not name the metric behind the 85–90% utilization figure.

## Limitations

- The paper does not account for power. A separate power-capping system handles power budgets (footnote 2). Harvesting and interference mitigation are out of scope (§7).
- The multi-AA throughput and conflict results (Figs. 13–15) come from a low-fidelity simulator that models the cache as a Bernoulli hit with p = 0.9 (§6.2). They are not production measurements. Throughput plateaus at scale as conflicts rise (§6.2).
- Rule order, weights and bucket counts are hand-tuned by trial and error (§3.3). There is no optimization formulation or optimality guarantee.
- Placement is greedy, one request at a time. Defragmentation needs migrations recommended outside the allocator (§6.3). (Own analysis)
- The cache design depends on low trait diversity and slow inventory change (§5.1). A workload with many unique request shapes would lower hit ratios. (Own analysis)
- VM lifetimes may be understated for VMs still running when data was collected (Fig. 5).

## Relation to other systems

- **Borg:** Borg also caches node scores and uses equivalence classes within a job. Protean shares cached rule and evaluation state across tenants and request types, and it does not sample machines the way Borg's relaxed randomization does (§7).
- **Omega:** Both are shared-state, optimistic-concurrency schedulers. Protean adds fine-grained merging of stale decisions and probabilistic conflict avoidance (§5.3, §7).
- **Apollo / Mercury:** These let conflicting decisions queue at the target node and resolve them later. Protean fails fast on a conflict so higher-level services can retry elsewhere (§7).
- **Sparrow:** Sparrow places tasks by random probing. Protean evaluates the full inventory, using cluster selection and caching (§7).
- **Firmament / Quincy:** The paper calls these monolithic flow-based schedulers harder to scale and too slow in batch mode for its latency and throughput targets (§7).
- **Mesos / YARN:** The paper considers two-level schedulers less applicable to IaaS VM placement (§7).

## Takeaways for practice

- Express policy as a strictly ordered list of validator and preference rules, with quantized scores. Operators can then reason about it and reorder it, and quantization keeps tie-breaking room for lower rules and randomness.
- Quantization also reduces conflicts. Unquantized scoring raised P99 conflicts from 11.6 to 18.0 per minute while improving packing density (Table 5). Deliberate ties spread concurrent agents across machines. (Own analysis on the mechanism; numbers from Table 5.)
- Cache by request equivalence class (the trait vector), not by request. Skewed VM-type demand and high reuse (Fig. 2, Table 2) make the hit ratio high.
- Drive cache maintenance from a revision-stamped change journal, so update cost tracks changed machines rather than fleet size. Do most of that work in idle time.
- Optimistic concurrency with fine-grained, resource-level validation at commit is enough at Azure's scale. Add randomized avoidance under load rather than locking.
- Prune first at a coarse level (clusters, then cells/racks) to keep the candidate set and sort costs bounded.

## References

- Paper: https://www.usenix.org/conference/osdi20/presentation/hadary
- PDF: https://www.usenix.org/system/files/osdi20-hadary.pdf
