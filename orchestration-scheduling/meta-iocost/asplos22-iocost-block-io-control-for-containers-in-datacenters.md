---
title: 'IOCost: Block IO Control for Containers in Datacenters'
authors:
- Tejun Heo
- Dan Schatzberg
- Andrew Newell
- Song Liu
- Saravanan Dhakshinamurthy
- Iyswarya Narayanan
- Josef Bacik
- Chris Mason
affiliations: 'Meta, Carnegie Mellon University'
venue: 'ASPLOS'
year: 2022
doi: 10.1145/3503222.3507727
abs_url: https://doi.org/10.1145/3503222.3507727
pdf_url: http://www.cs.cmu.edu/~dskarlat/publications/iocost_asplos22.pdf
code_url: https://github.com/facebookexperimental/resctl-demo
note_type: deep-read
written_at: '2026-11-25'
---

# IOCost: Block IO Control for Containers in Datacenters

> **Why it matters:** IOCost shows that proportional, work-conserving block IO isolation for containers on heterogeneous SSD fleets works when you schedule on modeled device *occupancy* (time) rather than IOPS, bytes or latency, and when swap/reclaim IO is charged to the cgroup that caused it.

Author list above is truncated to 8; the paper also lists Chunqiang Tang (Meta) and Dimitrios Skarlatos (CMU).

## Problem

Meta stacks many containers per host (cgroup hierarchy in Fig. 1) on a fleet "comprised of millions of machines" (Abstract). Existing Linux block IO controls each miss part of what is needed (Table 1):

- **kyber / mq-deadline**: low overhead and work-conserving, but no cgroup control, no proportional fairness, no memory-management awareness.
- **blk-throttle**: per-cgroup absolute limits; not work-conserving; overhead marked partial.
- **BFQ**: proportional and cgroup-aware, but high overhead on fast SSDs.
- **IOLatency** (Meta's previous upstreamed controller): per-cgroup latency targets; memory-aware but only partly work-conserving, and it cannot do proportional sharing between equal-priority workloads.

Four requirements (§1–2): (1) hardware heterogeneity — eight main SSD types with very different IOPS/latency profiles plus a long tail (Fig. 3); (2) workload diversity in read/write and random/sequential mix (Fig. 4); (3) work conservation, fairness among equal priorities, and configuration that does not need per-app IOPS numbers; (4) reclaim, swap and journaling IO that causes priority inversions if charged or throttled naively.

## Core design

### Split control: issue path vs planning path (§3.1, Fig. 5)

- **Issue path** (per bio, microsecond scale). Cost model gives the bio's *absolute cost* in time units ("an occupancy metric, not latency"). Dividing by the cgroup's **hweight** (hierarchical weight = compounded share of the device down the cgroup tree) gives the *relative cost*. Each cgroup has a **local vtime** advanced by relative cost; a **global vtime** advances with wall-clock time scaled by **vrate**. A cgroup's budget is how far global vtime is ahead of its local vtime; the bio is issued if budget covers the cost, otherwise it waits.
- hweight is cached and recomputed only when a weight-tree **generation number** changes. A cgroup is active while issuing IO and dropped from hweight computation after a full planning period idle.
- **Planning path** (periodic, millisecond scale; period derived from a multiple of the latency targets, no fixed value given). Collects per-cgroup usage and completion latencies, adjusts vrate, runs budget donation, updates weights.

### Device cost model (§3.2)

- Built offline per device. Native model is linear: `cost = base_cost + size_cost_rate × bio_size` (Eq. 1), with features read/write, random/sequential (relative to the cgroup's previous IO), and size. Six parameters: four base costs and two size rates. Arbitrary eBPF models are allowed.
- Operators configure it as `rbps, rseqiops, rrandiops, wbps, wseqiops, wrandiops`, converted via Eq. 2–3. Parameters come from saturating fio runs (e.g. max-rate 4 KB random reads for random-read base cost). Fig. 6 gives a sample configuration.

### QoS and dynamic vrate (§3.3–3.4)

- The linear model ignores SSD caching, reordering and GC; vrate corrects for this online. If IO is budget-deficient and the device is not saturated, vrate goes up; if saturated, it goes down. Saturation is detected by request depletion (in-flight requests filling device slots) or by latency-target violation (e.g. a p90 read-completion target, §3.3).
- QoS parameters (latency targets, vrate range) are tuned per device with **ResourceControlBench**, a synthetic latency-sensitive service, run alone with a growing working set and next to a memory leaker.

### Priority inversion: debt (§3.5)

- Swap-out IO is charged to the cgroup that owns the memory, issued immediately, and recorded as **debt**; future bios of that cgroup are throttled until debt is repaid from budget.
- To stop a cgroup living on "free" debt-only IO, a check before return to userspace briefly blocks the thread if debt exceeds a threshold (value not given). Filesystem journaling uses the same path.

### Budget donation (§3.6, Fig. 7–8)

- Instead of raising vrate, the planner lowers the local weights of cgroups using less than their hweight so their compounded hweight equals the post-donation value. Updates touch only nodes on donor-to-root paths (closed-form updates for h′, s′, w′ from invariants Eq. 4–5); others recompute hweight lazily on the issue path.
- **Rescinding** is local: a donor that needs budget back resets its weight up its path and bumps the generation number, no global operation; partial rescind is possible.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Production deployment | 2 years, Meta fleet | "millions of machines" | Abstract, §5 |
| Storage device types modeled | roughly thirty | Meta datacenters | §3.2 |
| Fleet share per SSD type | usually <14%; device F 19%; ~20% of capacity over 18 other devices | 8 SSD types A–H | §2.3, Fig. 3 |
| Sample read model | 2.05 ns/B size rate; 104 us seq base; 109 us rand base | Fig. 6 config | §3.2 |
| Overhead | IOCost "no noticeable overhead"; bfq "severe software overheads"; no per-mechanism IOPS figures in text | 750K-IOPS SSD, fio 4 KB random reads | §4.1, Fig. 9 |
| Proportional control | IOCost matches 2:1 target; BFQ >10:1; IOLatency best config ~10:1 | random 4 KB reads, p50 < 200 us gating | §4.2, Fig. 10 |
| Work conservation latency | high-priority workload avg 250 us, stdev nearly 1 ms; others <200 us avg, stdev ~200 us | 100 us think time | §4.2, Fig. 11 |
| Spinning disk | IOCost holds 2:1 in all random/sequential mixes; BFQ only when both sequential | 4 KB reads | §4.3, Fig. 12 |
| vrate adaptation | vrate ~100 initially; after model halved, vrate ~doubles; after spike, vrate drops to ~half | p90 read target 250 us | §4.4, Fig. 13 |
| Memory leak isolation | web server ≥80% of normal RPS with IOCost; BFQ near-total loss | prod web servers, leaker in system slice | §4.5, Fig. 14 |
| Ramp-up 40%→80% load | ~half BFQ's time unstressed; ~5x faster than BFQ under stress | ResourceControlBench, p95 < 75 ms | §4.5, Fig. 15 |
| ZooKeeper 1 s SLO violations over 6 h | blk-throttle 78; BFQ 13 (2–5 s each); IOLatency 31 (max 7.8 s); IOCost 2 (1.5 s, 1.04 s) | 12 ensembles × 5 on 5 machines, one noisy 300 KB ensemble | §4.6, Fig. 16 |
| Package fetch failures | roughly 10x fewer | region of hundreds of thousands of servers, IOLatency→IOCost over 2 months | §4.8, Fig. 18 |
| Container cleanup failures (>5 s) | 3x reduction | same migration | §4.8, Fig. 19 |
| Experimental platform | single-socket, 64 GB, one of three SSDs; Linux 5.6 + IOCost patches from 5.15 | all §4 experiments | §4 |


## Limitations

- No dedicated limitations section; the conclusion only alludes to "potential future hardware directions".
- The linear six-parameter model is coarse; correctness relies on online vrate correction and on offline per-device profiling (fio + ResourceControlBench) for every device type.
- QoS tuning explicitly sacrifices device utilization for consistent latency (§3.4); throughput-maximizing operators may want a different trade-off.
- Planning-period length and the debt threshold are not specified, so reproducing behavior from the paper alone is hard.
- Remote storage is covered only by the Fig. 17 cloud-disk repeat (AWS EBS gp3/io2, GCP PD balanced/SSD), reported qualitatively.
- (Own analysis) IOCost controls one host's block layer; it does not arbitrate shared remote-storage backends across hosts, and it assumes weights are a sufficient interface (no absolute IOPS guarantees).

## Relation to other systems

- **blk-throttle**: absolute per-cgroup limits, not work-conserving; Meta found per-application limits "inefficient, brittle and ultimately intractable" (§5). IOCost uses relative weights over modeled occupancy.
- **BFQ**: also proportional and cgroup-aware, but its software overhead is severe on fast SSDs (§4.1) and it does not account memory-management IO (Fig. 14). IOCost moves expensive work to the planning path.
- **IOLatency**: Meta's predecessor; latency targets depend on both device and application and cannot arbitrate equal-priority tenants (§5). IOCost keeps IOLatency's memory awareness but replaces targets with weights.
- **mClock / PARDA**: VM-level IO fairness on networked storage by measuring and controlling IOPS/latency; IOCost models occupancy and handles memory-subsystem IO (§6).
- **WDT**: cgroup-aware weighted scheduler for fast SSDs that distributes bandwidth; IOCost distributes occupancy (§6).
- **FlashBlox**: hardware isolation via SSD channel partitioning at the cost of tenant flexibility; IOCost is software-only and work-conserving (§6).

## Takeaways for practice

- Schedule shared devices on a modeled *time/occupancy* cost per request, not on IOPS or bytes; it makes one weight meaningful across random vs sequential and small vs large IO.
- Split per-request fast path (budget check against a virtual clock) from a periodic planner (rate correction, donation). The same pattern applies to GPU or NIC sharing where per-op cost must be cheap.
- Treat the offline cost model as a prior and close the loop with a global rate multiplier driven by device saturation signals; this tolerates model error (Fig. 13).
- Charge reclaim/swap IO to the cgroup owning the memory and let it run into debt instead of throttling the victim; memory and IO isolation must be designed together (§3.5, §5).
- Make work conservation cheap to undo (local donation, lazy recompute, local rescind), and expose only weights to application owners; device profiling and QoS tuning stay a fleet-level operator job.

## References

- Paper: https://doi.org/10.1145/3503222.3507727 (author-hosted PDF: http://www.cs.cmu.edu/~dskarlat/publications/iocost_asplos22.pdf)
- Code / blog: https://github.com/facebookexperimental/resctl-demo (named in the paper's footnote for the device-profiling and benchmarking tools); IOCost itself is upstreamed in the Linux kernel and the modeling tools are "in the Linux source tree" (§1, §3.2; the paper gives no URL)
