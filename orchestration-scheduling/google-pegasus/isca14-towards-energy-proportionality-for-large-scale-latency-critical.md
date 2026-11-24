---
title: 'Towards Energy Proportionality for Large-Scale Latency-Critical Workloads'
authors:
- David Lo
- Liqun Cheng
- Rama Govindaraju
- Luiz André Barroso
- Christos Kozyrakis
affiliations: 'Stanford University, Google'
venue: 'ISCA'
year: 2014
abs_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/42523.pdf
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/42523.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Towards Energy Proportionality for Large-Scale Latency-Critical Workloads

> **Why it matters:** It shows, on a real Google search cluster, that driving CPU power limits from end-to-end request latency (not CPU utilization) cuts power for latency-critical services at low load without new SLO violations, and it exposes the hot-shard problem that makes one uniform cluster-wide knob leave savings on the table.

## Problem

On-line, data-intensive (OLDI) services such as web search must keep every server up: the index is sharded across all leaves, so consolidation would drop part of it, and moving tens of GB of state is too slow (Sec. 2.3). SLOs are milliseconds (search) or tens to hundreds of microseconds (memkeyval), and fan-out gives each server a steady request stream even at low load, so idle periods are too short for deep sleep or PowerNap-style batching (Sec. 2.3, 3.2). Energy proportionality in diurnal troughs is therefore poor.

Utilization-driven DVFS (Linux cpufreq) also fails: on search it caused SLO violations over a 24 h trace (Fig. 7), because latency at a given utilization differs across p-states (Fig. 8). P-states are also coarse (Sec. 3.3).

## Core design

### Iso-latency policy
- Fixed SLO targets sit near the knee of the latency/load curve, so at low and medium load the service "overachieves" on latency. Iso-latency spends that slack: run every server just fast enough that the SLO is barely met (Sec. 3.2, 4).
- Actuator: Intel RAPL (Running Average Power Limit), a per-socket average CPU power cap written through an MSR. RAPL enforces the cap mostly by voltage/frequency scaling, and can also modulate frequency to average between p-state frequencies. This gives a much finer power/performance knob than p-states (Sec. 4.1).
- Potential study: sweep the RAPL limit at each load and pick the lowest-power setting that meets the SLO, for mean and tail SLO metrics and for a relaxed target (latency at peak load) and an aggressive one (latency at the knee) (Sec. 4.1, Fig. 9–10).
- Core consolidation (fewer cores at max p-state, rest in c7) is less effective than RAPL, since fast cores' dynamic power outweighs the static power saved (Sec. 4.2, Fig. 11).

### PEGASUS controller (Sec. 5.1)
- Components: an **Application Performance Monitor** that reports latency headroom (it can piggyback on existing monitoring), a central **PEGASUS controller**, and a **local agent** on each server that writes the RAPL limit (Fig. 12).
- Control law: a multi-step **bang-bang controller** that outputs a Δ(power limit %) based on latency headroom. Thresholds and step sizes are workload-specific and set empirically.
- Policy is separated from enforcement. The policy (thresholds and steps) is workload-specific. Enforcement is workload-agnostic and applies one uniform power limit to all managed servers, which assumes a homogeneous cluster.
- The controller re-sends the limit at a fixed period even when it is unchanged. If agents lose contact with the controller, they fall back to maximum power, so a controller failure cannot hurt the SLO.
- The update period is set by how long a power change takes to show up in measured latency (query inertia, measurement delay).

### Search policy (Table 1, Sec. 5.2)
Rules are listed in priority order and only the first match applies. X = SLO-window latency (30 s moving mean), Y = instantaneous latency, T = target:
1. X > T: set max power and wait 5 minutes (emergency stop, since a violation means the load is too high).
2. Y > 1.35T: set max power.
3. Y > T: raise power by 7%.
4. 0.85T ≤ Y ≤ T: hold.
5. Y < 0.85T: lower power by 1%.
6. Y < 0.60T: lower power by 3%.

Power goes up fast and down in tiny steps, because large perturbations near the knee can raise latency by an order of magnitude. Instantaneous latency gives early warning and allows more frequent updates than the 30 s metric.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Baseline proportionality gap | 70% of peak power at 30% utilization | search cluster, diurnal trace | Sec. 2.3, Fig. 2 |
| CPU share of server power | 40% at idle, 66% at peak | cited from [8] | Sec. 3.2 |
| C-state wake-up latency | c1 ≈ 0, c3 10 µs, c7 100 µs | Sandy Bridge servers | Sec. 3.2 |
| cpufreq conservative band | keeps CPU utilization within 20%–95% | Linux cpufreq | Sec. 3.3 |
| p0 → p1 frequency drop | up to 700 MHz (TurboBoost off) | Xeon E5-2667v2 example | Sec. 3.3 |
| Range where only p0 meets SLO | 65%–85% utilization | search | Sec. 3.3, Fig. 8 |
| RAPL granularity / window / response | 0.125 W steps; 45 ms default averaging; takes effect in <1 ms | evaluated servers | Sec. 4.1 |
| Latency knee | 80% of peak (search), 60% of peak (memkeyval) | aggressive SLO target | Sec. 4.1 |
| Ideal iso-latency savings | 20%–40% power at 20%–80% utilization | both workloads, both SLO targets | Sec. 4.1, Fig. 9–10 |
| Iso-latency vs. ideal EP | below EP power above 50% utilization (relaxed); matches EP above 60% and beats Dynamic EP above 30% (aggressive) | sweep study | Sec. 4.1 |
| Controller size / cost | ~200 lines; one core; >90% of time sending packets; ~500 ms to reach all agents at thousands of servers | central controller | Sec. 5.1 |
| SLO definition for PEGASUS | latency at 90% of max load; controller target 95% of SLO | search, 30 s mean at root | Sec. 5.2 |
| Small-cluster savings | 30% power in trough; 11% total energy over 24 h; no new SLO violations | tens of servers, 24 h trace | Sec. 5.2.1, Fig. 13 |
| Production-cluster savings | 10%–20% power in low-utilization period; no added SLO violations | thousands of servers, 12 h trough | Sec. 5.2.2, Fig. 14 |
| Headline production saving | up to 20% | — | Abstract, Sec. 1 |
| Shard skew at peak | 50% of nodes below 85% CPU; 0.2% of nodes at 100% CPU | production leaves | Sec. 5.2.2 |
| Distributed PEGASUS (estimate) | up to 35% power savings | estimated from utilization distribution and diurnal curve, not run | Sec. 5.2.2, Fig. 15 |

Inconsistencies in the paper (not resolved here):
- **Distributed PEGASUS savings** are given three ways: "nearly double these savings" relative to up to 20% (Abstract), "nearly 40% power savings" (Sec. 1), and "up to 35%" (Sec. 5.2.2, Fig. 15).
- **Update period:** Sec. 5.2 says instantaneous latency let PEGASUS update "approximately once every 5 seconds". Sec. 5.2.2 says the delay between iterations had to grow "from 3 to 4 seconds" on the production cluster.
- **Conclusions (Sec. 7)** attribute "20% to 40% savings" to PEGASUS on the search cluster. That range matches the ideal iso-latency sweep (Sec. 4.1). The measured production result is 10%–20% (Sec. 5.2.2).

## Limitations

- **Uniform power limit.** Hot index shards bottleneck the fan-out tree, so every leaf runs as fast as the hottest; this is why production savings trail the small cluster (Sec. 5.2.2).
- **Distributed version only estimated** (Fig. 15), due to production scheduling constraints.
- **Hand-tuned bang-bang policy.** Thresholds and steps are empirical per workload and SLO window, with no derivation method or stability analysis (Sec. 5.1, 5.2).
- **Narrow evaluation.** Only search leaf nodes were managed; memkeyval appears only in the potential study (Sec. 5.2). At production scale only the 12 h trough was run (Sec. 5.2.2).
- **Idle power and co-location are out of scope.** Ideal EP beats iso-latency below 50% utilization because idle power dominates (Sec. 4.1, 6).
- (Own analysis) Memory- or I/O-bound services, where CPU power poorly predicts latency, may gain less; this is untested.

## Relation to other systems

- **Linux cpufreq / utilization DVFS** (Sec. 3.3): utilization as sole input, coarse p-states. PEGASUS uses end-to-end latency and fine-grained RAPL caps.
- **PowerNap [28], Meisner et al. ISCA'11 [29]:** PowerNap needs deep idle states and batching, unsuited to OLDI request rates. The paper follows [29]'s call for coordinated cluster-wide management, but through active-mode capping rather than idle modes (Sec. 6).
- **Ensemble budgeting [36], "No Power Struggles" [34]:** coordinate power across servers or controllers against a budget. PEGASUS is driven by the application latency SLO (Sec. 6).
- **Bubble-Up [27], Bubble-Flux [46], Paragon [14]:** fill slack with co-located batch work. PEGASUS removes slack by slowing servers; the combination is left open (Sec. 6).
- **Real-time DVFS [30, 6, 42, 26, 38]:** assume known jobs and deadlines on one node. PEGASUS needs neither and spans thousands of servers (Sec. 6).
- (Own analysis) Later work by some of the same authors (Heracles, ISCA 2015) reuses latency-headroom feedback, but to admit best-effort jobs rather than to cut power.

## Takeaways for practice

- Control on the SLO metric measured near the user, not on utilization (Fig. 8).
- Fine-grained actuators (continuous power caps) reach operating points that p-states or core parking miss.
- Make the controller asymmetric: raise power fast, lower it slowly, keep a hold band, and add an emergency stop on the true SLO metric.
- Fail safe: agents default to max performance when the controller goes silent.
- Set the control period by system response time; it had to grow at scale (Sec. 5.2.2).
- Uniform knobs break under shard skew. Push per-node latency goals down from a root controller.
- (Own analysis) The pattern maps to GPU inference fleets: latency-SLO feedback to per-device power or clock caps in traffic troughs, with per-replica goals under skew.

## References

- Paper: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/42523.pdf
- Code / blog: none official.
