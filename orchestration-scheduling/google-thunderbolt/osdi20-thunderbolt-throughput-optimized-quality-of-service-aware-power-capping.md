---
title: 'Thunderbolt: Throughput-Optimized, Quality-of-Service-Aware Power Capping at Scale'
authors:
- Shaohong Li
- Xi Wang
- Xiao Zhang
- Vasileios Kontorinis
- Sreekumar Kodakara
- David Lo
- Parthasarathy Ranganathan
affiliations: 'Google'
venue: 'OSDI'
year: 2020
abs_url: https://www.usenix.org/conference/osdi20/presentation/li-shaohong
pdf_url: https://www.usenix.org/system/files/osdi20-li_shaohong.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Thunderbolt: Throughput-Optimized, Quality-of-Service-Aware Power Capping at Scale

> **Why it matters:** It shows that power capping for an oversubscribed facility can be built from plain Linux CFS bandwidth control, applied per task. That lets you throttle batch work on mixed-priority machines without killing it and without touching serving latency, and it works on any hardware.

## Problem

Power oversubscription means installing more servers than a power domain can nominally feed at full load (§1). It only pays off if something sheds load during rare peaks. Exceeding the protected limit trips breakers and drops power to thousands of machines, so power safety outranks both latency and throughput (§2).

Google's fleet adds two complications:
- **Mixed-priority machines.** Latency-sensitive serving tasks (ms-to-s deadlines, high priority) share machines with throughput-oriented tasks such as log processing, indexing and ML training (hour-scale deadlines, low priority) (§1). Machine-level priority schemes such as Dynamo and CapMaestro do not fit (§2, §9).
- **Stopping batch work is expensive.** The predecessor MVPP capper used SIGSTOP/SIGKILL. That wastes work through checkpoint and restart, and in synchronous training a stopped worker becomes a straggler (§2).

The goal is a hardware-agnostic capper that sheds power within seconds by slowing only batch tasks. It must also stay safe without telemetry, since meters plus the facility network are only about 99.9% available (§4.2).

## Core design

### Architecture (§4, Fig. 1)
- **One instance per protected power domain.** It reads meters at electrical choke points (PDUs or medium-voltage power planes) instead of summing per-node estimates.
- **Components:** a meter watcher polls at 1 Hz and writes a history datastore. A power notifier runs the control logic and asks a risk assessor when readings are missing. A machine manager fans out RPCs to the node controller on every machine. A topology datastore holds limits and domain membership.
- **Replication:** four replicas, two leaders and two followers. Only leaders read meters and send RPCs. RPCs are idempotent, so duplicates from both leaders are harmless.

### Mechanism 1: CPU bandwidth control (primary, reactive) (§4.1.1)
- Each task runs in its own cgroup. The node controller rewrites the CFS quota and period of **batch cgroups only**, based on each task's recent usage. Serving tasks and kernel threads are exempt.
- **Why this knob:** it is per-task, vendor-neutral and already in upstream Linux. Its 1 ms response is slower than the 100 µs of DVFS and RAPL, but those need hardware support and act on a core or socket (Table 1). RAPL is Intel-only, and per-task DVFS was not upstream.
- **Cost:** it is less power-efficient than DVFS, which keeps more throughput at equal power below about 0.85 normalized power (Fig. 4). Long throttles drive tasks to the 0.01 minimum share, where they can stall or fail health checks (§8). Exempt tasks can be hit indirectly, for example a high-priority controller whose batch workers were throttled (§6.1, Fig. 6).
- **Benefit:** a wider dynamic range than DVFS, close to 60% versus about 40% (Fig. 4). Throttling is rare, so efficiency matters less (§5).

### Control policy: load shaping (§4.1.2)
- **Power model (Eq. 1):** p(t) = Σ fᵢ(cᵢ + uᵢ) + n. Here c is controllable (batch) CPU, u is exempt and kernel CPU, and n is non-machine load.
- **Throttle step:** while p is over threshold, each batch cap becomes `m × previous usage`. It is refreshed every second, so caps shrink geometrically.
- **Safety condition (Eq. 3):** non-sheddable power, Σ fᵢ(uᵢ) + n, must stay below the limit. Operators size oversubscription to keep it there, with global load balancing of serving traffic as a last resort.
- **Two thresholds (Table 2):** the high threshold is 98% of the limit with a hard multiplier of 0.01. It rests on the observation that a nearly full cluster rises by no more than 2% of the limit within 5 s. The low threshold is 96% with a soft multiplier of 0.75. It is armed only after throttling starts and expires after 5 minutes of inactivity.
- **Unthrottling:** a random, non-overlapping subset of machines is released each second, for example 20% per second. Each throttle RPC carries a random 1–20 s timeout. If the leaders go silent, for instance during a partition, machines unthrottle on their own with no "stop" RPC needed.
- **Timing:** typically 1–2 s end to end, against a 5 s design budget.

### Mechanism 2: CPU jailing (failover, proactive) (§4.2)
- **What it does:** removes a fraction J of logical CPUs from the affinity of **all** tasks, serving tasks included. That caps machine utilization at 1−J until a renewable timeout restores the CPUs. A batch-only version would have to stop batch work entirely to be safe without readings.
- **Sizing (Eq. 4):** J = 1 − g(1/(1+r)), where r is the oversubscription ratio and g maps power to CPU utilization. Production uses 20–50%.
- **Trigger:** a deliberately conservative risk model of overload during a telemetry gap.
- **Cost:** serving tasks lose cores and rely on preempting batch work. At J=20%, p99 storage latency rose from 79 to 86 ms (Table 6). The authors saw latency about an order of magnitude higher at 80% jailing (§6.3). Jailing mostly bites on already-hot machines (Table 5).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Oversubscription enabled | 9%–25% | Production clusters, by power architecture | Abstract, §7 |
| End-to-end response | 1–2 s typical, 5 s budget | Both paths | §4.1.2, §4.2.2 |
| Thresholds and multipliers | 98% with 0.01; 96% with 0.75 | Production | Table 2 |
| CPU power floor: bandwidth ctl / DVFS / RAPL | 0.34 / 0.57 / 0.22 | Power virus, Skylake | §5, Fig. 3 |
| CPU cut per 0.02 power shed | ~0.1 utilization | Cluster | §6.1 |
| Serving p99 read latency, baseline / 0.75 soft | 79 / 80 ms | Exempt storage service | Table 3 |
| Exempt vs shaped CPU drop | ~0.03 vs ~0.1 | Multiplier 0.1 | §6.1, Fig. 6 |
| Power shed at 4 s: 0.01 mult. or SIGSTOP / 0.95 mult. | ~3% / 0.5% | Pushed-to-limit test | §6.2, Fig. 7 |
| Failure fraction: baseline / 0.01 / SIGSTOP | 0.0007 / 0.003 / 0.06 | Pushed-to-limit test | Table 4 |
| Jailing at J=20%: power | 0.72 → 0.70 in 5 s | Cluster | §6.3, Fig. 9 |
| Jailing: p99 machine CPU | 0.94 → 0.75 | Cluster | Table 5 |
| Production activations | 3 reactive, 2 proactive | First 130 days of 2020 | §7 |

## Limitations
- **Serving work is fully exempt.** Clusters where serving dominates power would need priority buckets (§8). Eq. 3 is an operator-maintained assumption.
- **CPU is the only actuator.** That makes it weak when accelerators dominate power (§8), which is the key gap for GPU and TPU fleets.
- **Jailing is blunt.** It hurts serving tasks, and its conservative J limits oversubscription in latency-heavy clusters (§8).
- **Purely reactive.** Power-aware scheduling and admission control are left as future work (§8, §9).
- **Thin production evidence.** There are a few activations, and the savings claim ("millions of dollars", §10) comes without a figure.

## Relation to other systems

*Apart from Dynamo, which the paper itself compares in §9, these comparisons are this note's own analysis. Each draws on that system's public abstract or paper.*

- **Borg (EuroSys 2015).** Borg gets high utilization from over-commitment and process-level isolation on shared machines (abstract). Mixing priorities that way is what forces a per-task capper. Thunderbolt runs beside the cluster scheduler (cited as [22]) and never changes placement or admission.
- **Heracles (ISCA 2015).** Heracles is a feedback controller that keeps latency-critical services within SLO while best-effort tasks use leftover CPU, memory and network (90% average utilization, per its abstract). Both protect serving work by throttling best-effort work, but they guard different limits. Heracles controls a per-server latency SLO with several knobs. Thunderbolt controls a domain-wide power limit with one CPU knob and never reads latency. Thunderbolt does not cite it.
- **Dynamo (Facebook, ISCA 2016).** Dynamo caps oversubscribed power hierarchies:
  - Per-server agents set RAPL limits.
  - Leaf controllers pull power every 3 s and upper controllers every 9 s.
  - It caps low-priority service groups first.
  - It reports 18 prevented outages and 8% more usable capacity.

  It differs from Thunderbolt in its actuator (RAPL versus cgroup bandwidth), its multi-level hierarchy (versus one choke-point meter) and its machine-level rather than task-level granularity (§9).
- **CPI² (EuroSys 2013).** CPI² detects interference from hardware-counter CPI, identifies antagonists and optionally throttles them. It is the same Google lineage and shares an author (Xiao Zhang), and it also caps low-priority CPU to protect victims. CPI² triggers on a per-task performance anomaly, while Thunderbolt triggers on an aggregate facility signal and throttles every batch task in the domain.
- **DynamoLLM (arXiv 2408.00741).** DynamoLLM reconfigures LLM inference clusters across instance count, model parallelism and GPU frequency to cut energy while meeting SLOs. Its abstract reports 53% energy savings. It is energy optimization for GPU serving rather than breaker safety for CPU fleets, and it covers the accelerator-dominated case that Thunderbolt's §8 says it handles poorly.

## Takeaways for practice
- **Mixed priorities need task-level caps.** When priorities share a machine, cap at the cgroup level. CFS quota is a portable, upstream actuator for that.
- **Throttle rather than kill.** Throttling batch work gives an order of magnitude fewer task failures than SIGSTOP at similar shedding speed (Table 4) and avoids stragglers.
- **Use two thresholds with a hard and a soft multiplier.** They trade response speed against oscillation.
- **Make throttle commands leases.** Randomized, lease-based unthrottling survives controller partitions and lets you run active-active leaders.
- **Keep an open-loop fallback.** Size it from the oversubscription ratio and expect it to be costly for serving tasks.
- **Budget from non-sheddable power.** Size oversubscription from serving, idle and cooling power, not from the total.
- **GPU fleets need more than a CPU knob.** You need GPU frequency or power limits, or instance reconfiguration.

## References
- Paper: https://www.usenix.org/conference/osdi20/presentation/li-shaohong (PDF: https://www.usenix.org/system/files/osdi20-li_shaohong.pdf)
- Google Research page: https://research.google/pubs/thunderbolt-throughput-optimized-quality-of-service-aware-power-capping-at-scale/
- Related: Borg https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ ; Heracles https://research.google/pubs/heracles-improving-resource-efficiency-at-scale/ ; Dynamo https://research.facebook.com/publications/dynamo-facebooks-data-center-wide-power-management-system/ ; CPI² https://research.google/pubs/cpi2-cpu-performance-isolation-for-shared-compute-clusters/ ; DynamoLLM https://arxiv.org/abs/2408.00741
