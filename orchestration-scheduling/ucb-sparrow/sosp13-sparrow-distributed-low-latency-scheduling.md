---
title: 'Sparrow: Distributed, Low Latency Scheduling'
authors:
- Kay Ousterhout
- Patrick Wendell
- Matei Zaharia
- Ion Stoica
affiliations: 'University of California, Berkeley'
venue: 'SOSP'
year: 2013
paper_id: 4cb31c5150c4f12768e946c43849ff9d34f25440
doi: 10.1145/2517349.2522716
abs_url: https://dl.acm.org/doi/10.1145/2517349.2522716
pdf_url: https://people.eecs.berkeley.edu/~matei/papers/2013/sosp_sparrow.pdf
code_url: https://github.com/radlab/sparrow
note_type: deep-read
written_at: '2026-11-25'
---

# Sparrow: Distributed, Low Latency Scheduling

> **Why it matters:** Sparrow showed that many stateless schedulers that each probe a few random workers, combined with batch sampling and late binding, can place sub-second parallel tasks within about 12% of an ideal scheduler's median response time.
## Problem

Analytics frameworks are moving toward shorter tasks and wider fan-out. Figure 1 traces the trend from 2004 MapReduce batch jobs to Dremel, in-memory Spark and Impala queries, aiming at about 100 ms latency. A cluster of 10,000 16-core machines running 100 ms tasks may need more than 1 million scheduling decisions per second (§1). That exceeds what a centralized scheduler handles, and a single scheduler is also a point of failure. The goals (§2) are millisecond-scale delay, millions of decisions per second and tolerance of scheduler failure. Long-running executors are assumed on each worker, so only short task descriptions travel. Sparrow deliberately drops bin packing, gang scheduling and inter-job constraints (§2, §8).

## Core design

**Per-task sampling and why it fails (§3.1–3.2).** Workers run tasks in fixed slots, and a job finishes with its slowest task. The baseline applies power-of-two-choices per task: probe d = 2 random workers and use the shorter queue. A job of m tasks then waits for the unluckiest of m independent samples. In the Figure 3 simulation (10,000 4-core machines, 1 ms RTT, 100-task jobs, exponential 100 ms tasks), per-task sampling at 80% load is more than 3× better than random placement but still more than 2.6× worse than an omniscient scheduler.

**Batch sampling (§3.3).** A job with m tasks probes d·m workers in one batch and places its m tasks on the m least-loaded of them. Probe information is pooled across the job's tasks. At 80% load this gives 0.73× the response time of per-task sampling, but it is still 1.92× worse than omniscient (§3.3, Fig. 3).

**Why queue length is not enough (§3.4).** Queue length predicts wait time poorly (two 50 ms tasks vs one 300 ms task), and concurrent schedulers can all pile onto the same idle worker.

**Late binding (§3.5).** Probes do not return a queue length. Instead, a worker's node monitor enqueues a *reservation* (`enqueueReservation()`). When the reservation reaches the head of the queue, the worker calls back the scheduler (`getTask()`). The scheduler hands real tasks to the first m workers that call back and sends no-ops to the other (d−1)·m. Binding waits until a slot is free, which removes both the estimation problem and the race. The cost is one idle round trip per callback: the idle fraction is (d·RTT)/(t + d·RTT), at most 2% for 100 ms tasks, d ≤ 2 and the 1 ms EC2 RTT. At 80% load late binding gives 0.55× the response time of batch sampling and comes within 5% (4 ms) of omniscient (§3.5, Fig. 3).

**Proactive cancellation (§3.6).** Once all m tasks are launched, the scheduler can cancel outstanding reservations. This trims median response time by 6% at 95% load for about 2% extra RPCs. It matters more as the ratio of network delay to task duration grows.

**Placement constraints (§4.1).** Per-job constraints restrict the d·m candidates to eligible workers, after which batch sampling proceeds unchanged. Per-task constraints (for example, data locality with 3 HDFS replicas) fall back to per-task sampling with late binding: two probes into each task's allowed set. A small optimization lets a worker probed for one task run another task it is eligible for.

**Resource sharing across schedulers (§4.2).** There is no global state, so policy is enforced locally at each worker. *Strict priorities* use one queue per priority, and the worker always serves the highest non-empty queue. *Weighted fair sharing* uses one queue per user with weighted fair queuing, which yields cluster-wide weighted shares in expectation. Running tasks are never preempted.

**Implementation (§6).** Stateless schedulers expose a Thrift `submitRequest()` service, and a per-worker node monitor calls `launchTask()` on executors. A 280-line Scala Spark plugin submits each stage as a Sparrow job. Clients heartbeat every 100 ms and fail over to the next scheduler, and Spark relaunches in-flight stages, so tasks must be idempotent (§6.3).

## Analytical results (§5)

The model (Table 1) assumes zero network delay, infinitely many servers and one task per server, with ρ the load. Per-task sampling places all m tasks on idle machines with probability (1−ρ^d)^m, which decays exponentially in m. For 100-task jobs it is below 2% already at 20% load (Fig. 4). Table 2 gives the corresponding expression for batch sampling; it is not reproduced here because the extracted formula was garbled. With c cores per machine, ρ is replaced by ρ^c. With 4 cores and 100-task jobs, 99.9% of jobs see zero wait at up to 79% load (Fig. 5).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Per-task sampling vs omniscient | >2.6× worse | Sim., 80% load, 100-task jobs | §3.2, Fig. 3 |
| Batch vs per-task sampling | 0.73× response time | Sim., 80% load | §3.3, Fig. 3 |
| Late binding vs batch sampling | 0.55× response time; within 5% (4 ms) of omniscient | Sim., 80% load | §3.5, Fig. 3 |
| Proactive cancellation | −6% median; +2% RPCs | 95% load | §3.6 |
| Zero-wait probability, batch sampling | 99.9% of jobs up to 79% load | Model, 4 cores, 100 tasks/job | §5, Fig. 5 |
| TPC-H/Shark vs ideal | median within 12% | 110 EC2 VMs (100 workers, 10 schedulers), 80% load | Abstract, §7.1, Fig. 8 |
| TPC-H vs random placement | 4–8× lower median; >10× lower p95 | same | §7.1, Fig. 8 |
| Late binding gain on TPC-H | 14% average median reduction over batch sampling | same | §7.1 |
| Median scheduling delay | 7 ms unconstrained; 14 ms constrained | TPC-H | §7.3, Fig. 10 |
| Scheduler failover | <120 ms (≈100 ms detect, <5 ms reconnect, <15 ms relaunch) | 10 frontends, 100 nodes | §7.4, Fig. 11 |
| Spark native scheduler limit | ~1,500 tasks/s; cannot keep up below 1,355 ms tasks | 10-task jobs, 80% load | §7, Fig. 12 |
| High-priority isolation | median ~106 ms → ~141 ms | low-priority load raises total load to 1.75 | §7.8, Table 3 |
| Probe ratio 1.1 vs 1.0 | >2.5× lower median | 90% load | §7.9, Fig. 14 |
| Short jobs with 50% long tasks | within 11% of ideal | 16-core machines | §7.10, Fig. 15 |

TPC-H setup (§7.1): ten users, 2 GB per-user data in 33 triply replicated in-memory partitions, 4 slots per 8-core worker. Against per-task sampling, the median is about 0.8× and p95 almost 2× lower.

## Limitations

- Policies are approximate. Fair share and priorities hold only in expectation, and without preemption high-priority tasks can wait behind running low-priority ones (§4.2, §7.8, §8).
- No gang scheduling, bin packing or inter-job constraints. Gang jobs could deadlock (§8).
- Worker failures are not handled, in-flight jobs of a failed scheduler are not recovered, and there is no protection against rogue schedulers (§6.3, §8).
- Probe ratio is static (d = 2). Load-adaptive probing is left as future work (§8, §7.9).
- Heterogeneous durations hurt more on low-core machines (§7.10), and 10,000-node results are simulation only (§7.11).
- Scheduling is per stage, not per query (§8).

## Relation to other systems

- **Mesos (NSDI 2011):** Two-level resource offers: Mesos decides what to offer each framework, and frameworks pick tasks (abstract). Sparrow's §9 calls Mesos, YARN and Omega coarse-grained allocators too slow for sub-second tasks. Sparrow works at the per-task layer beneath them.
- **Omega (EuroSys 2013):** Parallel schedulers over *shared* cluster state with lock-free optimistic concurrency (abstract). Sparrow shares no state: conflicts are avoided by late binding at workers, not detected and retried at commit.
- **Apollo (OSDI 2014):** Also distributed, but decisions use loosely shared global cluster information and future resource availability (abstract), trading Sparrow's state-free design for better-informed placement.
- **Borg (EuroSys 2015):** A centralized cluster manager that gets high utilization from admission control, task packing, over-commitment and failure-aware placement (abstract). These are exactly the features Sparrow drops (§2) in exchange for latency and throughput.
- **Hawk (USENIX ATC 2015):** Hybrid design. Long jobs go through a centralized scheduler, short jobs use Sparrow-style distributed scheduling, a small partition is reserved for short jobs, and randomized work stealing repairs bad placements. On a Google trace at high load it reports 80%/90% better p50/p90 short-job runtimes than Sparrow (abstract).
- **Eagle (SoCC 2016):** Extends the hybrid line with succinct state sharing of long-job locations, sticky batch probing (a probe stays on a node until its job's tasks finish) and distributed SRPT ordering with starvation avoidance (abstract).

## Takeaways for practice

- For fan-out jobs, sample per job, not per task: pooling d·m probes removes most of the slowest-task penalty.
- Late binding (reserve, then pull work when a slot frees) replaces load estimation and avoids scheduler races for one RTT per task. That is cheap when task time is much larger than RTT.
- A probe ratio just above 1 captures much of the gain, and heavy oversampling only adds messages (Fig. 14).
- Without global state, per-worker multi-queues give approximate priorities and fair shares. Add preemption if isolation matters.
- Pair distributed sampling with a centralized path for long or gang jobs (Hawk, Eagle), as GPU training jobs need gang placement.
- Stateless schedulers plus heartbeating clients and idempotent relaunch gave sub-120 ms failover.

## References

- Paper: https://people.eecs.berkeley.edu/~matei/papers/2013/sosp_sparrow.pdf (DOI 10.1145/2517349.2522716)
- Code: https://github.com/radlab/sparrow (Apache-2.0, archived)
