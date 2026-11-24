---
title: 'Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider'
authors:
- Mohammad Shahrad
- Rodrigo Fonseca
- Íñigo Goiri
- Gohar Chaudhry
- Paul Batum
- Jason Cooke
- Eduardo Laureano
- Colby Tresness
affiliations: 'Microsoft Azure, Microsoft Research, Princeton University'
venue: 'USENIX ATC'
year: 2020
arxiv_id: '2003.03423'
abs_url: https://www.usenix.org/conference/atc20/presentation/shahrad
pdf_url: https://www.usenix.org/system/files/atc20-shahrad.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider

> **Why it matters:** It characterizes the entire production workload of a major FaaS platform (Azure Functions) from the provider side, and shows that a small per-application idle-time histogram beats fixed keep-alive on both cold starts and memory.

## Problem

In FaaS the provider decides when to load an application's image and how long to keep it; warm images avoid cold starts but waste memory for rarely invoked applications. At the time, major providers used a fixed keep-alive after each execution: the paper cites about 10 minutes for AWS Lambda and 20 minutes for Azure Functions (§1), and OpenWhisk's default is also a fixed timeout (§2). A fixed window ignores how much workloads differ, and prior studies measured providers only from the outside with benchmarks (§7).

The paper characterizes all Azure Functions invocations from July 15–28, 2019 (§3), then designs a keep-alive and pre-warming policy from those findings, evaluates it in simulation and Apache OpenWhisk, and describes its Azure implementation (§4–§6). The **application**, not the function, is the unit of scheduling and resource allocation (§2).

## Core design

### Workload characterization (§3)
- **Data** (§3.1): per-function invocation counts in 1-minute bins, per-worker execution-time aggregates per 30 s, and memory sampled every 5 s. Sub-minute interarrival times cannot be reconstructed; execution-time percentiles are weighted estimates.
- **Findings that drive the design** (§3.6): most applications are invoked rarely, rates span over 8 orders of magnitude, many have highly variable interarrival times, and execution times are mostly seconds, on the same order as cold-start time.

### Two windows instead of one (§4.1)
- **Pre-warming window:** wait after the last execution before reloading the image; 0 means "do not unload."
- **Keep-alive window:** how long the image stays loaded after pre-warming (or after the execution, if pre-warming is 0). Both are recomputed after every invocation.

### Hybrid histogram policy (§4.2)
- **Range-limited idle-time histogram** per application. It uses 1-minute bins over a configurable range; the evaluated default is 4 hours. Idle times beyond the range are counted as out of bounds (OOB).
  - Head = 5th percentile, which sets the pre-warming window (rounded down to the bin).
  - Tail = 99th percentile, which sets the keep-alive window (rounded up).
  - A default 10% margin shortens the pre-warming window and lengthens the keep-alive window.
- **Representativeness check:** the policy computes the coefficient of variation (CV) of the bin counts online with Welford's algorithm. Below a threshold (default CV=2, §5.2) the histogram is unrepresentative (too few samples or a changed pattern) and the policy falls back to pre-warming 0 and keep-alive equal to the histogram range.
- **Time-series fallback:** applications with many OOB idle times use ARIMA (orders chosen by `auto_arima` from pmdarima) to predict the next idle time, with a 15% margin. The model is updated on every invocation. The paper's example: a predicted 5-hour idle time yields a 4.25-hour pre-warming window and a 1.5-hour keep-alive window (§4.2).

### OpenWhisk implementation (§4.3)
- The controller's Load Balancer keeps histograms and computes windows; a keep-alive field in `ActivationMessage` tells the Invoker's `ContainerProxy` when to unload, replacing the fixed 10-minute timeout.

### Azure Functions implementation (§6)
- HTTP-triggered applications only; workers send asynchronous updates to the controller, which builds the histograms.
- Each histogram is kept in memory as 240 integers (960 bytes), backed up to the database every hour. A new histogram starts each day, and histograms older than 2 weeks are dropped.
- When an application goes idle, a pre-warm event is scheduled for the predicted time minus 90 seconds. Pre-warming loads dependencies and does JIT where it applies; the function code itself is compiled at the real invocation.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Trace period | July 15–28, 2019 | All Azure Functions invocations | §3.1 |
| Apps with a single function | 54% | Trace | §3.2, Fig. 1 |
| Event triggers: functions vs invocations | 2.2% vs 24.7% | Trace | §3.2, Fig. 2 |
| Queue triggers: functions vs invocations | 15.2% vs 33.5% | Trace | §3.2 |
| Timer triggers: functions vs invocations | 15.6% vs 2% | Trace | §3.2 |
| Spread of invocation rates | >8 orders of magnitude | Invocations per day, functions and apps | §3.3, Fig. 5(a) |
| Apps invoked ≤1/minute on average | 81% | Trace | §3.3, Fig. 5(a) |
| Share of invocations from the 18.6% most popular apps | 99.6% | Trace | §3.3, Fig. 5(b) |
| Apps with IAT CV > 1 | 40% | Trace | §3.6 |
| Functions with average execution time < 1 s | 50% | Weighted estimate | §3.4, Fig. 7 |
| Apps never above 400 MB / apps at most 170 MB | 90% / 50% | Allocated memory | §3.5, Fig. 8 |
| 75th-percentile app cold-start rate | 50.3% (10-min fixed), 25% (1-h fixed) | Simulation, first trace week | §5.2, Fig. 14 |
| Fixed 2-h vs hybrid with 4-h range | ~same cold starts, ~50% more resources | Simulation | §5.2, Fig. 15 |
| Invocations handled by ARIMA / apps using it | 0.64% / 9.3% | Simulation | §5.2, Fig. 19 |
| Apps with 100% cold starts, without vs with ARIMA | 10.5% → 5.2% | Simulation | §5.2, Fig. 19 |
| Testbed | 19 VMs (18 invokers, 2 cores and 4 GB each); 68 apps; 8 h per run; 12,383 invocations | OpenWhisk | §5.1, §5.3 |
| Worker container memory | −15.6% | OpenWhisk vs default 10-min | §5.3 |
| Function execution time, average / p99 | −32.5% / −82.4% | OpenWhisk; warm containers skip runtime bootstrap | §5.3 |
| Added end-to-end latency | 835.7 µs average (σ 245.5 µs) | OpenWhisk | §5.3 |
| ARIMA cost | 26.9 ms model build, 5.3 ms per later forecast | OpenWhisk | §5.3 |
| Histogram size in production | 240 integers = 960 bytes per app | Azure Functions | §6 |

## Limitations

- **No production results.** §6 says the main elements "will be rolling out to production in stages" but reports no production measurements; evidence is simulation plus a 68-app, 8-hour OpenWhisk run (§5).
- **Simulation simplifications** (§5.1): execution time is set to 0 (worst case for wasted memory), and every application is assumed to use the same memory because memory data is incomplete. (Own analysis) Simulated memory savings are therefore in wasted-time terms, not bytes.
- **Concurrency cold starts are out of scope** (§2; fewer than 1% of applications, per the paper).
- **Heuristic parameters.** Percentiles, margins, the 4-hour range and CV=2 come from sensitivity studies on this one trace (§5.2).
- **Things the paper flags but leaves open:** the cause of the constant ~50% invocation baseline is not investigated (§3.3). The production implementation covers HTTP-triggered applications only, and no reason is given (§6).
- **Possible tension inside the paper:** §3.1 describes data on all invocations across Azure's infrastructure, but the simulation assumes equal per-app memory because memory data is incomplete (§5.1), and only a subset of the traces is released (§3.1).
- (Own analysis) Each application is optimized on its own; cluster-level memory pressure and placement are not considered.

## Relation to other systems

- **Fixed keep-alive (AWS Lambda, Azure Functions, OpenWhisk default):** one timeout for every application; the hybrid policy uses per-application pre-warm and keep-alive windows and can unload early when the next call is predictably far away (§1, §2, §4).
- **SOCK (OpenLambda):** makes each cold start cheaper (library caching, lightweight isolation); this paper reduces how often they happen (§7).
- **SAND:** application-level sandboxing avoids cold starts for later calls within an application; Azure already warms all of an application's functions together (§7).
- **Replayable Execution:** checkpointing and memory sharing speed up JVM-based startup, again cutting cold-start cost, not count (§7).
- **TTL caches and prefetching cache policies:** TTLs reset on access but do not prefetch; prefetching caches evict only under capacity pressure. The hybrid policy unloads and pre-warms proactively (§7).

## Takeaways for practice

- Make the **unit of warmth** the unit the platform actually loads (here, the application), and keep per-unit state small: a fixed-size histogram of 240 integers (960 bytes) is enough (§6).
- Separate **when to load** from **how long to stay**. A pre-warm window lets the platform give memory back during predictable idle gaps instead of paying a long keep-alive.
- Use **cheap statistics first, expensive models only for the tail**. The histogram serves almost everything; ARIMA ran for 0.64% of invocations in simulation and still halved the share of always-cold apps (§5.2).
- Always pair a predictor with a **representativeness test and a safe fallback**. Here, a CV-of-bins check maintained online with Welford's algorithm (§4.2).
- Keep the policy **off the critical path**. Azure runs decisions asynchronously and schedules pre-warm 90 s early (§6); OpenWhisk overhead was 835.7 µs average (§5.3).
- (Own analysis) The same idle-time histogram plus fallback pattern carries over to deciding when to keep model replicas or sandbox images resident in inference and agent-sandbox platforms, where load times are also large relative to request times.

## References

- Paper (USENIX ATC '20, pp. 205–218): https://www.usenix.org/conference/atc20/presentation/shahrad
- PDF: https://www.usenix.org/system/files/atc20-shahrad.pdf
- arXiv: https://arxiv.org/abs/2003.03423
- Released traces (URL as given in §3.1 of the paper; not opened for this note): https://github.com/Azure/AzurePublicDataset
